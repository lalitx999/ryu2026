# RYU KANJI / RYU KANA / RYU DICTIONARY open data

`kanji_seed.json.gz` (2,211 JLPT kanji) and `static/data/kana_strokes.json` are built from:

- **KANJIDIC2** — readings, meanings, stroke counts, grade, frequency. © Electronic Dictionary Research and
  Development Group, used under CC BY-SA 4.0 — https://www.edrdg.org/wiki/index.php/KANJIDIC_Project
- **JLPT level lists** by Jonathan Waller (unofficial; JLPT has published no official lists since 2010) —
  https://www.tanos.co.uk/jlpt/ (CC BY), via https://github.com/davidluzgouveia/kanji-data
- **KanjiVG** — stroke-order paths. © Ulrich Apel, CC BY-SA 3.0 — https://kanjivg.tagaini.net

- **JMdict** (common-words edition, `jmdict_common.json.gz`, 22,661 words) — forms, readings, parts of speech,
  English glosses. © EDRDG, CC BY-SA 4.0 — https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project,
  via https://github.com/scriptin/jmdict-simplified.  Words are ranked (field `rk`) by the hardest JLPT level of their
  kanji, then length: a heuristic, since this edition carries no frequency numbers.

Derived data in this folder is shared under the same CC BY-SA terms.  The Thai fields (meaning, notes, example
translations) are written separately (AI draft + teacher review) and stored only in the database.
Load / refresh with `python manage.py import_kanji` (Thai fields are never overwritten).

Dictionary: `python manage.py import_dictionary` (bundled Thai drafts: `dict_th_drafts.json.gz`).
