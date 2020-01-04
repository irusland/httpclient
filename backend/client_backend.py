import socket
import sys
import logging

from email.parser import Parser

import chardet

from backend.query import Request, Response
from defenitions import LOG_PATH


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
    def parse_content_type(ct):
        if not ct:
            return {}
        s = ct.split('; ')
        vals = {}
        for sub in s:
            if '=' in sub:
                key, value = sub.split('=', maxsplit=1)
                vals[key] = value
            else:
                vals['type'] = sub
        return vals

    @staticmethod
    def bad_response(res: Response):
        return res.status in ['404', '403']

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

    def output(self, res: Response, destination, data):
        if destination is None:
            try:
                sys.stdout.write(data)
            except Exception:
                sys.stdout.buffer.write(data)
            logging.info('bytes printed')
        else:
            if isinstance(data, str):
                mode = 'w'
            else:
                mode = 'wb'
            with open(destination, mode) as f:
                f.write(data)
                logging.info('File written')

        if Client.bad_response(res):
            raise Exception('Bad response')

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

    def request(self, req: Request):
        redir_count = 0
        while True:
            if not self.connected:
                logging.error('No connection established')
                raise ConnectionError('Not connected')
            logging.info(f'got request to send: {req}')
            try:
                self.connection.sendall(bytes(req))
            except socket.error:
                logging.exception('Send failed')
                raise
            logging.info(f'request sent {req}')
            logging.info(f'waiting for response')
            res_builder = Response()
            break_out = False
            while not break_out:
                try:
                    while not break_out:
                        line = self.connection.recv(self.MAX_LINE)
                        split = Response.split_keep_sep(line, b'\r\n')
                        for s in split:
                            logging.info(f'received {s}')
                            if res_builder.dynamic_fill(s):
                                break_out = True
                                break
                except socket.timeout:
                    logging.info(f'body not received, waiting')

            redirect = self.get_redirect(res_builder)
            if redirect and not req.no_redirect and \
                    (not req.max_redir or redir_count < req.max_redir):
                redir_count += 1
                req = Request('GET', redirect,
                              req.host, no_redir=req.no_redirect,
                              max_redir=req.max_redir)
            else:
                break
        return res_builder

    @staticmethod
    def get_redirect(res: Response):
        if res.status == '301' and res.reason == 'Moved Permanently':
            return res.headers.get('Location')

    def parse_response(self, file):
        status, reason = self.parse_line(file)
        headers = self.parse_headers(file)
        body = self.parse_body(file, headers.get('Content-Length'))
        return status, reason, headers, body

    def parse_body(self, file, content_len=None):
        lines = []
        if content_len is None:
            content_len = -1
        content_len = int(content_len)
        while True and content_len:
            line = file.readline(self.MAX_LINE + 1)
            content_len -= len(line)
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
