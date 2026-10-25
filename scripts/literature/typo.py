"""Typography (the rules of anbani.db 86d3ae9) and line-wrap hyphens, applied to every converted line."""
import collections, re

KA = 'ა-ჰ'
WRAP = '\x02'  # a word hyphenated across a printed line: join or compound, decided against the corpus
SUSPENDED = {'და', 'თუ', 'ან', 'ანუ', 'თუ არა'}  # "დღე- და ღამე": a suspended compound, the hyphen stays


def vocabulary(texts):
    return collections.Counter(w for t in texts for w in re.findall(rf'[{KA}]+(?:-[{KA}]+)*', t))


def dehyphen(s, vocab, prose):
    """A\x02B (line-end hyphen) and, in prose, 'A- B': AB when the corpus knows AB more often than A-B, else A-B
    ('A- B' stays when the corpus knows neither or B is a conjunction). vocab: the other works' words, never this
    work's own (its earlier joins would vouch for themselves)."""
    vocab = vocab or {}

    def pick(a, b, spaced):
        joined, hyph = vocab.get(a + b, 0), vocab.get(f'{a}-{b}', 0)
        if joined > hyph:
            return a + b
        return None if spaced and not hyph else f'{a}-{b}'

    s = re.sub(rf'([{KA}]+){WRAP}([{KA}]+)', lambda m: pick(m.group(1), m.group(2), False), s)
    s = s.replace(WRAP, '-')
    if prose:
        def spaced(m):
            if m.group(2) in SUSPENDED:
                return m.group(0)
            r = pick(m.group(1), m.group(2), True)
            return r if r else m.group(0)
        s = re.sub(rf'(?<![{KA}-])([{KA}]+)- ([{KA}]+)', spaced, s)
    return s


def typo(s):
    s = re.sub(r'[ \t]{2,}', ' ', s).strip()
    s = re.sub(r',,(?=\S)', '„', s)  # ,, typed for the low opening quote
    s = re.sub(rf'(?<=[{KA}])([,;:!?])(?=[{KA}])', r'\1 ', s)
    s = re.sub(rf'(?<=[{KA}]{{2}})\.(?=[{KA}])', '. ', s)
    s = re.sub(rf'(?<=[{KA}]) +([,;:!?]|\.(?!\.))(?=\s|$)', r'\1', s)
    s = re.sub(r'\s*-{2,3}\s*', ' — ', s).strip()  # typed double/triple hyphens
    s = re.sub(r'(?<=[,.!?;:])[-–](?=[ა-ჰ])', ' — ', s)  # ',-word': a dash glued to its words
    s = re.sub(r'(?<=\s)[-–](?=\s)', '—', s)
    s = re.sub(rf'(?<=[{KA}?!.,…:;]) -(?=[{KA}„"])', ' — ', s)  # ' -word': a dialogue dash glued to the next word
    s = re.sub(rf'(?<=[.!?…,])- (?=[{KA}])', ' — ', s)  # '.- word'
    s = re.sub(rf'(?<=[{KA}])- (?=—)', ' ', s)  # 'word- —'
    s = re.sub(r'—(\s+—)+', '—', s)
    s = re.sub(r'^[-–] ?(?=\S)', '— ', s)
    s = re.sub(r'(?<=\S) [-–]$', ' —', s)
    s = re.sub(r'(?<!\d)(\d{3,4}) ?[-–—] ?(\d{2,4})(?!\d)', '\\1–\\2', s)
    return s


def apply(blocks, notes):
    out = []
    for b in blocks:
        if b[0] == 'h':
            out.append(('h', b[1], typo(b[2])))
        elif b[0] in ('para', 'stanza'):
            out.append((b[0], [typo(l) for l in b[1]]))
        else:
            out.append(b)
    return out, {k: typo(v) for k, v in notes.items()}
