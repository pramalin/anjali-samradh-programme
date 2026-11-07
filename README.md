# Anjali & Samradh: Bilingual Wedding Programme (Tamil + English)

A 4-page A5 booklet for Inkscape. It prints on one A4 sheet, double-sided, folded in half.

| Page | Contents |
|---|---|
| 1 Cover | உ, the title, names in Tamil and English, date and muhurtham, venue, and Thirukkural 45 with its English rendering |
| 2 Programme | நிகழ்ச்சி நிரல் / Order of Ceremony (8 bilingual steps), the officiant, and both families |
| 3 சொல் தேடல் | Tamil word search: one Tamil letter per box, words run left to right or top to bottom, and 18 words from the two verses with tick boxes and English meanings |
| 4 Word Search | English word search, Kurunthokai 40 in Tamil and English side by side, and the thank-you line |

## Files

| File | Purpose |
|---|---|
| `wedding-programme.svg` | The design. Open it in **Inkscape 1.2+**; the pages are listed under Document → Pages. |
| `wedding.json` | All the wording (each item has a Tamil `ta` and an English `en` line), the puzzle words and the colours. |
| `build.py` | Rebuilds the SVG and fresh puzzles from `wedding.json`. Runs on plain Python 3. If Pillow is installed, it uses the real fonts to shrink long lines to fit. |
| `wedding-programme-answer-key.txt` | Solutions to both puzzles. |
| `wedding-programme-proof.pdf` | The 4 pages as a PDF, for checking or a quick print. |
| `fonts/` | Noto Serif Tamil, Kavivanar (Tamil display), Great Vibes and Cormorant Garamond. All are free under the SIL Open Font License. |

## 1. Install the fonts

Install every `.ttf` in `fonts/`, then restart Inkscape. Without Noto Serif Tamil and Kavivanar, the Tamil text falls back to a system font.

## 2. Change the wording: edit `wedding.json`, then rebuild

```
python3 build.py
```

- **Order of ceremony:** `programme.items`. I wrote a typical Tamil-tradition sequence, so please confirm it with Sivathiru Aarooran's actual order. 6 to 9 items fit.
- **Families:** `programme.families[].lines`. Each line is `["ta", "…"]` or `["en", "…"]`. Add lines for grandparents or siblings (for example `["ta", "இளவல்: ஆதீஸ்வர்"]`); keep each column to about 6 lines.
- **Tamil puzzle:** `tamil_puzzle.words` holds `[word, English meaning]` pairs.
  - Tamil letters are split the way a reader sees them, so க், கா and கொ each take one box.
  - Changing `seed` gives a new layout with the same words.
  - Add `"down-right"` to `directions` for a harder puzzle.
- **English puzzle:** `english_puzzle.words`. COIMBATORE has 10 letters, so the grid needs to stay at least 10 × 10.
- **Colours:** `theme`. The maroon, gold, leaf green and marigold colours are each a single setting.

Running `build.py` overwrites the SVG. Do your wording changes first, then hand edits in Inkscape, or save the Inkscape version under a new name.

## 3. Edit directly in Inkscape

- **Layers:** Background (paper and frames), one layer per page, and **Answer Keys (hidden)**. Turn on the eye icon on the answer-key layer to see highlighted solutions, and turn it off before printing guest copies.
- **Names:** every object is named in the Layers and Objects panel (Ctrl+Shift+L), for example "Bride name (Tamil)", "Item 6 (English)" and "Thoranam (mango-leaf garland)".
- **Text:** all text is live, so double-click to retype.
- **Artwork:** File → Import adds a photo, a monogram or the venue QR code.

## 4. Printing as a folded booklet

1. Use File → Save a Copy → PDF and choose *Convert text to paths* for the print shop. This gives 4 A5 pages in reading order.
2. Print on A4 in **Booklet** mode. Adobe Reader and most printer drivers offer it. One sheet carries pages 4 | 1 on the outside and 2 | 3 on the inside; fold it, and the pages fall in order.
3. Alternatively, ask the print shop for "A5 4-page folded programme, A4 sheet". They can impose it from the PDF.

## Text sources

- Thirukkural 45 and Kurunthokai 40 are from the invitation, with the family's English renderings.
- The English meanings beside the Tamil puzzle words are short glosses written for this card.
