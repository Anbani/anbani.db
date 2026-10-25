"""Wikisource parse HTML -> canonical text.md (pandoc Markdown) + derived text.txt.

text.md: YAML front matter, `##` headings, prose paragraphs, verse as pandoc line blocks (`| `, one per stanza),
`* * *` scene breaks, *italic*, footnotes `[^n]`. text.txt (derived; the website reader's input): one block per
paragraph / stanza / heading, a blank line between blocks, markup stripped, NFC.

Wikisource transcribes the same thing several ways, so structure is read from lines, not tags: every <p>, <br> and
poem <div> ends a line; an empty line (two <br>, an empty <p>, a <p> opening with <br>) ends a group. A group of long
lines (mean > 110 chars) is prose, one paragraph per line; any other group of 2+ lines is a stanza on the poetry shelf
and inside a poem <div>, else a paragraph whose lines are kept as hard breaks.
"""
import typo
import json, re, sys, unicodedata
from html.parser import HTMLParser

NUMBERED = re.compile(r'^([IVXLCDM]+|\d+)\.?$|^([IVXLCDM]+|\d+)\s+(თავი|ნაწილი|კარი)$|^(თავი|ნაწილი|კარი|წიგნი)\s+\S+$')
VOID = {'br', 'img', 'hr', 'wbr', 'meta', 'link', 'input', 'source'}
DROP_TAGS = {'style', 'script', 'figure', 'table', 'sup', 'math', 'noscript'}
DROP_CLASSES = {'mw-editsection', 'noprint', 'navbox', 'toc', 'metadata', 'sistersitebox', 'ws-noexport', 'mw-empty-elt',
                'catlinks', 'printfooter', 'thumb', 'gallery', 'mw-cite-backlink'}
# 'თავი II. ქართლად შემოსლვაჲ…' (a titled chapter), or a front or back section standing alone
CHAPTER = re.compile(r'^(თავი|ნაწილი|კარი)\s+([IVXLCDM]+|\d+)\.\s+\S|^(შესავალი|წინასიტყვაობა|ბოლოსიტყვაობა|პროლოგი|ეპილოგი)$')
TAIL = re.compile(r'^(რესურსები ინტერნეტში|სქოლიო|სქოლიოები|შენიშვნები|წყარო|წყაროები|ლიტერატურა|იხილეთ აგრეთვე)$')
CREDIT = re.compile(r'^(გადამწერი|წყარო:|ტექსტი გადმოწერილია|თარგი:)')
LONG = 110
SOFT = '\x01'
WRAP = typo.WRAP


