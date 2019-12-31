import logging
import sys

from backend.query import Request
from backend.client_backend import Client


def main():
    args = Client.parse()
    logging.info(args)
    try:
        with Client(timeout=1) as client:
            client.connect(args.url, args.port)
            req = Request(args.method, args.path, args.url,
                          add_header=args.header, body=args.body,
                          no_redir=args.no_redirects, form=args.form)
            res = client.request(req)
            body = client.parse_res(res)
            client.output(res, args.output, body)

    except Exception as e:
        sys.stderr.write(str(e))


if __name__ == '__main__':
    main()
