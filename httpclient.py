import socket
import sys


class Client:
    ENDCHARS = {b'', b'\n'}
    MAX_LINE = 64 * 1024

    def __init__(self):
        self.connected = False
        try:
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f'socket created')
        except Exception as e:
            print(e)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connected = False
        print(exc_type, exc_val, exc_tb)

    def find_host_ip(self, host):
        try:
            ip = socket.gethostbyname(host)
            print(f'host ip found {ip}')
            return ip
        except socket.gaierror:
            print('Can\'t resove host')

    def connect(self, host, port):
        ip = self.find_host_ip(host)
        if ip:
            try:
                self.connection.connect((ip, port))
                print(f'connection established to {ip}:{port}')
                self.connected = True
            except ConnectionRefusedError as e:
                print(f'Connection refused error {e}')

    def request(self, req):
        if not self.connected:
            return 'No connection established'
        try:
            self.connection.sendall(req)
        except socket.error:
            print('Send failed')
            sys.exit()
        print(f'request sent {req}')
        data = []
        print(f'waiting for response')
        while True:
            s = self.connection.recv(self.MAX_LINE)
            print(f'received {s}')
            if s in self.ENDCHARS:
                break
            data.append(s)

        return b''.join(data).decode()

    def disconnect(self):
        if self.connected:
            self.connected = False
            self.connection.close()
            print(f'connection closed')


def main():
    client = Client()
    client.connect('0.0.0.0', 8000)
    res = client.request(b'GET / HTTP/1.1\r\n\r\n')
    print(f'respose {res}')
    client.disconnect()


if __name__ == '__main__':
    main()
