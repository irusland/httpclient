import argparse
from urllib.parse import urlparse


class ArgParser:
    def __init__(self, default_port):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('url', help='Url to request')
        self.parser.add_argument('-p', '--port', type=int,
                                 help='Choose port',
                                 default=default_port)
        self.parser.add_argument('-m', '--method',
                                 help='send GET or POST request',
                                 default='GET')
        self.parser.add_argument('--path', help='Specify request path',
                                 default='/')
        self.parser.add_argument('-H', '--header', action='append',
                                 help='Specify request header',
                                 default=[])
        self.parser.add_argument('--body', help='Request body'),
        self.parser.add_argument('--output', help='Use "--output <FILE>" to '
                                                  'print save to file')
        self.parser.add_argument('--user-agent', help='Specify UA for request',
                                 default='Mozilla/5.0')
        self.parser.add_argument('--cookie', action='append',
                                 help='Specify request cookies',
                                 default=[])

    def parse(self):
        args = self.parser.parse_args()
        raw_url = args.url
        if not args.url.startswith('//'):
            raw_url = f'//{args.url}'
        url = urlparse(raw_url)
        args.url = url.netloc
        if url.path:
            args.path = url.path
        if not args.port:
            args.port = url.port
        args.header.append(f'User-Agent: {args.user_agent}')
        if args.cookie:
            args.header.append(f'Cookie: {";".join(args.cookie)}')
        return args
