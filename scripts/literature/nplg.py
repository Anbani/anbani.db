"""The National Parliamentary Library's 'ბიბლიოთეკა სკოლას' pages (nplg.gov.ge/civil/statiebi/saskolo/, gone since 2025;
read from Wayback snapshots): page HTML -> the work's blocks -> HTML that convert() reads like a Wikisource page.

A page is a table: per row the work's text in one cell, glosses (and spacers) in others; glossed words wrapped in <dfn>.
Around the work: author: title, 'პროექტი: ბიბლიოთეკა სკოლას', reader credits, links to the author's other works.
The manifest says where the work starts and ends (`start`, `end`: a block's opening words) and which lines are glosses
or navigation (`drop`: opening words)."""
import html as H, re

PAGES = 'http://www.nplg.gov.ge/civil/statiebi/saskolo/'
KA = 'ა-ჰ'


def url(spec):
    return f"https://web.archive.org/web/{spec['snapshot']}id_/{PAGES}{spec['page']}"


def blocks(raw):
    s = raw[raw.lower().find('<body'):]
    s = re.sub(r'(?is)<script.*?</script>|<style.*?</style>|<!--.*?-->', '', s)
    s = re.sub(r'(?is)</?dfn\b[^>]*>', '', s)
    geo = lambda c: len(re.findall(f'[{KA}]', re.sub(r'<[^>]+>', '', c)))

    def row(m):  # a table row: the cell with the most text is the work's; glosses and spacers go
        cells = re.findall(r'(?is)<td\b[^>]*>(.*?)</td>', m.group(0))
        return '<p>' + max(cells, key=geo) + '</p>' if len(cells) > 1 else m.group(0)
    for _ in range(3):  # nested tables, innermost first
        s = re.sub(r'(?is)<tr\b(?:(?!<tr\b).)*?</tr>', row, s)
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'(?i)<br\s*/?>', '\n', s)
    s = re.sub(r'(?i)</?(p|div|td|tr|table|tbody|h\d|li|ul|ol|center|blockquote)\b[^>]*>', '\n\n', s)
    s = H.unescape(re.sub(r'<[^>]+>', '', s)).replace('\xa0', ' ')
    out = []
    for b in re.split(r'\n\s*\n', s):
        lines = [' '.join(l.split()) for l in b.split('\n')]
        if any(lines):
            out.append([l for l in lines if l])
    return out


def work_html(raw, spec, verse):
    bs = blocks(raw)
    first = next(i for i, b in enumerate(bs) if b[0].startswith(spec['start']))
    last = next(i for i in range(first, len(bs)) if any(l.startswith(spec['end']) for l in bs[i]))
    keep = []
    for b in bs[first:last + 1]:
        b = [l for l in b if not any(l.startswith(d) for d in spec.get('drop', []))]
        if b:
            keep.append(b)
    esc = lambda l: H.escape(l, quote=False)
    if verse:
        return '<div class="poem"><p>' + '<br />\n<br />\n'.join('<br />\n'.join(map(esc, b)) for b in keep) + '</p></div>'
    return ''.join('<p>' + '<br />\n'.join(map(esc, b)) + '</p>\n' for b in keep)
