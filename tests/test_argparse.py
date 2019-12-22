import sys
import unittest

from argparser import AParser


class ArgParseTestCase(unittest.TestCase):
    def test_parse(self):
        sys.argv = ['httpclient.py',
                    'http://urgu.org/c.png']
        p = AParser()
        args = p.parse()

        self.assertEqual(args.url, 'urgu.org')
        self.assertEqual(args.path, '/c.png')
        self.assertEqual(args.method, 'GET')
        self.assertEqual(args.output, '-')
        self.assertEqual(args.user_agent, 'httpclient/0.4.5')


if __name__ == '__main__':
    unittest.main()
