"""Import literature from pinned Georgian Wikisource revisions: manifest.json -> <id>/text.md, text.txt, source.json.

    python3 scripts/literature/import.py [--cache DIR] [--force] [id ...]   # fetch, convert, write
    python3 scripts/literature/import.py --derive [id ...]                 # text.md (hand-edited) -> text.txt, sha256

text.md (pandoc Markdown, YAML front matter) is canonical; text.txt is derived from it (md2txt) and is what the web
reader loads; source.json carries the provenance and both checksums (Web sync-library verifies `sha256`). A work is
imported when its manifest entry has `wikisource: {page, revision}` or `{page, parts: [{page, revision}, ...]}`.
An existing text.md is never overwritten without --force: after import, fixes go into text.md, then --derive.
--cache DIR reads/writes the parse responses as DIR/<id>.json (DIR/<id>.<n>.json for parts) instead of fetching.
"""
import argparse, datetime, glob, hashlib, json, os, random, re, sys, time, urllib.parse, urllib.request

import nplg, typo
from convert import convert, md2txt

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'datasets', 'literature')
FIXES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixes')  # <id>.tsv: wrong, right, source of the fix
API = 'https://ka.wikisource.org/w/api.php'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/136.0.0.0 Safari/537.36 (john@gmail.com)')  # Wikisource refuses requests without a contact: only this one

# Transcription typos in the pinned revisions: (wrong, right), each found exactly once; recorded in the front matter.
CORRECTIONS = {
    'iavnanam-ra-hkmna': [('ბილისიდან რომ აღმოსავლეთისკენ', 'თბილისიდან რომ აღმოსავლეთისკენ')],
    'khevisberi-gocha': [  # as anbani.db 86d3ae9
        ('მტერს.შეხვდა', 'მტერს შეხვდა'), ('ოსებიდა ნუგზარ', 'ოსები და ნუგზარ'), ('საალერსოდ?ნ', 'საალერსოდ?'),
        ('ალერსი?ნ', 'ალერსი?'), ('გახადა?ნ-ონისეს', 'გახადა? ონისეს'), ('3ხოლოდ მაშინ', 'მხოლოდ მაშინ'),
        ('დამ.ლული', 'დამალული'), ('სდებდნენ.     "', 'სდებდნენ.'), ('-  - მთები', '- მთები'),
        ('მოიცალtს', 'მოიცალეს')],
    # Latin keys typed in the wrong keyboard layout (Argon, 2026-10-26)
    'bashi-achuki': [('ჩAვკლათ', 'ჩავკლათ'), ('რ აც უნდა', 'რაც უნდა')],
    'gabaaseba-teimurazisa-da-rustvelisa': [('ქნა დ ა საკვირვალი', 'ქნა და საკვირვალი')],
    'mamis-mkvleli': [('ჩამოვიlა', 'ჩამოვიდა')],
    'lambalo-da-qasha': [('ჩადრებშI', 'ჩადრებში'), ('Aადრევაც', 'ადრევაც'), ('Uკვირდა', 'უკვირდა'), ('იშვიათI', 'იშვიათი'),
                         ('ტოXლიშვილი', 'თოხლიშვილი'), ('ლომბალოშI', 'ლომბალოში'), ('სიოზDდი', 'სიოზდი'),
                         ('ქუჩაშI', 'ქუჩაში'), ('შეშIნდი', 'შეშინდი'), ('ათIოდე', 'ათიოდე'),
                         ('ყრილიFფალავანი', 'ყრილი ფალავანი')],
}
DASH_HYPHENS = {'mamis-mkvleli'}  # 'word- word': this transcription types the dialogue dash as a hyphen
# Poems in regular stanzas whose source drops or misplaces the breaks: lines per stanza (Argon's per-poem review); a
# list: an irregular poem's own sizes in order (samshoblo: 3 lines + the 2-line refrain, last 2 + 2, then the date).
STANZAS = {'gandegili': 4, 'gogcha': 4, 'tornike-eristavi': 4, 'poeti': 4, 'tamar-mepis-sakhe-betaniis-eklesiashi': 6,
           'tano-tatano': 10, 'bazaletis-tba': 4, 'saqure': 6, 'nu-mtser': 4,
           'samshoblo-khevsurisa': [5, 5, 5, 5, 4, 1]}
