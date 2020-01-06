from collections.abc import Mapping


class HTTPHeadersDict(Mapping):
    def __init__(self):
        super().__init__()
        self._d = {}
        self._s = dict((k.lower(), k) for k in self._d)

    def __getitem__(self, k):
        return self._d[self._s[k.lower()]]

    def __setitem__(self, key, value):
        self._s[key.lower()] = key
        self._d[key] = value

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)
