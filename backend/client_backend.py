import argparse
import io
import socket
import sys
import logging

from email.parser import Parser

import chardet

from backend.query import Request, Response
from defenitions import LOG_PATH
from urllib.parse import urlparse


class Client:
    ENDCHARS = [b'\r\n', b'']
    LINESEP = '\r\n'
    MAX_LINE = 64 * 1024
    HTTP_PORT = 80
    HTTPS_PORT = 443

    def __init__(self, timeout=1):
        self.connected = False
        self.timeout = timeout

        logging.basicConfig(filename=LOG_PATH, filemode='w',
                            level=logging.INFO)
        socket.setdefaulttimeout(self.timeout)
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logging.info(f'socket created')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connected = False
        self.connection.close()
        return False

    @staticmethod
    def parse():
        parser = argparse.ArgumentParser()
        parser.add_argument('url', help='Url to request')
        parser.add_argument('-m', '--method',
                            help='send GET or POST request',
                            choices=['GET', 'POST'],
                            default='GET')
        parser.add_argument('-F', '--form', action='append',
                            help='Form-data',
                            default=[])
        parser.add_argument('-H', '--header', action='append',
                            help='Specify request header',
                            default=[])
        parser.add_argument('--body', help='Request body'),
        parser.add_argument('--user-agent', help='Specify UA for request',
                            default='httpclient/0.4.5')
        parser.add_argument('--cookie', action='append',
                            help='Specify request cookies',
                            default=[])
        parser.add_argument('-o', '--output',
                            default='-',
                            help='Use "--output <FILENAME>" to '
                                 'print save to file')
        parser.add_argument('--no-redirects', action='store_true')

        args = parser.parse_args()
        url = urlparse(args.url)
        args.url = url.netloc.split(':')[0]
        args.path = url.path or '/'
        args.port = url.port
        args.header.append(f'User-Agent: {args.user_agent}')
        args.header.append(f'Connection: keep-alive')
        if args.cookie:
            args.header.append(f'Cookie: {"; ".join(args.cookie)}')
        if args.form:
            args.method = 'POST'
        return args

    @staticmethod
    def parse_content_type(ct: str) -> dict:
        if not ct:
            return {}
        s = ct.split('; ')
        vals = {}
        for sub in s:
            if '=' in sub:
                k = sub.split('=', maxsplit=2)
                key, value = k[0], k[1]
                vals[key] = value
            else:
                vals['type'] = sub
        return vals

    @staticmethod
    def bad_response(res: Response):
        if res.status in ['404', '403']:
            return True
        return False

    def parse_res(self, res: Response):
        if self.bad_response(res):
            data = res.reason
        else:
            data = res.body
            ct = self.parse_content_type(res.headers.get('Content-Type'))
            encoding = ct.get('charset')
            if encoding:
                try:
                    data = data.decode(encoding)
                except Exception:
                    pass
            else:
                data = self.decode(data)
        return data

    def output(self, res: Response, destination: str, data: str) -> None:
        if destination == '-':
            try:
                # for str
                sys.stdout.write(data)
            except Exception:
                # for bytes
                sys.stdout.buffer.write(data)
            logging.info('bytes printed')
        elif destination is not None:
            with open(destination, 'w') as f:
                f.write(data)
                logging.info('File written')
        else:
            raise IOError

        if self.bad_response(res):
            sys.exit(1)

    def connect(self, host, port=None):
        if port is None:
            port = Client.HTTP_PORT
        try:
            self.connection.connect((host, port))
            logging.info(f'connection established to {host}:{port}')
            self.connected = True
        except ConnectionRefusedError as e:
            logging.exception(f'Connection refused error {e}')
            self.connected = False
            sys.exit(1)

    def request(self, req: Request):
        while True:
            if not self.connected:
                logging.exception('No connection established')
                raise ConnectionError('Not connected')
            logging.info(f'got request to send: {req}')
            try:
                self.connection.sendall(bytes(req))
            except socket.error as e:
                logging.exception('Send failed')
                raise e
            logging.info(f'request sent {req}')
            data = []
            logging.info(f'waiting for response')
            try:
                while True:
                    s = self.connection.recv(self.MAX_LINE)
                    logging.info(f'received {s}')
                    if s in self.ENDCHARS:
                        break
                    data.append(s)
            except socket.timeout:
                pass

            res = b''.join(data)
            if not res:
                return
            with io.BytesIO(res) as file:
                parsed = self.parse_response(file)
                res = Response(*parsed)
                if int(res.headers.get('Content-Length')) != len(res.body):
                    raise Exception('Content Length insufficient')
                logging.info(f'respose: \n{res}')
            redirect = self.get_redirect(res)
            if redirect and not req.no_redirect:
                req = Request('GET', redirect,
                              req.host, None, None,
                              req.no_redirect, None)
            else:
                break
        return res

    @staticmethod
    def get_redirect(res: Response):
        if res.status == '301' and res.reason == 'Moved Permanently':
            return res.headers.get('Location')

    def parse_response(self, file):
        status, reason = self.parse_line(file)
        headers = self.parse_headers(file)
        body = self.parse_body(file)
        return status, reason, headers, body

    def parse_body(self, file):
        lines = []
        while True:
            line = file.readline(self.MAX_LINE + 1)
            if line in self.ENDCHARS:
                break
            lines.append(line)
        return b''.join(lines)

    def parse_headers(self, file):
        headers = self.parse_body(file).decode()
        dheaders = Parser().parsestr(headers)
        return dheaders

    @staticmethod
    def decode(b):
        try:
            encoding = chardet.detect(b)['encoding']
            return str(b, encoding)
        except Exception:
            pass
        return b

    def parse_line(self, file):
        raw = file.readline(self.MAX_LINE + 1)
        req_line = raw.decode()
        try:
            ver, status, *reason = req_line.split()
        except ValueError as e:
            logging.exception('Incorrect response syntax')
            raise ValueError(req_line)
        return status, reason

    def disconnect(self):
        if self.connected:
            self.connected = False
            self.connection.close()
            logging.info(f'connection closed')
