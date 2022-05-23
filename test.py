#!/usr/bin/env python3

import bot
import secret
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
        self.assertCaption('asdf\n\nqwer', 'asdf', 'qwer', 0, 0)

    def testBattery(self):
        self.assertMultiple([
            (f'asdf\n\nqwer', 'asdf', 'qwer', 0, 0),
            (f'asdf\nqwer', '', 'asdf\nqwer', 0, 0),
            (f'foobar', '', 'foobar', 0, 0),
            (f'@{secret.BOT_NAME} Bro', '', 'Bro', 0, 0),
            (f'@{secret.BOT_NAME} Henlo\n\nWordl', 'Henlo', 'Wordl', 0, 0),
            (f'50\nHenlo\n\nWordl\n30', 'Henlo', 'Wordl', 50, 30),
            (f'50\nHenlo\n\nWordl @{secret.BOT_NAME}\n30', 'Henlo', f'Wordl @{secret.BOT_NAME}', 50, 30),
            (f'/caption\nCool!\n\nBut why?!', 'Cool!', 'But why?!', 0, 0),
            (f'/caption@{secret.BOT_NAME}\nCool!\n\nBut why?!', 'Cool!', 'But why?!', 0, 0),
            (f'@{secret.BOT_NAME}\nCool!\n\nBut why?!', 'Cool!', 'But why?!', 0, 0),
            (f'@{secret.BOT_NAME} @{secret.BOT_NAME}\n\nBest bot evar', f'@{secret.BOT_NAME}', 'Best bot evar', 0, 0),
            (f'@{secret.BOT_NAME}\n@{secret.BOT_NAME}\n\nBest bot evar', f'@{secret.BOT_NAME}', 'Best bot evar', 0, 0),
            (f'@{secret.BOT_NAME} 10\n@{secret.BOT_NAME}\n\nBest bot evar\n20', f'@{secret.BOT_NAME}', 'Best bot evar', 10, 20),
            (f'@{secret.BOT_NAME} 30\n50\n\n70\n90', '50', '70', 30, 90),
            (f'Oof\n10', '', 'Oof', 0, 10),
            (f'', '', '', 0, 0),
            (f'@{secret.BOT_NAME}\n30\nFoo\n\nBar\n\nBaz\n90', 'Foo', 'Bar\nBaz', 30, 90),
        ])


if __name__ == '__main__':
    unittest.main()