class Walker(HTMLParser):
    """Flattens parse HTML to tokens: ('text', s) ('nl',) ('blank',) ('h', level, text) ('hr',) ('poem',) ('/poem',)
    ('i',) ('/i',) ('note', n). Footnote bodies (ol.references) go to self.notes."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tokens, self.stack, self.skip = [], [], 0
        self.notes, self.note_n, self.ref_depth, self.ref_li, self.ref_buf = {}, 0, 0, 0, ''
        self.h, self.h_text = 0, ''

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            if not self.skip and not self.ref_depth:
                self.tokens.append(('br',) if tag == 'br' else ('hr',) if tag == 'hr' else ('nop',))
            return
        a = dict(attrs)
        cls = set((a.get('class') or '').split())
        kind = None
        if self.skip:
            kind = 'skip'
        elif tag == 'sup' and 'reference' in cls:
            self.note_n += 1
            self.tokens.append(('note', self.note_n))
            kind = 'skip'
        elif tag == 'ol' and 'references' in cls:
            kind = 'refs'
            self.ref_depth += 1
        elif self.ref_depth and tag == 'li':
            kind = 'refli'
            self.ref_li += 1
            self.ref_buf = ''
        elif tag in DROP_TAGS or cls & DROP_CLASSES or (tag == 'span' and 'mw-cite-backlink' in cls):
            kind = 'skip'
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            kind, self.h, self.h_text = 'h', int(tag[1]), ''
        elif tag == 'div' and 'poem' in cls:
            kind = 'poem'
            self.tokens.append(('poem',))
        elif tag in ('p', 'dd', 'li', 'blockquote', 'div', 'center'):
            kind = 'block'
            self.tokens.append(('nl',))
            if tag == 'p':
                self.tokens.append(('p',))
        elif tag in ('i', 'em'):
            kind = 'i'
            self.tokens.append(('i',))
        if kind == 'skip':
            self.skip += 1
        self.stack.append((tag, kind))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        while self.stack:
            t, kind = self.stack.pop()
            if kind == 'skip':
                self.skip -= 1
            elif kind == 'refs':
                self.ref_depth -= 1
            elif kind == 'refli':
                self.notes[self.ref_li] = clean(self.ref_buf).lstrip('↑ ').strip()
            elif kind == 'h':
                self.tokens.append(('h', self.h, clean(self.h_text)))
                self.h = 0
            elif kind == 'poem':
                self.tokens.append(('/poem',))
            elif kind == 'block':
                self.tokens.append(('nl',))
                if t == 'p':
                    self.tokens.append(('/p',))
            elif kind == 'i':
                self.tokens.append(('/i',))
            if t == tag:
                break

    def handle_data(self, data):
        if self.ref_depth:
            if self.ref_li and not self.skip:
                self.ref_buf += data
            return
        if self.skip:
            return
        if self.h:
            self.h_text += data
            return
        self.tokens.append(('text', data))


def clean(s):
    s = unicodedata.normalize('NFC', s.replace(SOFT, ' ').replace('\xa0', ' ').replace('​', '').replace('­', ''))
    return re.sub(r'\s+', ' ', s).strip()


def clean_soft(s):
    """clean() that keeps SOFT newlines (trimmed of spaces around them, none at the ends)."""
    parts = [clean(p) for p in s.split(SOFT)]
    return SOFT.join(p for p in parts if p)


def lines_of(tokens):
    """Tokens -> items: ('line', text, in_poem) | ('blank',) | ('h', level, text) | ('hr',)."""
    items, cur, italic, poem, p_open_empty = [], '', False, 0, False

    def end(blank_if_empty=False):
        nonlocal cur
        t = clean_soft(cur)
        if italic and t and t.count('*') % 2:
            t += '*'
        if t:
            items.append(('line', t, poem > 0))
        elif blank_if_empty:
            items.append(('blank',))
        cur = '*' if italic and t else ''

    prev = None
    for tok in tokens:
        k = tok[0]
        if k == 'text':
            # a raw newline inside running text is the wikitext's own line: SOFT, resolved in blocks_of
            cur += tok[1].replace('\n', SOFT) if tok[1].strip() else tok[1].replace('\n', ' ')
            if tok[1].strip():
                prev = 'text'
            continue
        elif k == 'i':
            cur += '*'
            italic = True
        elif k == '/i':
            cur = cur.rstrip()
            cur = cur[:-1] if cur.endswith('*') else cur + '*'
            italic = False
        elif k == 'note':
            cur += f'[^{tok[1]}]'
        elif k == 'br':
            had = bool(clean(cur))
            end()
            # two <br> with nothing between, or a <p> opening with <br>: a blank line
            if not had and prev in ('br', 'p'):
                items.append(('blank',))
            prev = 'br'
            continue
        elif k == 'nl':
            end()
            if prev != 'p':
                prev = 'nl'
            continue
        elif k == 'p':
            end()
            p_open_empty = True
            items.append(('pstart',))
        elif k == '/p':
            end()
            if items and items[-1][0] == 'pstart':  # an empty <p>: blank line
                items[-1] = ('blank',)
        elif k == 'poem':
            end()
            items.append(('blank',))
            poem += 1
        elif k == '/poem':
            end()
            items.append(('blank',))
            poem -= 1
        elif k == 'h':
            end()
            items.append(('blank',))
            if tok[2]:
                items.append(('h', tok[1], tok[2]))
        elif k == 'hr':
            end()
            items.append(('hr',))
        prev = k
    end()
    # a <p> whose first content is a <br> opens with a blank line
    out = []
    for i, it in enumerate(items):
        if it[0] == 'pstart':
            continue
        out.append(it)
    return out


DIALOGUE = re.compile(r'^[-—–_]\s?(?=\S)')


def unwrap(text, verse_shelf):
    """A line holding SOFT newlines: long segments are paragraphs of their own; short ones are the printed page's line
    wraps, joined back into paragraphs (a word split as `ა-` + newline is joined without the space; a dialogue dash
    opens a new paragraph). On the poetry shelf short segments are verse lines."""
    segs = [clean(s) for s in text.split(SOFT)]
    segs = [s for s in segs if s]
    if not segs:
        return []
    if verse_shelf or sorted(len(s) for s in segs)[len(segs) // 2] > LONG:
        return [[s] for s in segs]
    paras, cur, prev = [], '', ''
    full = sorted(len(s) for s in segs)[len(segs) * 3 // 4]  # a full printed line
    for s in segs:
        # the printed paragraph's last line: short and closing a sentence
        ended = prev and len(prev) < 0.7 * full and re.search(r'[.!?…:»“"]$', prev)
        ended = ended or (prev and len(prev) < 40 and prev.endswith(':'))  # a lead-in ('თქვა რუქამ არაკი:') + title
        prev = s
        if NUMBERED.match(s) and len(s) <= 30:  # a chapter numeral glued to its first line ('III' + newline + text)
            if cur:
                paras.append(cur)
            paras.append(s)
            cur, prev = '', ''
            continue
        if cur and (DIALOGUE.match(s) or ended):
            paras.append(cur)
            cur = s
        elif cur.endswith('-') and not cur.endswith(' -'):
            cur = cur[:-1] + WRAP + s  # hyphen at a printed line's end: typo.dehyphen decides join or compound
        else:
            cur = f'{cur} {s}' if cur else s
    if cur:
        paras.append(cur)
    return [[p] for p in paras]


def blocks_of(items, verse_shelf):
    blocks, group = [], []

    def flush():
        nonlocal group
        if not group:
            return
        texts = [g[1] for g in group]
        in_poem = any(g[2] for g in group)
        if any(SOFT in t for t in texts):
            if verse_shelf:
                texts = [l[0] for t in texts for l in unwrap(t, True)]
            else:
                for t in texts:
                    blocks.extend(('para', p) for p in unwrap(t, False))
                group = []
                return
        mean = sum(len(t) for t in texts) / len(texts)
        if mean > LONG:
            blocks.extend(('para', [t]) for t in texts)
        elif verse_shelf:
            blocks.append(('stanza', texts))
        elif in_poem and len(texts) >= 3 and max(len(t) for t in texts) < 70:
            blocks.append(('stanza', texts))  # verse quoted in prose
        else:
            blocks.extend(('para', [t]) for t in texts)  # dialogue, cast lists, a play's speaker + speech
        group = []

    for it in items:
        if it[0] == 'line':
            group.append(it)
        elif it[0] == 'blank':
            flush()
        else:
            flush()
            blocks.append(it)
    flush()
    return blocks


def split_numbered(blocks):
    """A numbered divider inside a block (a source without blank lines: subtitle, dedication, 'I', first stanza) ends
    the block there and stands alone. Arabic numbers stay: on the poetry shelf they number stanzas (tidy drops them)."""
    out = []
    for b in blocks:
        if b[0] not in ('para', 'stanza') or len(b[1]) < 2:
            out.append(b)
            continue
        cur = []
        for line in b[1]:
            if NUMBERED.match(line.strip('*')) and len(line) <= 12 and not re.fullmatch(r'\d+\.?', line):  # not stanza nos
                if cur:
                    out.append((b[0], cur))
                out.append((b[0], [line]))
                cur = []
            else:
                cur.append(line)
        if cur:
            out.append((b[0], cur))
    return out


def split_dividers(b):
    """A section-break line (∗) inside a block: the block ends there, the break stands alone."""
    out, cur = [], []
    for line in b[1]:
        if line.strip() in ('∗', '*', '⁂', '∗ ∗ ∗', '* * *'):
            if cur:
                out.append((b[0], cur))
            out.append((b[0], [line.strip()]))
            cur = []
        else:
            cur.append(line)
    if cur:
        out.append((b[0], cur))
    return out


def restanza(blocks, n):
    """A poem in n-line stanzas: each run of stanza blocks between headings is re-cut into n-line stanzas when its
    lines add up (one line left over, a subtitle or a date, stands alone). n a list: the poem's own stanza sizes in
    order (an irregular poem with no headings); its lines must add up exactly."""
    if isinstance(n, list):
        lines = [l for b in blocks for l in b[1]]
        if any(b[0] != 'stanza' for b in blocks) or len(lines) != sum(n):
            raise ValueError(f'stanza sizes {n} do not fit {len(lines)} lines')
        cuts = [sum(n[:i]) for i in range(len(n) + 1)]
        return [('stanza', lines[a:b]) for a, b in zip(cuts, cuts[1:])]
    out, run = [], []

    def flush():
        lines = [l for b in run for l in b[1]]
        extra = len(lines) % n
        if lines and extra in (0, 1) and len(lines) > n:
            head = tail = []
            if extra:  # the leftover: a line standing alone at an end, else one with a digit (a date), else the first
                alone = [len(run[0][1]) == 1, len(run[-1][1]) == 1]
                if alone[1] and not alone[0] or alone == [False, False] and re.search(r'\d', lines[-1]) and \
                        not re.search(r'\d', lines[0]):
                    lines, tail = lines[:-1], [('stanza', lines[-1:])]
                else:
                    head, lines = [('stanza', lines[:1])], lines[1:]
            out.extend(head + [('stanza', lines[i:i + n]) for i in range(0, len(lines), n)] + tail)
        else:  # block by block
            out.extend(x for b in run for x in ([('stanza', b[1][i:i + n]) for i in range(0, len(b[1]), n)]
                                                if len(b[1]) > n and len(b[1]) % n == 0 else [b]))
        run.clear()

    for b in blocks:
        if b[0] == 'stanza' and not (len(b[1]) == 1 and NUMBERED.match(b[1][0].strip('*'))):
            run.append(b)
        else:
            flush()
            out.append(b)
    flush()
    return out


def numbered_prose(blocks):
    """Prose with bare arabic numbers as paragraphs: from 1 or 2 up, chapter numbers (headings; a chapter the source
    repeats keeps its longest copy); from far above, the scan's page numbers (dropped, the paragraph they cut rejoined)."""
    num = lambda b: b[0] == 'para' and len(b[1]) == 1 and re.fullmatch(r'\d{1,4}', b[1][0].strip(' *'))
    nums = [int(b[1][0].strip(' *')) for b in blocks if num(b)]
    if len(nums) < 3:
        return blocks
    if min(nums) <= 2:
        chapters, order, cur = {}, [], None
        head = []
        for b in blocks:
            if num(b):
                cur = b[1][0].strip(' *')
                if cur not in chapters:
                    order.append(cur)
                    chapters[cur] = []
                chapters[cur].append([])
            elif cur is None:
                head.append(b)
            else:
                chapters[cur][-1].append(b)
        out = head
        for n in order:
            out.append(('h', 3, n))
            out.extend(max(chapters[n], key=lambda body: sum(len(' '.join(x[1])) for x in body if x[0] == 'para')))
        return out
    if min(nums) > 20:
        out, glue = [], False
        for b in blocks:
            if num(b):
                glue = bool(out) and out[-1][0] == 'para' and not re.search(r'[.!?…»"”:]$', out[-1][1][-1])
                continue
            if glue and b[0] == 'para':
                out[-1] = ('para', out[-1][1][:-1] + [out[-1][1][-1] + ' ' + b[1][0]] + b[1][1:])
            else:
                out.append(b)
            glue = False
        return out
    return blocks


