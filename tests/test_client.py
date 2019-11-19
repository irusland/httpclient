import socket
import sys
import unittest
import httpclient

from httpclient import Client, Request
from unittest.mock import patch


class MyTestCase(unittest.TestCase):
    def connect(self):
        client = Client()
        client.connect('google.com')
        return client

    def test_connect(self):
        with self.connect() as client:
            self.assertTrue(client.connected)

    def test_connect_fail(self):
        with Client() as client:
            client.connect('')
            self.assertFalse(client.connected)

    def test_build_req(self):
        m = 'GET'
        t = '/'
        h = 'google.com'
        hs = ['Content-Type: text/html']
        b = 'body'

        r = Request(m, t, h, hs, b)

        self.assertEqual(r._method, m)
        self.assertEqual(r._target, t)
        self.assertEqual(r._host, h)
        self.assertEqual(r._header, hs)
        self.assertEqual(r._body, b)

        self.assertEqual(bytes(r), f'{m} {t} HTTP/1.1\n'
                                   f'Host: {h}\n'
                                   f'{hs[0]}'
                                   f'\r\n\r\n{b}'.encode('utf-8'))

    def test_run_command_line(self):
        args = 'google.com', '-m', 'GET', '--header', 'Accept: text/html', \
               '--header', 'Date: Mon, 18 Nov 2019 17:17:42 GMT'
        testargs = ["httpclient.py", *args]
        with patch.object(sys, 'argv', testargs):
            self.assertIsNotNone(httpclient.main())

    def test_context_manager(self):
        try:
            with Client() as _:
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


if __name__ == '__main__':
    unittest.main()
