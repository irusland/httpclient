import io
import socket
import sys
import logging
import argparse

from email.parser import Parser
from urllib.parse import urlparse

import chardet

from argparser import parse
from defenitions import LOG_PATH
from exceptions import ByteFloodError, BytesDecodeError


class Client:
    ENDCHARS = [b'\r\n', b'\n', b'']
    LINESEP = '\r\n'
    MAX_LINE = 64 * 1024
    HTTP_PORT = 80
    HTTPS_PORT = 443

    def __init__(self, timeout=1):
        self.connected = False
        self.timeout = timeout

        logging.basicConfig(filename=LOG_PATH, level=logging.INFO)
        socket.setdefaulttimeout(self.timeout)
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
        return False

    def find_host_ip(self, host):
        try:
            ip = socket.gethostbyname(host)
            logging.info(f'host ip found {ip}')
            return ip
        except socket.gaierror:
            logging.exception('Can\'t resolve host')

    def output(self, data, content_type, destination):
        if destination == '-':
            print(data)
            logging.info('bytes printed')
        elif destination is not None:
            with open(destination, 'wb') as f:
                f.write(data)
                logging.info('File written')
        else:
            try:
                print(self.decode(data))
            except Exception:
                raise ByteFloodError()

    def connect(self, host, port=HTTP_PORT):
        ip = self.find_host_ip(host)
        if ip:
            try:
                self.connection.connect((ip, port))
                logging.info(f'connection established to {ip}:{port}')
                self.connected = True
            except ConnectionRefusedError as e:
                logging.exception(f'Connection refused error {e}')
                self.connected = False
                raise ConnectionError('Cannot connect to server')

    def request(self, req):
        if not self.connected:
            raise ConnectionError('Not connected')
        logging.info(f'got request to send: {req}')
        if not self.connected:
            logging.exception('No connection established')
            return
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
        return b''.join(lines)

    def parse_headers(self, file):
        headers = self.parse_body(file).decode()
        dheaders = Parser().parsestr(headers)
        return dheaders

    @staticmethod
    def decode(b):
        encoding = chardet.detect(b)['encoding']
        if encoding:
            return str(b, encoding)
        return str(b, 'utf-8')

    def parse_line(self, file):
        raw = file.readline(self.MAX_LINE + 1)
        req_line = raw.decode()
        try:
            ver, status, *reason = req_line.split()
        except ValueError as e:
            logging.exception('Incorrect response syntax')
            e = req_line.split()
            raise ValueError(e)
        return status, reason

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
        req = (f'{method} {target} HTTP/1.1\n'
               f'Host: {host}')
        headers = '' if not header else '\n'.join(h for h in header)
        req = f'{req}\n{headers}\r\n\r\n{body if body else ""}'
        self._request = req

    def __str__(self):
        return self._request

    def __bytes__(self):
        return self._request.encode('utf-8')


def main():
    args = parse(Client.HTTP_PORT)
    logging.info(args)
    try:
        with Client(timeout=1) as client:
            client.connect(args.url)
            req = Request(args.method, args.path,
                          args.url, args.header, args.body)
            res = client.request(req)
            content_type = res.headers.get('Content-Type')
            client.output(res.body, content_type, args.output)

    except ByteFloodError:
        print('Binary representation available only. Use "--output -" to '
              'output it to your terminal '
              'or consider "--output <FILE>" '
              'to save to a file.')

    except Exception as e:
        print(e)


if __name__ == '__main__':
    main()
