#!/usr/bin/env python3
"""
Build the interactive web version of the programme into docs/ (for GitHub Pages).

    python3 web/build_web.py

Reads the same wedding.json + games.json as the print booklet, generates the same
word searches and crossword (same seeds, so web and print match), a maze, and writes:
    docs/index.html      the page (game logic and content included)
    docs/assets/...      images
Then publish docs/ with GitHub Pages (see README: "Website").
"""
import hashlib
from datetime import datetime
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402  (puzzle generators shared with the print version)
import maze   # noqa: E402

DOCS = ROOT / "docs"
ASSETS = ["parchment.jpg", "monogram.svg", "groom.svg", "bride.svg", "kuthuvilakku.png", "drawing-frame.png"]


def word_search(cfg, phon):
    words = build.puzzle_words(cfg)
    grid, placed = build.make_word_search([w["word"] for w in words], int(cfg["rows"]), int(cfg["cols"]),
                                          int(cfg["seed"]), cfg.get("directions", ["right", "down"]),
                                          int(cfg.get("decoys", 0)))
    gl = {w["word"]: w for w in words}
    return {
        "grid": grid,
        "words": [{"word": p["word"], "row": p["row"], "col": p["col"],
                   "dr": build.DIRECTIONS[p["dir"]][0], "dc": build.DIRECTIONS[p["dir"]][1], "len": len(p["toks"]),
                   "gloss": gl[p["word"]].get("gloss", ""),
                   "ph": phon.get(p["word"], "").replace("|", " ")} for p in placed],
    }


def make_maze(seed, n=21):
    """The standard maze with story stops (same as the booklet's): python3 maze.py --story --size 21 --seed 686 --report"""
    import maze_icons
    m = maze.story_maze(seed, n)
    edges = m["edges"]
    opened = lambda a, b: frozenset((a, b)) in edges
    print("maze: story,", len(m["path"]), "squares on the route")
    return {"rows": n, "cols": n,
            "cells": [[1] * n for _ in range(n)],
            "right": [[int(not opened((r, c), (r, c + 1))) for c in range(n)] for r in range(n)],
            "down": [[int(not opened((r, c), (r + 1, c))) for c in range(n)] for r in range(n)],
            "solution": m["path"], "start": m["start"], "end": m["end"],
            "rooms": [{"r": r, "c": c, "icon": name, "parts": maze_icons.ICONS[name]}
                      for name, (r, c) in zip(maze_icons.ORDER, m["rooms"])]}


def see_through(src, dst):
    """Copy a line drawing on white with the white made transparent (soft edges kept)."""
    from PIL import Image
    im = Image.open(src).convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            light = min(r, g, b)
            px[x, y] = (r, g, b, min(a, max(0, round((255 - light) * 255 / 120))) if light > 135 else a)
    im.save(dst, optimize=True)


def main():
    data = build.load_data([ROOT / "wedding.json", ROOT / "games.json"])
    phon = {k: v for k, v in data.get("phonetics", {}).items() if not k.startswith("_")}
    breaks = data.get("tamil_line_breaks", {})

    cw = data["crossword"]
    rows, R, C, cell, numbers = build.prepare_crossword(cw, "crossword")
    crossword = {
        "rows": R, "cols": C,
        "cells": [[cell(r, c) for c in range(C)] for r in range(R)],
        "numbers": [[numbers.get((r, c)) for c in range(C)] for r in range(R)],
        "across": [{k: e[k] for k in ("n", "answer", "clue", "len", "row", "col")} for e in cw["across"]],
        "down": [{k: e[k] for k in ("n", "answer", "clue", "len", "row", "col")} for e in cw["down"]],
    }

    out = {
        # only what the page shows: the invitation's date, time and venue are NOT published
        "cover": {k: data.get("cover", {}).get(k) for k in ("title", "subtitle")},
        "monogram": data.get("monogram", {}),
        "programme": {
            "title_en": data["programme"].get("title_en", "Order of Ceremony"),
            "title_ta": data["programme"].get("title_ta", ""),
            "items": [{"ta": it["ta"], "en": it.get("en", ""),
                       "ph": phon.get(it["ta"], "").replace("|", " ")} for it in data["programme"]["items"]],
        },
        "tamil_words": {**{k: data["tamil_words"].get(k, "") for k in ("title_ta", "title_en_short", "instructions")},
                        **word_search(data["tamil_words"], phon)},
        "english_words": {**{k: data["english_words"].get(k, "") for k in ("title_en", "title_ta", "instructions")},
                          **word_search(data["english_words"], phon)},
        "maze": {**data.get("maze", {}), **make_maze(686)},
        "drawing": data.get("drawing", {}),
        "dots_boxes": data.get("dots_boxes", {}),
        "tictactoe": data.get("tictactoe", {}),
        "crossword": {**{k: cw.get(k, "") for k in ("title_ta", "title_en", "instructions_ta", "instructions_en")},
                      **crossword},
        "verses": data.get("verses", {}),
        "thanks": data.get("thanks", {}),
    }

    DOCS.mkdir(exist_ok=True)
    (DOCS / "assets").mkdir(exist_ok=True)
    for a in ASSETS:
        if a.endswith(".svg"):    # drawings in the booklet's ink colour
            svg = (ROOT / "assets" / a).read_text(encoding="utf-8")
            (DOCS / "assets" / a).write_text(svg.replace("#000000", "#3a2c24").replace("fill:#000;", "fill:#3a2c24;"),
                                             encoding="utf-8")
        elif a == "drawing-frame.png":   # the drawing shows through: white becomes transparent
            see_through(ROOT / "assets" / a, DOCS / "assets" / a)
        else:
            shutil.copy2(ROOT / "assets" / a, DOCS / "assets" / a)
    # the content goes inside index.html, so the page is one self-contained file plus its images
    page = Path(__file__).with_name("index.html").read_text(encoding="utf-8")
    payload = json.dumps(out, ensure_ascii=False).replace("</", "<\\/")
    page = page.replace('<script src="data.js"></script>', f"<script>window.PROGRAMME = {payload};</script>")
    for a in ASSETS:     # ?v=<content hash> so browsers fetch an image again whenever it changes
        v = hashlib.sha1((DOCS / "assets" / a).read_bytes()).hexdigest()[:8]
        page = page.replace(f"assets/{a}", f"assets/{a}?v={v}")
    page = page.replace("__BUILD__", datetime.now().strftime("%d %b %Y %H:%M"))
    (DOCS / "index.html").write_text(page, encoding="utf-8")
    (DOCS / "data.js").unlink(missing_ok=True)
    (DOCS / ".nojekyll").write_text("")
    print(f"Wrote {DOCS}/index.html and {len(ASSETS)} images")


if __name__ == "__main__":
    main()
