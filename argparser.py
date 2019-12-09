import argparse
from urllib.parse import urlparse


def parse(default_port):
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='Url to request')
    parser.add_argument('-p', '--port', type=int,
                        help='Choose port',
                        default=default_port)
    parser.add_argument('-m', '--method',
                        help='send GET or POST request',
                        choices=['GET', 'POST'],
                        default='GET')
    parser.add_argument('--path', help='Specify request path',
                        default='/')
    parser.add_argument('-H', '--header', action='append',
                        help='Specify request header',
                        default=[])
    parser.add_argument('--body', help='Request body'),
    parser.add_argument('--output', help='Use "--output <FILE>" to '
                                         'print save to file')
    parser.add_argument('--user-agent', help='Specify UA for request',
                        default='Mozilla/5.0 (Macintosh; Intel Mac OS X '
                                '10_15_1) AppleWebKit/605.1.15 (KHTML, '
                                'like Gecko) Version/13.0.3 Safari/605.1.15')
    parser.add_argument('--cookie', action='append',
                        help='Specify request cookies',
                        default=[])

    args = parser.parse_args()
    url = urlparse(args.url)
    args.url = url.netloc
    if url.path:
        args.path = url.path
    if not args.port:
        args.port = url.port
    args.header.append(f'User-Agent: {args.user_agent}')
    if args.cookie:
        args.header.append(f'Cookie: {";".join(args.cookie)}')
    return args
