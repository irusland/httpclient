import argparse
import sys
from urllib.parse import urlparse


class AParser:
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('url', help='Url to request')
        self.parser.add_argument('-m', '--method',
                                 help='send GET or POST request',
                                 choices=['GET', 'POST'],
                                 default='GET')
        self.parser.add_argument('-F', '--form', action='append',
                                 help='Form-data',
                                 default=[])
        self.parser.add_argument('-H', '--header', action='append',
                                 help='Specify request header',
                                 default=[])
        self.parser.add_argument('--body', help='Request body'),
        self.parser.add_argument('--user-agent', help='Specify UA for request',
                                 default='httpclient/0.4.5')
        self.parser.add_argument('--cookie', action='append',
                                 help='Specify request cookies',
                                 default=[])
        self.parser.add_argument('-o', '--output',
                                 default='-',
                                 help='Use "--output <FILENAME>" to '
                                      'print save to file')
        self.parser.add_argument('--no-redirects', action='store_true')

    def parse(self):
        args = self.parser.parse_args()
        url = urlparse(args.url)
        args.url = url.netloc.split(':')[0]
        args.path = url.path
        args.port = url.port
        args.header.append(f'User-Agent: {args.user_agent}')
        args.header.append(f'Connection: keep-alive')
        if args.cookie:
            args.header.append(f'Cookie: {";".join(args.cookie)}')
        if args.form:
            args.method = 'POST'
        return args
