import io
import socket
import sys
import logging
import argparse

from email.parser import Parser
from defenitions import LOG_PATH


class Client:
    ENDCHARS = [b'\r\n', b'\n', b'']
    LINESEP = '\r\n'
    MAX_LINE = 64 * 1024
    HTTP_PORT = 80
    HTTPS_PORT = 443
    TIMEOUT = 2

    def __init__(self):
        self.connected = False
        logging.basicConfig(filename=LOG_PATH, level=logging.INFO)
        socket.setdefaulttimeout(self.TIMEOUT)
        try:
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            logging.info(f'socket created')
        except Exception as e:
            logging.exception(e)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connected = False
        self.connection.close()
        logging.exception(exc_type, exc_val, exc_tb)
        return True

    def find_host_ip(self, host):
        try:
            ip = socket.gethostbyname(host)
            logging.info(f'host ip found {ip}')
            return ip
        except socket.gaierror:
            logging.exception('Can\'t resove host')

    def connect(self, host, port=HTTP_PORT):
        ip = self.find_host_ip(host)
        if ip:
            try:
                self.connection.connect((ip, port))
                logging.info(f'connection established to {ip}:{port}')
                self.connected = True
            except ConnectionRefusedError as e:
                logging.exception(f'Connection refused error {e}')

    def request(self, req):
        logging.info(f'got request to send: {req}')
        if not self.connected:
            logging.exception('No connection established')
            return
        try:
            self.connection.sendall(bytes(req))
        except socket.error:
            logging.exception('Send failed')
            sys.exit()
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
            logging.exception('receiving timed out')

        res = b''.join(data)
        file = io.BytesIO(res)
        parsed = self.parse_response(file)
        response = Response(*parsed)
        logging.info(f'respose: \n{response}')
        return response

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
        return b''.join(lines).decode()

    def parse_line(self, file):
        raw = file.readline(self.MAX_LINE + 1)
        req_line = raw.decode()
        try:
            ver, status, *reason = req_line.split()
        except ValueError as e:
            logging.exception('Incorrect response syntax')
            e = req_line.split()
            raise SyntaxError(e)
        return status, reason

    def parse_headers(self, file):
        headers = []
        while True:
            line = file.readline(self.MAX_LINE + 1)
            if line in self.ENDCHARS:
                break
            headers.append(line)
        headers = b''.join(headers).decode()
        dheaders = Parser().parsestr(headers)
        return dheaders

    def disconnect(self):
        if self.connected:
            self.connected = False
            self.connection.close()
            logging.info(f'connection closed')


class Response:
    def __init__(self, status, reason, headers=None, body=None):
        self.status = status
        self.reason = ' '.join(reason)
        self.headers = headers
        self.body = body

    def __str__(self):
        limit = Client.MAX_LINE
        return '\n'.join(
            f'{k}: '
            f'{str(v) if not limit else str(v)[:limit]}'
            for k, v in self.__dict__.items())


class Request:
    def __init__(self, method, target, host, header=None, body=None):
        self._method = method
        self._target = target
        self._host = host
        self._header = header
        self._body = body
        req = f'{method} {target} HTTP/1.1\n' \
              f'Host: {host}'
        headers = '' if not header else '\n'.join(h for h in header)
        req = f'{req}\n{headers}\r\n\r\n{body if body else ""}'
        self._request = req

    def __str__(self):
        return self._request

    def __bytes__(self):
        return self._request.encode('utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('host', help='Host name')
    parser.add_argument('-p', '--port', type=int,
                        help='Choose port', default=Client.HTTP_PORT)
    parser.add_argument('-m', '--method', help='send GET or POST request',
                        default='GET')
    parser.add_argument('--target', help='Specify request url', default='/')
    parser.add_argument('-H', '--header', action='append',
                        help='Specify request header')
    parser.add_argument('--body', help='Request body')

    args = parser.parse_args()
    logging.info(args)
    with Client() as client:
        client.connect(args.host, args.port)
        if client.connected:
            req = Request(args.method, args.target,
                          args.host, args.header, args.body)
            res = client.request(req)
            return res.body


if __name__ == '__main__':
    print(main())
