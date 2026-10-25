"""python3 -m unittest discover -s scripts/literature"""
import unittest

import typo
from convert import convert, md2txt, numbered_prose, restanza

META = {'id': 't', 'title': 'ტ', 'author': 'ა', 'death_year': 1900, 'genre': 'ლექსი', 'shelf': 'პოეზია', 'lang': 'ka',
        'source': {'site': 'Georgian Wikisource', 'page': 'ტ', 'revision': 1}}


class Typo(unittest.TestCase):
    def test_rules(self):
        self.assertEqual(typo.typo('- სად ხარ,ჯაყო ?'), '— სად ხარ, ჯაყო?')
        self.assertEqual(typo.typo('ხელი, - დამდნარი'), 'ხელი, — დამდნარი')
        self.assertEqual(typo.typo('1858 - 1863 წ.'), '1858–1863 წ.')
        self.assertEqual(typo.typo('_ შენდობა, მამაო! _ გაუშვირა'), '— შენდობა, მამაო! — გაუშვირა')
        self.assertEqual(typo.typo('პატრიარქი ,, მარშიმუნი‘‘, და <<ძენი>>'), 'პატრიარქი „მარშიმუნი“, და «ძენი»')
        self.assertEqual(typo.typo('ადგილებში,, თოვლების'), 'ადგილებში,, თოვლების')  # a stray comma, not a quote

    def test_dehyphen(self):
        vocab = {'რომელიც': 3, 'მეფე-დედოფალი': 1}
        self.assertEqual(typo.dehyphen(f'რო{typo.WRAP}მელიც', vocab, True), 'რომელიც')
        self.assertEqual(typo.dehyphen(f'მეფე{typo.WRAP}დედოფალი', vocab, True), 'მეფე-დედოფალი')
        self.assertEqual(typo.dehyphen(f'უცნო{typo.WRAP}ბი', vocab, True), 'უცნო-ბი')  # unknown: the source's hyphen
        self.assertEqual(typo.dehyphen('დღე- და ღამე', vocab, True), 'დღე- და ღამე')


class Convert(unittest.TestCase):
    def test_stanzas_and_roundtrip(self):
        html = '<div class="poem"><p>ერთი, ორი<br>სამი<br><br>ოთხი<br>ხუთი</p></div>'
        md, txt = convert(html, META)
        self.assertIn('| ერთი, ორი\n| სამი\n\n| ოთხი\n| ხუთი', md)
        self.assertEqual(txt, 'ერთი, ორი\nსამი\n\nოთხი\nხუთი\n')
        self.assertEqual(md2txt(md), txt)

    def test_footnotes(self):
        html = '<p>ტექსტი<sup class="reference">[1]</sup> აქ.</p><ol class="references"><li>შენიშვნა</li></ol>'
        md, txt = convert(html, {**META, 'shelf': 'პროზა', 'genre': 'მოთხრობა'})
        self.assertIn('ტექსტი[^1] აქ.', md)
        self.assertIn('[^1]: შენიშვნა', md)
        self.assertTrue(txt.endswith('ტექსტი¹ აქ.\n\n∗ ∗ ∗\n\n¹ შენიშვნა\n'))


if __name__ == '__main__':
    unittest.main()


class Structure(unittest.TestCase):
    def test_restanza(self):
        lines = list('აბგდევზთ')
        out = restanza([('stanza', ['ქვესათაური'] + lines[:6]), ('stanza', lines[6:])], 4)  # subtitle glued on
        self.assertEqual([b[1] for b in out], [['ქვესათაური'], lines[:4], lines[4:]])
        out = restanza([('stanza', lines), ('stanza', ['1883 წ.'])], 4)  # a date standing alone stays last
        self.assertEqual([b[1] for b in out], [lines[:4], lines[4:], ['1883 წ.']])

    def test_numbered_prose(self):
        p = lambda *ls: ('para', list(ls))
        chapters = [p('1'), p('ა.'), p('2'), p('ბ.'), p('3'), p('გ.'), p('2'), p('ბ. უფრო გრძელი.')]
        self.assertEqual(numbered_prose(chapters), [('h', 3, '1'), p('ა.'), ('h', 3, '2'), p('ბ. უფრო გრძელი.'),
                                                    ('h', 3, '3'), p('გ.')])
        pages = [p('სიტყვა'), p('628'), p('მაინც თქვა.'), p('629'), p('— კი.'), p('630'), p('ბოლო.')]
        self.assertEqual(numbered_prose(pages), [p('სიტყვა მაინც თქვა.'), p('— კი.'), p('ბოლო.')])
