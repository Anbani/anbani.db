"""python3 -m unittest discover -s scripts/literature"""
import unittest

import typo
from convert import convert, md2txt

META = {'id': 't', 'title': 'ტ', 'author': 'ა', 'death_year': 1900, 'genre': 'ლექსი', 'shelf': 'პოეზია', 'lang': 'ka',
        'source': {'site': 'Georgian Wikisource', 'page': 'ტ', 'revision': 1}}


class Typo(unittest.TestCase):
    def test_rules(self):
        self.assertEqual(typo.typo('- სად ხარ,ჯაყო ?'), '— სად ხარ, ჯაყო?')
        self.assertEqual(typo.typo('ხელი, - დამდნარი'), 'ხელი, — დამდნარი')
        self.assertEqual(typo.typo('1858 - 1863 წ.'), '1858–1863 წ.')

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
