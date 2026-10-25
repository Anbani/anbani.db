# Literature

Public-domain Georgian prose and poetry (Georgia: author died 70+ years ago), one directory per work.
`manifest.json` lists every work: `ready` texts, and the rest of the top-100 canon ([top100/](top100/README.md)):
`source-needed`, `transcription-needed`, `copyright` (`public_domain_year`). `top100_rank`: place in the top 100;
`rank`: 101+ for the public-domain works ranked after it (`top100/ranking-101.tsv`). `layout_review`: how a poem whose
stanza breaks Argon could not settle from the transcription was settled (a second transcription, or the source).

## Per work

- `text.md`: canonical. pandoc Markdown, UTF-8 NFC, YAML front matter (id, title, author, death_year, genre, shelf,
  source with pinned revision, corrections, license). `#`/`##`/`###` headings, one paragraph per block, verse as
  line blocks (`| ` per line, one block per stanza), `* * *` scene breaks, `*italic*`, footnotes `[^n]`.
- `text.txt`: derived from text.md (`md2txt`): one block per paragraph/stanza/heading, blank line between, markup
  dropped, footnote refs as ¹²³ and notes after a final `∗ ∗ ∗`. The web reader's input (Web `scripts/sync-library.mjs`
  checks `sha256`).
- `source.json`: page, revision (or `parts`), retrieved, transcription license, corrections, `sha256` (text.txt),
  `sha256_md` (text.md).

Ebooks: `pandoc text.md -o x.epub --metadata lang=ka --css book.css --epub-embed-font=AnbaniSerif-Regular.ttf --toc`
(PDF via typst; MOBI via calibre `ebook-convert`).

## Import

```sh
python3 scripts/literature/import.py [--cache DIR] [--force] [id ...]   # pinned Wikisource revision -> text.md, txt
python3 scripts/literature/import.py --derive [id ...]                 # after editing text.md: text.txt + sha256
```

A manifest entry with `wikisource: {page, revision}` (or `parts`) is importable. The converter reads structure from
lines (paragraphs, stanzas, scan wraps rejoined), applies the typography rules (spaces after punctuation, dashes,
year ranges) and decides line-wrap hyphens against the rest of the corpus. Per-work fixes live in `import.py`
(`CORRECTIONS` for typos, `scripts/literature/fixes/<id>.tsv` for a proofread's typing errors (matched across line
wraps, each exactly once), `LAYOUT` for source layout and apparatus, `FIXUPS`, `STANZAS` for poems in regular
stanzas whose source lost the breaks: lines per stanza, from Argon's per-poem review). An existing text.md is kept unless `--force`; hand fixes go into text.md, then `--derive`.
`vefxistyaosani` stays at `../vefxistyaosani.txt` (own format, source review pending).
