import io
import multiprocessing
import socket
import sys
import time
import unittest

import httpclient
from backend.client_backend import Client
from backend.query import Request, Response
from aiohttp import web


class ClientTestCase(unittest.TestCase):
    def connect(self):
        client = Client()
        client.connect('google.com')
        return client

    def test_build_req(self):
        m = 'GET'
        t = '/'
        h = 'google.com'
        hs = ['Content-Type: text/html']
        b = 'body'

        r = Request(m, t, h, hs, b)

        self.assertEqual(r.method, m)
        self.assertEqual(r.target, t)
        self.assertEqual(r.host, h)
        self.assertEqual(r.headers, hs)
        self.assertEqual(r.body, b)

        self.assertEqual(f'{m} {t} HTTP/1.1\r\n'
                         f'Host: {h}\r\n'
                         f'{hs[0]}\r\n'
                         f'Accept: */*\r\n'
                         f'Content-Length: {len(b)}\r\n'
                         f'\r\n{b}'.encode('utf-8'), bytes(r))

    class MockClient:
        def __init__(self):
            self.connected = True
            self.closed = False
            self.connection = ClientTestCase.MockClient.Connection()

        class Connection:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

            def sendall(self, b):
                raise socket.error

    def test_disconnect(self):
        mock_client = ClientTestCase.MockClient()
        Client.disconnect(mock_client)
        self.assertEqual(mock_client.connected, False)
        self.assertEqual(mock_client.connection.closed, True)

    def test_decode(self):
        enc = 'utf-8'
        string = 'test_string'
        encoded = string.encode(enc)
        decoded = Client.decode(encoded)
        self.assertEqual(decoded, string)

    def test_no_decode(self):
        b = b'\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\\x '
        dec = Client.decode(b)
        self.assertEqual(dec, b)

    def test_request_connection_err(self):
        mock = ClientTestCase.MockClient()
        mock.connected = False
        with self.assertRaises(ConnectionError):
            Client.request(mock, b'')

    def test_request_sendall_fails(self):
        mock = ClientTestCase.MockClient()
        with self.assertRaises(socket.error):
            Client.request(mock, b'')

    def test_context_manager(self):
        try:
            with Client() as _:
                pass
        except socket.error:
            self.fail()

    class ClientMock(Client):
        def __init__(self):
            super().__init__()
            self.connected = True
            self.connection = ClientTestCase.ConnectionMock()
            self.MAX_LINE = 10000
            self.ENDCHARS = [b'\r\n', b'']

    class ConnectionMock:
        SENT = False

        def sendall(self, *args):
            pass

        def recv(self, *args):
            if not self.SENT:
                self.SENT = True
                return (b'HTTP/1.1 200 OK\r\n'
                        b'Server: httpserver\r\n'
                        b'Content-Length: 12\r\n'
                        b'\r\n'
                        b'1234567890\r\n')
            return b''

    def test_request(self):
        res = Client.request(ClientTestCase.ClientMock(),
                             Request('GET', '/', 'HTTP/1.1'))
        self.assertEqual(res.status, '200')
        self.assertEqual(res.reason, 'OK')
        self.assertListEqual(list(res.headers.items()),
                             [('Server', 'httpserver'),
                              ('Content-Length', '12')])
        self.assertEqual(res.body, b'1234567890\r\n')

    def test_ct_parse(self):
        ct = Client.parse_content_type('text/html; charset=utf-8')
        self.assertEqual(ct.get('charset'), 'utf-8')

    def test_bad_req(self):
        res: Response = Response()
        res.status = '404'
        res.reason = 'Not Found'
        br = Client.bad_response(res)
        self.assertEqual(br, 1)

    def test_not_bad_req(self):
        res: Response = Response()
        res.status = '200'
        res.reason = 'OK'
        br = Client.bad_response(res)
        self.assertEqual(br, 0)

    def test_parse_res(self):
        res = Response()
        res.status = '200'
        res.reason = 'OK'
        res.headers = {}
        res.body = 'body'
        with Client() as c:
            body = c.parse_res(res)
            self.assertEqual(body, 'body')

    def test_parse_args(self):
        sys.argv = ['client_backend.py', 'http://urgu.org/c.png']

        args = httpclient.parse()
        self.assertEqual(args.url, 'urgu.org')
        self.assertEqual(args.path, '/c.png')
        self.assertEqual(args.method, 'GET')
        self.assertEqual(args.output, None)
        self.assertEqual(args.user_agent, 'httpclient/0.4.5')

    def test_output_no_dest(self):
        res = Response()
        res.status = '200'
        res.reason = 'OK'
        res.headers = {'Content-Type': 'text/html; charset=utf-8'}
        res.body = b'body'

        with self.assertRaises(IOError):
            Client.output(Client(None), res, '', '')

    def test_output_stdout(self):
        res = Response()
        res.status = '200'
        res.reason = 'OK'
        res.headers = {'Content-Type': 'text/html; charset=utf-8'}
        res.body = b'body'

        with Client(None) as c:
            c.output(res, None, '')

    def test_parse_response(self):
        contents = 'HTTP/1.1 200 OK\r\nh1: h1\r\nh2: ' \
                   'h2\r\n\r\nbody\r\n'.encode()
        file = io.BytesIO(contents)
        with Client() as c:
            s, r, h, b = Client.parse_response(c, file)
        self.assertEqual(s, '200')
        self.assertListEqual(r, ['OK'])
        self.assertEqual(str(h), 'h1: h1\nh2: h2\n\n')
        self.assertEqual(b, b'body\r\n')

    def test_cookie(self):
        cookie = ['a=a', 'b=b']
        args = {'body': None,
                'cookie': cookie,
                'form': [],
                'header': ['User-Agent: httpclient/0.4.5',
                           'Connection: keep-alive',
                           f'Cookie: {"; ".join(cookie)}'],
                'max_redirects': 10,
                'method': 'GET',
                'no_redirects': False,
                'output': None,
                'path': '/',
                'port': None,
                'timeout': 1,
                'url': 'a.com',
                'user_agent': 'httpclient/0.4.5'}

        req = Request(args['method'], args['path'], args['url'],
                      add_header=args['header'], body=args['body'],
                      no_redir=args['no_redirects'], form=args['form'],
                      max_redir=args['max_redirects'])

        self.assertEqual(req.method, 'GET')
        for header in req.headers:
            if header.startswith('Cookie'):
                self.assertEqual(header, f'Cookie: {"; ".join(cookie)}')
                return
        self.fail()

    def test_main_exception(self):
        sys.argv = ['httpclient.py', '']
        with self.assertRaises(SystemExit):
            httpclient.main()


if __name__ == '__main__':
    unittest.main()
