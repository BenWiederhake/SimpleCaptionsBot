#!/usr/bin/env python3

import bot
import unittest


class CaptionTests(unittest.TestCase):
    def assertCaption(self, request, *args):
        expected = bot.CaptionRequest(*args)
        actual = bot.parse_caption(request)
        self.assertEqual(repr(expected), repr(actual))

    def assertMultiple(self, captions):
        for i, (request, *caption_args) in enumerate(captions):
            with self.subTest(i=i, request=request):
                self.assertCaption(request, *caption_args)

    def testEmpty(self):
        pass

    def testSimple(self):
        self.assertCaption('asdf\nqwer', 'asdf', 'qwer', 0, 0)

    def testBattery(self):
        self.assertMultiple([
            ('asdf\nqwer', 'asdf', 'qwer', 0, 0),
            ('asdf\nqwer', 'asdf', 'qwer', 0, 0),
            ('asdf\nqwer', 'asdf', 'qwer', 0, 0),
        ])


if __name__ == '__main__':
    unittest.main()