TURNS = {'lambalo-da-qasha'}  # one scanned paragraph; '_' starts each dialogue turn: a paragraph per turn
# Layout slips and apparatus in the source HTML (no change to the work's text): (wrong, right), each found exactly once.
LAYOUT = {
    'achrdili': [('სცნობ,— <br />\n<br />\n”თვით', 'სცნობ,— <br />\n”თვით')],  # II's last line split off
    'gabaaseba-teimurazisa-da-rustvelisa': [('<br />\n213 ოთხი', '<br />\nოთხი')],  # a stanza number glued on
    'glakhis-naambobi': [('<p><br />\nპირვანდელი ვარიანტი მოთხრობისა “გლახის ნაამბობი” შესრულებულია 1859 წელს; ხოლო ბოლო '
                          'რედაქცია ეკუთვნის: I — VI თავები 1862 წელს, VII — XII თავები 1872 — 1873 წლებს. რედ.\n</p>', '')],  # editor's note
    'ramdenime-surati-anu-epizodi-qachaghis-tskhovrebidam': [('ათავისუფლე მონები, მიღწვიან', 'ათავისუფლე მონები,<br />\nმიღწვიან')],  # two lines (ვეფხისტყაოსანი)
    'irines-bedniereba': [('<p>ირინეს ბედნიერება <br />\nსურათი სოფლის ცხოვრებიდან ორ მოქმედებად <br />\nმოქმედნი პირნი <br />',
                           '<p>სურათი სოფლის ცხოვრებიდან ორ მოქმედებად <br />\n<br />\nმოქმედნი პირნი <br />')],  # title repeated
    'saghamo-gamosalmebisa': [('შეღამდა...<br />\nმარტო ვზი', 'შეღამდა... მარტო ვზი')],  # one line (NPLG, poetry.ge)
    'tano-tatano': [('დანაცარებო!<br />\n<br />\nბესარიონ გაბაშვილი (ბესიკი)<br />', 'დანაცარებო!<br />')],  # signature
}
LEGACY = str.maketrans('ÀÁÂÃÄÅÆÈÉÊËÌÍÏÐÑÒÓÔÖ×ØÙÚÛÜÝÞßàáãä', 'აბგდევზთიკლმნოპჟრსტუფქღყშჩცძწჭხჯჰ')


def fix_khevisberi(h):
    """Footnotes typed inline: digit markers, bodies as page-bottom lines (1, 2 in a legacy 8-bit font) -> notes."""
    notes = []
    for n in (1, 2):
        m = re.search(rf'\n</p><p>{n} ((?:[^\n]*[À-ä][^\n]*\n)+)', h)
        notes.append(' '.join(m.group(1).split()).translate(LEGACY))
        h = h[:m.start()] + '\n' + h[m.end():]  # the page break the note sat on: the paragraph goes on
    m = re.search(r'(?:</p><p><br />\n)*3 (ეს მოთხრობა[^\n]*)\n', h)
    notes.append(m.group(1))
    h = h[:m.start()] + h[m.end():]
    for n in (1, 2, 3):
        h = re.sub(rf'(?<=[ა-ჰ"”,.]){n}(?=\s)', f'<sup class="reference">[{n}]</sup>', h, count=1)
    return h + '<ol class="references">' + ''.join(f'<li>{x}</li>' for x in notes) + '</ol>'


def fix_kacia(h):
    """Ilia's two notes: ∗ markers in the text, bodies as bullets after the date; the third bullet is editorial, cut off."""
    lis = re.findall(r'<ul><li>([\s\S]*?)</li></ul>', h)
    assert len(lis) == 3 and lis[2].startswith('პირვანდელი ესკიზი'), lis
    h = re.sub(r'(<ul><li>[\s\S]*?</li></ul>\s*)+', '', h)
    for n in (1, 2):
        h = re.sub(r'(?<=[?,])∗', f'<sup class="reference">[{n}]</sup>', h, count=1)
    return h + '<ol class="references">' + ''.join(f'<li>{x}</li>' for x in lis[:2]) + '</ol>'


def fix_bedi(h):
    """Three {{Ref}}s and one {{Note}} to templates ka.wikisource lacks: only note 3 (a variant reading) survives."""
    refs = list(re.finditer(r'<a [^>]*title="თარგი:Ref[^"]*"[^>]*>([^<]*?)თარგი:Ref</a>', h))
    assert len(refs) == 3, len(refs)
    for i, m in reversed(list(enumerate(refs))):
        h = h[:m.start()] + m.group(1) + ('<sup class="reference">[1]</sup>' if i == 2 else '') + h[m.end():]
    m = re.search(r'<dl><dd>3\.<a [^>]*>თარგი:Note([^<]*)</a>([^<]*)</dd></dl>', h)
    return h[:m.start()] + h[m.end():] + f'<ol class="references"><li>{m.group(1) + m.group(2)}</li></ol>'


