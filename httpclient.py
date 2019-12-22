import io
import socket
import sys
import logging

from email.parser import Parser

import chardet

from argparser import AParser
from backend.request import Request
from backend.response import Response
from defenitions import LOG_PATH


class Client:
    ENDCHARS = [b'\r\n', b'\n', b'']
    LINESEP = '\r\n'
    MAX_LINE = 64 * 1024
    HTTP_PORT = 80
    HTTPS_PORT = 443

    def __init__(self, args, timeout=1):
        self.connected = False
        self.timeout = timeout
        self.args = args

        logging.basicConfig(filename=LOG_PATH, level=logging.INFO)
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
    def parse_content_type(ct: str) -> dict:
        s = ct.split('; ')
        vals = {}
        for sub in s:
            k = sub.split('=')
            if len(k) == 2:
                key, value = k[0], k[1]
                vals[key] = value
            else:
                vals['type'] = ''.join(k)
        return vals

    @staticmethod
    def bad_response(res: Response):
        if res.status in ['404', '403']:
            return 1
        return 0

    def output(self, res: Response, destination):
        if self.bad_response(res):
            data = res.reason
        else:
            data = res.body
            ct = self.parse_content_type(res.headers.get('Content-Type'))
            encoding = ct.get('charset')
            if encoding:
                data = data.decode(encoding)
            else:
                data = self.decode(data)

        if destination == '-':
            try:
                # for str
                sys.stdout.write(data)
            except Exception:
                # for bytes
                sys.stdout.buffer.write(data)
            logging.info('bytes printed')
        elif destination is not None:
            with open(destination, 'wb') as f:
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
                response = Response(*parsed)
                logging.info(f'respose: \n{response}')
            redirect = self.get_redirect(response)
            if redirect and not req.no_redirect:
                new_req = Request('GET', redirect,
                                  req.host, None, None,
                                  req.no_redirect, None)
                req = new_req
            else:
                break
        return response

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
            if encoding:
                return str(b, encoding)
            else:
                return b
        except Exception:
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


def main():
    parser = AParser()
    args = parser.parse()
    logging.info(args)
    try:
        with Client(args, timeout=1) as client:
            client.connect(args.url, args.port)
            req = Request(args.method, args.path,
                          args.url, args.header, args.body,
                          args.no_redirects, args.form)
            res = client.request(req)
            client.output(res, args.output)

    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(e.__str__())


if __name__ == '__main__':
    main()
