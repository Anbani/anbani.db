# Top 100 of Georgian literature and poetry

The Anbani library's target list (2026-10-25).

- `shortlist.tsv`: 500 works, one row per work (poems, poemas, prose, drama, hagiography, chronicles). Drawn from a
  private Georgian-books collection on Google Drive (`in_drive`), plus canon missing from it. `public_domain`:
  author died ≤1955 (Georgia, life + 70). `death_year` 2100 = living.
- `round1-votes.tsv`: three models each ranked 100 ids from the shortlist without seeing the others: Argon (Gemini 4),
  Astra (GPT-6), Fable (Claude). `votes` counts the picks; `borda` sums 101 − rank.
- `top100.tsv`: the 61 works all three picked are in. Argon filled the other 39 places from the 83 contested works,
  seeing the other two models' ranks and reasons. On Kartvelian content Argon decides and the others advise.

Onboarding (2026-10-25): the 71 public-domain works plus the public-domain works of a second list George supplied
(same canon, grouped by era) were looked up on Georgian Wikisource. Found ones are in `../manifest.json` as `ready`
(`top100_rank` set for the top-100 ones); the rest are `source-needed` (no Wikisource transcription; NPLG e-books and
TITUS are the next sources) or `transcription-needed`. The 29 works in copyright are listed as `copyright` with
`public_domain_year` and stay out of the library until then.
