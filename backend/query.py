import logging
import random
import re
import string
from email.message import Message
from email.parser import Parser

import chardet


class Request:
    def __init__(self, method, target, host, add_header=None, body=None,
                 no_redir=True, form=None, max_redir=None):
        self.method = method
        self.target = target
        self.host = host
        self.form = form
        self.headers = add_header or []
        self.body = body
        self.no_redirect = no_redir
        self.max_redir = max_redir

        req = (f'{method} {target} HTTP/1.1\r\n'
               f'Host: {host}')
        self.headers.append(f'Accept: */*')

        if self.form:
            boundary = self.make_boundary()
            ct = f'Content-Type: multipart/form-data; boundary={boundary}'
            self.headers.append(ct)
            self.body = self.make_multipart(self.form, boundary)

        if self.body:
            self.headers.append(f'Content-Length: {len(self.body)}')

        if self.headers:
            headers = '\r\n'.join(h for h in self.headers)
        else:
            headers = ''
        req = (f'{req}\r\n'
               f'{headers}\r\n'
               f'\r\n'
               f'{self.body if self.body else ""}')
        self.request = req

    def __str__(self):
        return self.request

    def __bytes__(self):
        return self.request.encode('utf-8')

    def make_boundary(self):
        length = 40
        chars = 16
        dashes = length - chars
        return ('-' * dashes) + ''.join(random.choices(
            string.ascii_lowercase + string.digits, k=chars))

    def make_multipart(self, form, boundary):
        res = []
        for f in form:
            name, value = f.split('=', maxsplit=2)
            res.append(f'--{boundary}')
            res.append(f'{self.make_disposition(name)}')
            res.append(f'')
            res.append(f'{value}')

        res.append(f'--{boundary}--\r\n')
        return '\r\n'.join(res)

    def make_disposition(self, name):
        return f'Content-Disposition: form-data; name="{name}"'


class Response:
    def __init__(self):
        self.status = None
        self.reason = None
        self.headers = {}
        self.body = b''

        self._body_to_read = None
        self.filled = False

    def dynamic_fill(self, line: bytes):
        if not self._body_to_read and not self.filled:
            if line.endswith(b'\r\n'):
                line = line[:-2]
            elif line.endswith(b'\n'):
                line = line[:-1]

        if not line:
            if self._body_to_read == 0:
                self.filled = True
                return True
            if not self._body_to_read:
                length = self.headers.get("Content-Length")
                if length:
                    self._body_to_read = int(length)
                else:
                    self._body_to_read = 0
                    self.filled = True
                    return True
            return False

        if not self.status:
            line = Response.decode(line)
            _, self.status, *self.reason = line.split()
            self.reason = ' '.join(self.reason)
            return False

        if self._body_to_read != 0 and self._body_to_read is not None:
            self.body += line
            self._body_to_read -= len(line)
            if self._body_to_read < 0:
                logging.error('Content-Length was less than body len')
                return True
            if self._body_to_read == 0:
                self.filled = True
                return True
        else:
            p = Parser()
            headers = p.parsestr(Response.decode(line))
            if headers.items():
                for k, v in headers.items():
                    self.headers[k] = v

    @staticmethod
    def decode(b):
        encoding = chardet.detect(b)['encoding']
        return str(b, encoding or 'utf-8')

    @staticmethod
    def split_keep_sep(s: bytes, sep):
        xs = re.split(rb'(%s)' % re.escape(sep), s)
        return [xs[i] + (xs[i + 1] if i + 1 < len(xs) else b'')
                for i in range(0, len(xs), 2)]

    def __str__(self):
        return '\n'.join(
            f'{k}: {str(v)}'
            for k, v in self.__dict__.items())