def tidy(blocks, title, verse_shelf, play=False, stanza_lines=None):
    out = []
    blocks = split_numbered(blocks)
    blocks = [x for b in blocks for x in (split_dividers(b) if b[0] in ('para', 'stanza') else [b])]
    if not verse_shelf:
        blocks = numbered_prose(blocks)
    if stanza_lines:
        blocks = restanza(blocks, stanza_lines)
    for b in blocks:
        if b[0] in ('para', 'stanza'):
            lines = [l for l in b[1] if l and not CREDIT.match(l)]
            if not lines:
                continue
            text = ' '.join(lines)
            if re.fullmatch(r'[*∗⁂\s.]+|\{\\displaystyle[^}]*\}', text):
                out.append(('hr',))
                continue
            first = lines[0].strip('*')
            if verse_shelf and re.fullmatch(r'\d+\.?', first):
                lines = lines[1:]  # a stanza's own number (Archil's 1., 2., …) is apparatus, not a heading
                if not lines:
                    continue
                text = ' '.join(lines)
            if len(lines) == 1 and (NUMBERED.match(text.strip('*')) and len(text) <= 30 or
                                    CHAPTER.match(text.strip('*')) and len(text) <= 120):
                out.append(('h', 3, text.strip('*')))
                continue
            if len(lines) > 1 and NUMBERED.match(lines[0].strip('*')) and len(lines[0]) <= 12:
                out.append(('h', 3, lines[0].strip('*')))
                lines = lines[1:]
            if not any(x[0] in ('para', 'stanza') for x in out) and len(lines) == 1 and title and \
                    re.sub(r'[\s\-–—?!.*“”"]', '', text) == re.sub(r'[\s\-–—?!.*“”"]', '', title):
                continue  # the page repeats the work's title
            # prose (not a play): a short line standing alone, no closing punctuation, after text = a section title
            if not verse_shelf and not play and b[0] == 'para' and len(lines) == 1 and len(text) <= 50 and \
                    not re.search(r'[.,:;!?…»“”"—–\-)]$', text) and not DIALOGUE.match(text) and \
                    out and out[-1][0] in ('para', 'stanza'):
                out.append(('h', 4, text.strip('*')))
                continue
            out.append((b[0], lines))
        elif b[0] == 'h':
            if TAIL.match(b[2]):
                break
            out.append(b)
        else:
            out.append(b)
    res = []
    for b in out:
        if b[0] == 'hr' and (not res or res[-1][0] == 'hr'):
            continue
        res.append(b)
    while res and res[-1][0] in ('hr', 'h'):
        res.pop()
    # one-line verse lines in a row on the poetry shelf (double-spaced transcription with no stanza signal): one block
    return res


