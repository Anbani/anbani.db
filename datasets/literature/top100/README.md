# Top 100 of Georgian literature and poetry

The Anbani library's target list (2026-10-25).

- `shortlist.tsv`: 500 works, one row per work (poems, poemas, prose, drama, hagiography, chronicles). Drawn from a
  private Georgian-books collection on Google Drive (`in_drive`), plus canon missing from it. `public_domain`:
  author died ≤1955 (Georgia, life + 70). `death_year` 2100 = living.
- `round1-votes.tsv`: three models each ranked 100 ids from the shortlist without seeing the others: Argon (Gemini 4),
  Astra (GPT-6), Fable (Claude). `votes` counts the picks; `borda` sums 101 − rank.
- `top100.tsv`: the 61 works all three picked are in. Argon filled the other 39 places from the 83 contested works,
  seeing the other two models' ranks and reasons. On Kartvelian content Argon decides and the others advise.

Onboarding: public-domain works go into `../manifest.json` and `../<id>/` (pinned Wikisource revision, sha256). The
29 works still in copyright stay out of the library until they enter the public domain.
