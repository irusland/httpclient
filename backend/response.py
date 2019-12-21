

class Response:
    def __init__(self, status, reason, headers=None, body=None):
        self.status = status
        self.reason = ' '.join(reason)
        self.headers = headers
        self.body = body

    def __str__(self):
        limit = 64 * 1024
        return '\n'.join(
            f'{k}: '
            f'{str(v) if not limit else str(v)[:limit]}'
            for k, v in self.__dict__.items())
