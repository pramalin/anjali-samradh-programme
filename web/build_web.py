#!/usr/bin/env python3
"""
Build the interactive web version of the programme into docs/ (for GitHub Pages).

    python3 web/build_web.py

Reads the same wedding.json + games.json as the print booklet, generates the same
word searches and crossword (same seeds, so web and print match), a maze, and writes:
    docs/index.html      the page (all game logic included)
    docs/data.js         the content and puzzles
    docs/assets/...      images
Then publish docs/ with GitHub Pages (see README: "Website").
"""
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
                                          int(cfg["seed"]), cfg.get("directions", ["right", "down"]))
    gl = {w["word"]: w for w in words}
    return {
        "grid": grid,
        "words": [{"word": p["word"], "row": p["row"], "col": p["col"],
                   "dr": build.DIRECTIONS[p["dir"]][0], "dc": build.DIRECTIONS[p["dir"]][1], "len": len(p["toks"]),
                   "gloss": gl[p["word"]].get("gloss", ""),
                   "ph": phon.get(p["word"], "").replace("|", " ")} for p in placed],
    }


def make_maze(size, seed, tries):
    best = None
    for s in range(seed, seed + tries):
        right, down = maze.carve(size, s)
        path = maze.solve(size, right, down)
        if best is None or len(path) > best[0]:
            best = (len(path), right, down, path)
    _, right, down, path = best
    return {"n": size, "right": [[int(v) for v in r] for r in right],
            "down": [[int(v) for v in r] for r in down], "solution": path}


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
        "maze": {**data.get("maze", {}), **make_maze(21, 1511, 200)},
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
        else:
            shutil.copy2(ROOT / "assets" / a, DOCS / "assets" / a)
    (DOCS / "data.js").write_text("window.PROGRAMME = " + json.dumps(out, ensure_ascii=False, indent=1) + ";\n",
                                  encoding="utf-8")
    shutil.copy2(Path(__file__).with_name("index.html"), DOCS / "index.html")
    (DOCS / ".nojekyll").write_text("")
    print(f"Wrote {DOCS}/index.html, data.js and {len(ASSETS)} images")


if __name__ == "__main__":
    main()