WRAPS = {}  # printed line-end hyphens the corpus could not settle: work -> [(token, joined)]
for _row in open(os.path.join(FIXES, 'wraps.tsv'), encoding='utf-8').read().splitlines()[1:]:
    _w, _t, _j = _row.split('\t')[:3]
    WRAPS.setdefault(_w, []).append((_t, _j))

FIXUPS = {'khevisberi-gocha': fix_khevisberi, 'kacia-adamiani': fix_kacia, 'bedi-kartlisa': fix_bedi}


def parse(page, revision, cache_file):
    if cache_file and os.path.exists(cache_file):
        data = json.load(open(cache_file, encoding='utf-8'))
    else:
        url = API + '?' + urllib.parse.urlencode({'action': 'parse', 'oldid': revision, 'prop': 'text|revid',
                                                  'format': 'json', 'formatversion': '2'})
        for attempt in range(4):
            time.sleep(random.uniform(0.8, 1.8))  # jittered pace
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
                    data = json.load(r)
                break
            except OSError:
                if attempt == 3:
                    raise
                time.sleep(5 * (attempt + 1))
        if cache_file:
            json.dump(data, open(cache_file, 'w', encoding='utf-8'), ensure_ascii=False)
    assert data['parse']['revid'] == revision, f'{page}: revision mismatch'
    return data['parse']['text']


def fetch_page(u, cache_file):
    """A plain page (an archived snapshot is fixed, so the URL is the pin); cached as fetched."""
    if cache_file and os.path.exists(cache_file):
        return open(cache_file, encoding='utf-8', errors='replace').read()
    for attempt in range(4):
        time.sleep(random.uniform(0.8, 1.8))
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=90) as r:
                raw = r.read().decode('utf-8', errors='replace')
            break
        except OSError:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    if cache_file:
        open(cache_file, 'w', encoding='utf-8').write(raw)
    return raw


