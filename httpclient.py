import io
import socket
import sys
import logging

from email.parser import Parser


class Client:
    ENDCHARS = [b'\r\n', b'\n', b'']
    LINESEP = '\r\n'
    MAX_LINE = 64 * 1024
    HTTP_PORT = 80
    HTTPS_PORT = 443

    def __init__(self):
        self.connected = False
        socket.setdefaulttimeout(1)
        logging.basicConfig(filename="client.log", level=logging.INFO)
        try:
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            logging.info(f'socket created')
        except Exception as e:
            logging.exception(e)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connected = False
        logging.exception(exc_type, exc_val, exc_tb)

    def find_host_ip(self, host):
        try:
            ip = socket.gethostbyname(host)
            logging.info(f'host ip found {ip}')
            return ip
        except socket.gaierror:
            logging.error('Can\'t resove host')

    def connect(self, host, port):
        ip = self.find_host_ip(host)
        if ip:
            try:
                self.connection.connect((ip, port))
                logging.info(f'connection established to {ip}:{port}')
                self.connected = True
            except ConnectionRefusedError as e:
                logging.error(f'Connection refused error {e}')

    def request(self, req):
        if not self.connected:
            raise ConnectionError('No connection established')
        try:
            self.connection.sendall(req)
        except socket.error:
            logging.error('Send failed')
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
            logging.error('receiving timed out')

        res = b''.join(data)
        file = io.BytesIO(res)
        parsed = self.parse_response(file)
        return Response(*parsed)

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
            logging.error('Incorrect response syntax')
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
        self.reason = reason
        self.headers = headers
        self.body = body

    def __str__(self):
        lim = 500
        return '\n'.join(
            f'{k}: {str(v) if len(str(v)) < lim else str(v)[:lim]}'
            for k, v in self.__dict__.items())


def main():
    client = Client()
    client.connect('google.com', Client.HTTP_PORT)
    req = b'GET / HTTP/1.1\n' \
          b'Host: 0.0.0.0:8000\n' \
          b'Accept: text/html,application/xhtml+xml,' \
          b'application/xml;q=0.9,*/*;q=0.8\n' \
          b'Accept-Language: en-us\r\n\r\n'
    res = client.request(req)
    print(f'respose: \n{res}')
    client.disconnect()


if __name__ == '__main__':
    program_name = sys.argv[0]
    arguments = sys.argv[1:]
    for x in arguments:
        print(f'Argument: {x}')
    main()
