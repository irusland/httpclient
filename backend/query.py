class Request:
    def __init__(self, method, target, host, add_header=None, body=None,
                 no_redir=True, form=None):
        self.method = method
        self.target = target
        self.host = host
        self.headers = add_header or []
        self.body = body or '&'.join(form or [])
        self.no_redirect = no_redir

        req = (f'{method} {target} HTTP/1.1\n'
               f'Host: {host}')
        self.headers.append(f'Accept: */*')
        if self.body:
            self.headers.append(f'Content-Length: {len(self.body)}')

        if self.headers:
            headers = '\n'.join(h for h in self.headers)
        else:
            headers = ''
        req = f'{req}\n{headers}\r\n\r\n{self.body if self.body else ""}\r\n'
        self.request = req

    def __str__(self):
        return self.request

    def __bytes__(self):
        return self.request.encode('utf-8')


class Response:
    def __init__(self, status, reason, headers=None, body=''):
        if headers is None:
            headers = {}
        self.status = status
        self.reason = ' '.join(reason)
        self.headers = headers
        self.body = body

    def __str__(self):
        return '\n'.join(
            f'{k}: {str(v)}'
            for k, v in self.__dict__.items())