def sha(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def write(work_id, md, record):
    d = os.path.join(ROOT, work_id)
    os.makedirs(d, exist_ok=True)
    txt = md2txt(md)
    open(os.path.join(d, 'text.md'), 'w', encoding='utf-8').write(md)
    open(os.path.join(d, 'text.txt'), 'w', encoding='utf-8').write(txt)
    record.update(sha256=sha(txt), sha256_md=sha(md))
    open(os.path.join(d, 'source.json'), 'w', encoding='utf-8').write(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    return txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ids', nargs='*')
    ap.add_argument('--cache')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--derive', action='store_true')
    a = ap.parse_args()
    works = [w for w in json.load(open(os.path.join(ROOT, 'manifest.json'), encoding='utf-8'))['works']
             if (w.get('wikisource') or w.get('nplg')) and (not a.ids or w['id'] in a.ids)]
    if a.derive:
        for w in works:
            src = os.path.join(ROOT, w['id'], 'source.json')
            write(w['id'], open(os.path.join(ROOT, w['id'], 'text.md'), encoding='utf-8').read(),
                  json.load(open(src, encoding='utf-8')))
        return
    texts = {f.split(os.sep)[-2]: open(f, encoding='utf-8').read() for f in glob.glob(os.path.join(ROOT, '*', 'text.txt'))}
    corpus = typo.vocabulary(texts.values())
    for w in works:
        d, ws = os.path.join(ROOT, w['id']), w.get('wikisource')
        if os.path.exists(os.path.join(d, 'text.md')) and not a.force:
            continue
        old = json.load(open(os.path.join(d, 'source.json'), encoding='utf-8')) if os.path.exists(os.path.join(d, 'source.json')) else {}
        cache = lambda suffix: a.cache and os.path.join(a.cache, f"{w['id']}{suffix}.json")
        if w.get('nplg'):  # the National Library's school page, from its Wayback snapshot
            raw = fetch_page(nplg.url(w['nplg']), a.cache and os.path.join(a.cache, w['id'] + '.htm'))
            html = nplg.work_html(raw, w['nplg'], w['shelf'] == 'პოეზია')
        elif ws.get('parts'):  # a work split into subpages: chapters in order, each under its heading
            html = ''.join(f"<h2>{p['page'].rsplit('/', 1)[1]}</h2>" + parse(p['page'], p['revision'], cache(f'.{i}'))
                           for i, p in enumerate(ws['parts']))
        else:
            html = parse(ws['page'], ws['revision'], cache(''))
        start = re.search(r'<h2[^>]*>(?:<span[^>]*></span>)?ტექსტი</h2>', html)
        if start:  # a 'ტექსტი' section: what precedes it is the page's apparatus (series box, editions, links)
            html = html[start.end():]
        html = re.sub(r'<b>\[\d{1,4}\]</b> ?', '', html)  # the printed edition's page numbers, bold in brackets
        html = re.sub(r'(?:<ul>\s*<li>\s*)+(?:<br\s*/?>\s*)*(?:</li>\s*</ul>\s*)+', '\n<p>∗</p>\n', html)  # empty bullet: section break
        if w['id'] in FIXUPS:
            html = FIXUPS[w['id']](html)
        if w['id'] in TURNS:
            html = re.sub(r'(?<=[.!?…»“"–—-])\s+_\s', '\n</p><p>_ ', html)
        if w['id'] in DASH_HYPHENS:
            html = re.sub(r'(?<=[ა-ჰ])- (?=[ა-ჰ"„])', ' — ', html)
        for wrong, right in LAYOUT.get(w['id'], []):
            assert html.count(wrong) == 1, (w['id'], wrong, html.count(wrong))
            html = html.replace(wrong, right)
        corrections = []
        for wrong, right in CORRECTIONS.get(w['id'], []):
            assert html.count(wrong) == 1, (w['id'], wrong, html.count(wrong))
            html = html.replace(wrong, right)
            corrections.append(f'{wrong} → {right}')
        tsv = os.path.join(FIXES, w['id'] + '.tsv')
        if os.path.exists(tsv):  # a proofread's typing errors: words, matched across the source's line wraps
            for row in open(tsv, encoding='utf-8').read().splitlines()[1:]:
                wrong, right = row.split('\t')[:2]
                pat = r'(?<![ა-ჰ])' + r'\s+'.join(map(re.escape, wrong.split())) + r'(?![ა-ჰ])'
                n = len(re.findall(pat, html))
                assert n == 1, (w['id'], wrong, n)
                html = re.sub(pat, lambda m: right, html)
                corrections.append(f'{wrong} → {right}')
        retrieved = old.get('retrieved') or datetime.date.today().isoformat()
        if w.get('nplg'):
            source = {'site': 'NPLG, ბიბლიოთეკა სკოლას (Wayback snapshot)', 'page': w['nplg']['page'],
                      'url': nplg.url(w['nplg']), 'snapshot': w['nplg']['snapshot']}
        else:
            source = {'site': 'Georgian Wikisource', 'page': ws['page']}
        if ws and ws.get('parts'):
            source['parts'] = ws['parts']
        elif ws:
            source.update(url=f"https://ka.wikisource.org/w/index.php?oldid={ws['revision']}", revision=ws['revision'])
        source['retrieved'] = retrieved
        licence = 'not stated by the NPLG page (the work is public domain)' if w.get('nplg') else 'CC BY-SA 4.0, Georgian Wikisource'
        meta = {'id': w['id'], 'title': w['title'], 'author': w['author'], 'death_year': w['death_year'],
                'genre': w['genre'], 'shelf': w['shelf'], 'lang': 'ka', 'source': source, 'corrections': corrections,
                'transcription': licence,
                'stanza_lines': STANZAS.get(w['id'])}
        meta['joins'] = WRAPS.get(w['id'], [])
        md, _ = convert(html, meta, corpus - typo.vocabulary([texts.get(w['id'], '')]))
        record = {'source': source['site'], 'page': source['page'],
                  **{k: v for k, v in source.items() if k in ('url', 'revision', 'parts', 'snapshot')},
                  'retrieved': retrieved, 'transcription_license': 'CC BY-SA 4.0' if ws else 'not stated',
                  'converter': 'scripts/literature/import.py'}
        if corrections:
            record['corrections'] = corrections
        txt = write(w['id'], md, record)
        print(f"{w['id']:42} {len(txt):>8} chars", file=sys.stderr)


if __name__ == '__main__':
    main()
