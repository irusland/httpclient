import io
import os
import socket
import sys
import unittest
from random import random

import httpclient
from argparser import AParser

from httpclient import Client
from backend.request import Request
from unittest.mock import patch


class ClientTestCase(unittest.TestCase):
    def connect(self):
        client = Client(AParser())
        client.connect('google.com')
        return client

    def test_connect(self):
        with self.connect() as client:
            self.assertTrue(client.connected)

    def test_connect_fail(self):
        with Client(AParser()) as client:
            self.assertRaises(SystemExit, client.connect, '')

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

        self.assertEqual(f'{m} {t} HTTP/1.1\n'
                         f'Host: {h}\n'
                         f'{hs[0]}\n'
                         f'Accept: */*\n'
                         f'Content-Length: {len(b)}'
                         f'\r\n\r\n{b}\r\n'.encode('utf-8'), bytes(r))

    #
    # def test_run_command_line(self):
    #     args = 'google.com', '--output', '-'
    #     testargs = ["httpclient.py", *args]
    #     with patch.object(sys, 'argv', testargs):
    #         try:
    #             httpclient.main()
    #         except Exception:
    #             self.fail()
    #
    # def test_run_command_line_save_file(self):
    #     path = f'{random()}.txt'
    #     args = 'https://google.com', '--output', path
    #     testargs = ["httpclient.py", *args]
    #     with patch.object(sys, 'argv', testargs):
    #         httpclient.main()
    #         with open(path, 'rb') as f:
    #             data = f.read()
    #             os.remove(path)
    #             self.assertIsNotNone(data)

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
        s = 'ascii'
        b = s.encode(enc)
        dec = Client.decode(b)
        self.assertEqual(dec, s)

    def test_no_decode(self):
        b = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10' \
            b'\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f ' \
            b'!"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[' \
            b'\\]^_`abcdefghijklmnopqrstuvwxyz{' \
            b'|}~\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c' \
            b'\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b' \
            b'\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa' \
            b'\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9' \
            b'\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8' \
            b'\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7' \
            b'\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6' \
            b'\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5' \
            b'\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\\x '
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
            with Client(AParser()) as _:
                pass
        except socket.error:
            self.fail()

    def test_request(self):
        with self.connect() as client:
            self.assertTrue(client.connected)
            req = Request('GET', '/', 'google.com')
            res = client.request(req)
            self.assertIsNotNone(res)
            self.assertNotEqual(res, 'Empty reply from server')

    def test_parse_response(self):
        contents = 'HTTP/1.1 200 OK\nh1: h1\nh2: h2\n\nbody\n'.encode()
        file = io.BytesIO(contents)
        with Client(AParser()) as c:
            s, r, h, b = Client.parse_response(c, file)
        self.assertEqual(s, '200')
        self.assertListEqual(r, ['OK'])
        self.assertEqual(str(h), 'h1: h1\nh2: h2\n\n')
        self.assertEqual(b, b'body\n')


if __name__ == '__main__':
    unittest.main()
