import io
import multiprocessing
import re
import socket
import sys
import time
import unittest
from contextlib import redirect_stdout

from backend.client_backend import Client
from backend.query import Request, Response
from aiohttp import web


class AioHTTPTests(unittest.TestCase):
    def test_post_form(self):
        server = multiprocessing.Process(target=self.aiohttp_server_run)
        server.start()
        time.sleep(1)

        form = ['a=a', 'b=b', 'key=val']
        args = {'body': None,
                'cookie': [],
                'form': form,
                'header': ['User-Agent: httpclient/0.4.5',
                           'Connection: keep-alive'],
                'max_redirects': 10,
                'method': 'POST',
                'no_redirects': False,
                'output': None,
                'path': '/post',
                'port': None,
                'timeout': 1,
                'url': 'a.com',
                'user_agent': 'httpclient/0.4.5'}

        req = Request(args['method'], args['path'], args['url'],
                      add_header=args['header'], body=args['body'],
                      no_redir=args['no_redirects'], form=args['form'],
                      max_redir=args['max_redirects'])

        with Client() as c:
            time.sleep(1)
            f = io.BytesIO()
            with redirect_stdout(f):
                while True:
                    try:
                        c.connect('localhost', 8080)
                        break
                    except socket.error:
                        time.sleep(1)
                c.request(req, sys.stdout)

        server.terminate()

        r = re.compile(
            r'-+?.+?\r\n'
            r'Content-Disposition: form-data; name=\"(?P<name>.+?)\"\r\n'
            r'\r\n'
            r'(?P<value>.+?)\r\n')

        body = f.getvalue().decode('utf-8')
        found = r.findall(body)
        res_form = '&'.join('='.join(x) for x in found)
        self.assertEqual(res_form, '&'.join(form))

    def aiohttp_server_run(self):
        app = web.Application()
        app.add_routes([
            web.get('/', self.handle_index),
            web.post('/post', self.handle_post_form),
        ])
        web.run_app(app)

    async def handle_index(self, request):
        text = 'index'
        return web.Response(text=text)

    async def handle_post_form(self, request):
        if request.body_exists:
            body = await request.read()
            return web.Response(text=body.decode('utf-8'))
        self.fail()

    def get_res(self, s, req):
        try:
            s.sendall(req)
        except Exception as e:
            print(e)
            pass

        res = Response()
        break_out = False
        while not break_out:
            try:
                while not break_out:
                    line = s.recv(Client.MAX_LINE)
                    split = Response.split_keep_sep(line, b'\r\n')
                    for spl in split:
                        if res.dynamic_fill(spl):
                            break_out = True
                            break
            except socket.timeout:
                pass
        return res

    def test_get_index(self):
        server = multiprocessing.Process(target=self.aiohttp_server_run)
        server.start()
        time.sleep(1)
        ip = ('localhost', 8080)
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(ip)
                break
            except socket.error:
                time.sleep(1)

        req = b'GET / HTTP/1.1\r\n\r\n'
        res = self.get_res(s, req)
        s.close()
        server.terminate()

        self.assertEqual(res.status, '200')
        self.assertEqual(res.reason, 'OK')


if __name__ == '__main__':
    unittest.main()