def esc(s):
    s = re.sub(r'([\\`<>#|\[\]])', r'\\\1', s)
    s = re.sub(r'\\\[\^(\d+)\\\]', r'[^\1]', s)  # keep footnote refs live
    s = re.sub(r'^([-+]|\d+[.)])(\s)', r'\\\1\2', s)
    return s


SUP = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')


def plain(s):
    s = re.sub(r'\[\^(\d+)\]', lambda m: m.group(1).translate(SUP), s)
    return s.replace('*', '') if s.count('*') % 2 == 0 else s


def render(meta, blocks, notes):
    q = lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, (str, list, dict)) else str(v)
    fm = ['---'] + [f'{k}: {q(meta[k])}' for k in ('id', 'title', 'author', 'death_year', 'genre', 'shelf', 'lang')]
    fm += ['source:'] + [f'  {k}: {q(v)}' for k, v in meta['source'].items()]
    if meta.get('corrections'):
        fm += ['corrections:'] + [f'  - {q(c)}' for c in meta['corrections']]
    fm += ['license:', f'  work: {q("public domain in Georgia (author died %s)" % meta["death_year"])}',
           f'  transcription: {q(meta.get("transcription", "CC BY-SA 4.0, Georgian Wikisource"))}', '---', '', '']
    md, txt = [], []
    rank = {lv: i + 1 for i, lv in enumerate(sorted({b[1] for b in blocks if b[0] == 'h'}))}  # top level -> '#'
    for b in blocks:
        if b[0] == 'h':
            md.append('#' * min(rank[b[1]], 3) + ' ' + esc(b[2]))
            txt.append(plain(b[2]))
        elif b[0] == 'hr':
            md.append('* * *')
            txt.append('∗ ∗ ∗')
        elif b[0] == 'stanza':
            md.append('\n'.join('| ' + esc(l) for l in b[1]))
            txt.append('\n'.join(plain(l) for l in b[1]))
        else:
            md.append('\\\n'.join(esc(l) for l in b[1]))
            txt.append('\n'.join(plain(l) for l in b[1]))
    used = {int(n) for b in blocks if b[0] != 'hr' for l in (b[1] if b[0] != 'h' else [b[2]]) for n in re.findall(r'\[\^(\d+)\]', l)}
    if used:
        md.append('\n'.join(f'[^{n}]: {esc(notes.get(n, ""))}' for n in sorted(used)))
        txt.append('∗ ∗ ∗')
        txt += [f'{str(n).translate(SUP)} {plain(notes.get(n, ""))}' for n in sorted(used)]
    return ('\n'.join(fm) + '\n\n'.join(md) + '\n',
            unicodedata.normalize('NFC', '\n\n'.join(t for t in txt if t.strip())) + '\n')


def convert(html, meta, vocab=None):
    w = Walker()
    w.feed(html)
    verse = meta['shelf'] == 'პოეზია'
    blocks = tidy(blocks_of(lines_of(w.tokens), verse), meta["title"], verse, meta["genre"] == "პიესა",
                  meta.get('stanza_lines'))
    blocks = [(b[0], [typo.dehyphen(l, vocab, b[0] == 'para') for l in b[1]]) if b[0] in ('para', 'stanza') else b
              for b in blocks]
    for token, joined in meta.get('joins', []):  # broken words a proofread found: every occurrence, whole tokens only
        pat = re.compile(r'(?<![ა-ჰ-])' + re.escape(token) + r'(?![ა-ჰ-])')
        blocks = [(b[0], [pat.sub(joined, l) for l in b[1]]) if b[0] in ('para', 'stanza') else b for b in blocks]
    blocks, notes = typo.apply(blocks, w.notes)
    md, txt = render(meta, blocks, notes)
    assert md2txt(md) == txt, meta['id']  # text.txt is derivable from text.md alone
    return md, txt


def md2txt(md):
    """text.md -> text.txt for the Markdown this module writes (edit text.md by hand in the same subset)."""
    body = md.split('\n---\n', 1)[1] if md.startswith('---\n') else md
    unesc = lambda s: plain(re.sub(r'\\(.)', r'\1', s))
    txt, notes = [], []
    for block in re.split(r'\n{2,}', body.strip('\n')):
        if block.startswith('#'):
            txt.append(unesc(block.lstrip('#').strip()))
        elif block == '* * *':
            txt.append('∗ ∗ ∗')
        elif block.startswith('[^'):
            for line in block.split('\n'):
                n, note = re.match(r'\[\^(\d+)\]: ?(.*)$', line).groups()
                notes.append(f'{n.translate(SUP)} {unesc(note)}')
        elif block.startswith('| '):
            txt.append('\n'.join(unesc(l[2:]) for l in block.split('\n')))
        else:
            txt.append('\n'.join(unesc(l) for l in block.split('\\\n')))
    if notes:
        txt += ['∗ ∗ ∗'] + notes
    return unicodedata.normalize('NFC', '\n\n'.join(t for t in txt if t.strip())) + '\n'
