#!/usr/bin/env python3
"""
Bilingual (Tamil + English) wedding programme booklet with word searches.

    python3 build.py                     # wedding.json -> wedding-programme.svg
    python3 build.py my.json out.svg

Produces a 4-page A5 booklet (prints on A4, folded):
  1 Cover - names, date, venue, Thirukkural 45
  2 Order of ceremony & families
  3 Tamil word search (one Tamil letter per box, words from the verses)
  4 English word search + Kurunthokai 40 + thank-you

Open the SVG in Inkscape 1.2+ (pages appear in Document > Pages). Everything is
live text on named layers; answer keys are on a hidden layer.
Standard-library Python is enough. If Pillow is installed, long lines are
measured with the real fonts and shrunk to fit; otherwise an estimate is used.
"""
import json
import math
import random
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
MM = 96 / 25.4

DIRECTIONS = {
    "right": (0, 1), "down": (1, 0), "down-right": (1, 1), "up-right": (-1, 1),
    "left": (0, -1), "up": (-1, 0), "up-left": (-1, -1), "down-left": (1, -1),
}

FONT_FILES = {  # used only to measure text widths
    ("Noto Serif Tamil", False): "NotoSerifTamil[wdth,wght].ttf",
    ("Kavivanar", False): "Kavivanar-Regular.ttf",
    ("Great Vibes", False): "GreatVibes-Regular.ttf",
    ("Cormorant Garamond", False): "CormorantGaramond[wght].ttf",
    ("Cormorant Garamond", True): "CormorantGaramond-Italic[wght].ttf",
}


# ------------------------------------------------------------ Tamil letters
TAMIL_MARKS = set(range(0x0BBE, 0x0BCE)) | {0x0B82, 0x0BD7, 0x200C, 0x200D}


def letters(word):
    """Split a word into 'letters' as Tamil readers see them: க், கா, கொ ...
    (a base character plus any vowel sign / pulli that follows it)."""
    out = []
    for ch in word:
        if ch.isspace() or ch in "-'.,?!·":
            continue
        if out and ord(ch) in TAMIL_MARKS:
            out[-1] += ch
        else:
            out.append(ch.upper())
    return out


# ------------------------------------------------------------ word search
def make_word_search(words, rows, cols, seed, dirs):
    items = [(letters(w), w) for w in words]
    for toks, w in items:
        if len(toks) > max(rows, cols):
            sys.exit(f"'{w}' has {len(toks)} letters - grid {rows}x{cols} is too small.")
    for attempt in range(400):
        rng = random.Random(seed + attempt)
        grid = [[None] * cols for _ in range(rows)]
        placed, ok = [], True
        for toks, w in sorted(items, key=lambda t: -len(t[0])):
            opts = []
            for d in dirs:
                dr, dc = DIRECTIONS[d]
                n = len(toks)
                for r in range(rows):
                    for c in range(cols):
                        er, ec = r + dr * (n - 1), c + dc * (n - 1)
                        if not (0 <= er < rows and 0 <= ec < cols):
                            continue
                        hit, fits = 0, True
                        for i, t in enumerate(toks):
                            g = grid[r + dr * i][c + dc * i]
                            if g is None:
                                continue
                            if g != t:
                                fits = False
                                break
                            hit += 1
                        if fits and hit < n:
                            opts.append((hit, rng.random(), r, c, d))
            if not opts:
                ok = False
                break
            # pick a direction at random first so words run every allowed way,
            # then prefer a crossing with an existing word
            d_pick = rng.choice(sorted({o[4] for o in opts}))
            opts = [o for o in opts if o[4] == d_pick]
            opts.sort(key=lambda o: (-min(o[0], 1), o[1]))
            _, _, r, c, d = opts[0] if rng.random() < 0.4 else rng.choice(opts)
            dr, dc = DIRECTIONS[d]
            for i, t in enumerate(toks):
                grid[r + dr * i][c + dc * i] = t
            placed.append({"word": w, "toks": toks, "row": r, "col": c, "dir": d})
        if ok:
            break
    else:
        sys.exit("Could not fit all words - enlarge the grid or allow more directions.")
    pool = [t for toks, _ in items for t in toks]
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] is None:
                grid[r][c] = rng.choice(pool)
    order = [w for _, w in items]
    placed.sort(key=lambda p: order.index(p["word"]))
    return grid, placed


# ------------------------------------------------------------ text + measuring
try:
    from PIL import ImageFont
    _cache = {}

    def text_width(s, family, size, italic=False):
        key = (family, italic)
        f = FONT_FILES.get(key) or FONT_FILES.get((family, False))
        path = HERE / "fonts" / f if f else None
        if not path or not path.exists():
            return len(s) * size * 0.55
        k = (path, round(size * 4))
        if k not in _cache:
            try:
                _cache[k] = ImageFont.truetype(str(path), size,
                                               layout_engine=ImageFont.Layout.RAQM)
            except Exception:
                _cache[k] = ImageFont.truetype(str(path), size)
        return _cache[k].getlength(s)
except ImportError:  # no Pillow: rough estimate
    def text_width(s, family, size, italic=False):
        return len(s) * size * 0.55


def esc(s):
    return escape(str(s), {'"': "&quot;"})


def text(x, y, s, size, font, fill, anchor="middle", weight=None, italic=False,
         spacing=0, label=None, maxw=None):
    if maxw:  # shrink to fit the available width
        while size > 6 and text_width(s, font, size, italic) + spacing * len(s) > maxw:
            size *= 0.96
            spacing *= 0.96
    st = [f"font-family:'{font}'", f"font-size:{size:.2f}px", f"fill:{fill}",
          f"text-anchor:{anchor}"]
    if weight:
        st.append(f"font-weight:{weight}")
    if italic:
        st.append("font-style:italic")
    if spacing:
        st.append(f"letter-spacing:{spacing:.2f}px")
    lab = f' inkscape:label="{esc(label)}"' if label else ""
    return (f'<text xml:space="preserve" x="{x:.2f}" y="{y:.2f}" '
            f'style="{";".join(st)}"{lab}>{esc(s)}</text>')


# ------------------------------------------------------------ ornaments
def mango_leaf(x, y, length, angle, color):
    w = length * 0.28
    return (f'<g transform="translate({x:.2f},{y:.2f}) rotate({angle:.1f})">'
            f'<path d="M 0,0 C {w:.2f},{length*0.25:.2f} {w*0.8:.2f},{length*0.75:.2f} 0,{length:.2f} '
            f'C {-w*0.8:.2f},{length*0.75:.2f} {-w:.2f},{length*0.25:.2f} 0,0 Z" style="fill:{color}"/>'
            f'<path d="M 0,{length*0.08:.2f} L 0,{length*0.9:.2f}" '
            f'style="stroke:#ffffff;stroke-opacity:0.35;stroke-width:0.7"/></g>')


def marigold(x, y, r, color, center):
    petals = "".join(
        f'<ellipse cx="{x + r*0.55*math.cos(a):.2f}" cy="{y + r*0.55*math.sin(a):.2f}" '
        f'rx="{r*0.5:.2f}" ry="{r*0.32:.2f}" transform="rotate({math.degrees(a):.1f} '
        f'{x + r*0.55*math.cos(a):.2f} {y + r*0.55*math.sin(a):.2f})" style="fill:{color}"/>'
        for a in [i * math.pi / 5 for i in range(10)])
    return f'<g>{petals}<circle cx="{x:.2f}" cy="{y:.2f}" r="{r*0.35:.2f}" style="fill:{center}"/></g>'


def thoranam(x0, x1, y, t, label="Thoranam (mango-leaf garland)"):
    """Traditional doorway garland: a cord with hanging mango leaves and marigolds."""
    sag = 10
    out = [f'<g inkscape:label="{label}">',
           f'<path d="M {x0:.2f},{y:.2f} Q {(x0+x1)/2:.2f},{y+sag*2:.2f} {x1:.2f},{y:.2f}" '
           f'style="fill:none;stroke:{t["gold"]};stroke-width:1.4"/>']
    n = 15
    for i in range(n + 1):
        u = i / n
        px = x0 + (x1 - x0) * u
        py = (1 - u) ** 2 * y + 2 * (1 - u) * u * (y + sag * 2) + u ** 2 * y
        if i % 2 == 0:
            out.append(mango_leaf(px, py, 30 if i % 4 == 0 else 24, 0, t["leaf"]))
        else:
            out.append(marigold(px, py + 4, 6.5, t["marigold"], t["maroon"]))
    out.append("</g>")
    return "".join(out)


def kolam_divider(cx, y, t, half=70, label="Kolam divider"):
    dots = "".join(f'<circle cx="{cx + s*d:.2f}" cy="{y:.2f}" r="1.3" style="fill:{t["gold"]}"/>'
                   for d in range(18, int(half), 9) for s in (-1, 1))
    diamond = (f'<path d="M {cx},{y-7} L {cx+7},{y} L {cx},{y+7} L {cx-7},{y} Z" '
               f'style="fill:none;stroke:{t["maroon"]};stroke-width:1.1"/>'
               f'<circle cx="{cx}" cy="{y}" r="2" style="fill:{t["maroon"]}"/>')
    return f'<g inkscape:label="{label}">{dots}{diamond}</g>'


def frame(ox, W, H, t):
    m1, m2 = 14, 20
    corner = ""
    for cx, cy in [(ox + m2, m2), (ox + W - m2, m2), (ox + m2, H - m2), (ox + W - m2, H - m2)]:
        corner += (f'<path d="M {cx},{cy-6} L {cx+6},{cy} L {cx},{cy+6} L {cx-6},{cy} Z" '
                   f'style="fill:{t["background"]};stroke:{t["gold"]};stroke-width:1"/>'
                   f'<circle cx="{cx}" cy="{cy}" r="1.5" style="fill:{t["maroon"]}"/>')
    return (f'<g inkscape:label="Frame">'
            f'<rect x="{ox+m1}" y="{m1}" width="{W-2*m1:.2f}" height="{H-2*m1:.2f}" '
            f'style="fill:none;stroke:{t["maroon"]};stroke-width:1.6"/>'
            f'<rect x="{ox+m2}" y="{m2}" width="{W-2*m2:.2f}" height="{H-2*m2:.2f}" '
            f'style="fill:none;stroke:{t["gold"]};stroke-width:0.7"/>{corner}</g>')


# ------------------------------------------------------------ pages
class Page:
    def __init__(self, cfg, ox, W, H):
        self.t = cfg["theme"]
        self.ox, self.W, self.H = ox, W, H
        self.cx = ox + W / 2
        self.maxw = W - 80
        self.parts = []

    def add(self, s):
        self.parts.append(s)

    def ta(self, y, s, size, **kw):
        kw.setdefault("maxw", self.maxw)
        self.add(text(kw.pop("x", self.cx), y, s, size, self.t["tamil_font"],
                      kw.pop("fill", self.t["ink"]), **kw))

    def ta_display(self, y, s, size, **kw):
        kw.setdefault("maxw", self.maxw)
        self.add(text(kw.pop("x", self.cx), y, s, size, self.t["tamil_display_font"],
                      kw.pop("fill", self.t["maroon"]), **kw))

    def en(self, y, s, size, **kw):
        kw.setdefault("maxw", self.maxw)
        self.add(text(kw.pop("x", self.cx), y, s, size, self.t["serif_font"],
                      kw.pop("fill", self.t["ink"]), **kw))

    def script(self, y, s, size, **kw):
        kw.setdefault("maxw", self.maxw)
        self.add(text(kw.pop("x", self.cx), y, s, size, self.t["script_font"],
                      kw.pop("fill", self.t["gold"]), **kw))

    def svg(self):
        return "\n".join(self.parts)


def cover_page(cfg, ox, W, H):
    c, t = cfg["cover"], cfg["theme"]
    p = Page(cfg, ox, W, H)
    p.add(thoranam(ox + 30, ox + W - 30, 30, t))
    p.ta(118, c["blessing"], 20, fill=t["maroon"], weight=600, label="Blessing (உ)")
    p.ta(138, c["deity_line"], 10, fill=t["gold"], label="Deity line")
    p.ta_display(180, c["title_ta"], 22, fill=t["gold"], label="Title (Tamil)")
    p.en(200, c["title_en"], 10, spacing=4, weight=600, label="Title (English)")
    p.ta_display(268, c["bride_ta"], 50, label="Bride name (Tamil)")
    p.script(310, "&", 34, label="Ampersand")
    p.ta_display(366, c["groom_ta"], 50, label="Groom name (Tamil)")
    p.script(414, c["couple_en"], 36, fill=t["ink"], label="Couple names (English)")
    p.add(kolam_divider(p.cx, 442, t))
    p.ta(478, c["date_ta"], 13, weight=600, label="Date (Tamil)")
    p.en(498, c["date_en"], 15, italic=True, label="Date (English)")
    p.ta(524, c["time_ta"], 11, label="Time (Tamil)")
    p.en(542, c["time_en"], 13, italic=True, label="Time (English)")
    p.ta(572, c["venue_ta"], 11.5, fill=t["maroon"], weight=600, label="Venue (Tamil)")
    p.en(591, c["venue_en"].upper(), 9.5, spacing=1.6, weight=600, label="Venue (English)")
    # verse box
    by = 618
    p.add(f'<rect x="{ox+48:.2f}" y="{by:.2f}" width="{W-96:.2f}" height="128" rx="6" '
          f'style="fill:{t["gold_light"]};fill-opacity:0.28;stroke:{t["gold"]};stroke-width:0.6"'
          f' inkscape:label="Verse box"/>')
    g = ['<g inkscape:label="Thirukkural 45">']
    p2 = Page(cfg, ox, W, H)
    p2.maxw = W - 120
    for i, line in enumerate(c["verse_ta"]):
        p2.ta(by + 26 + i * 20, line, 12.5, fill=t["maroon"], weight=500)
    p2.ta(by + 26 + len(c["verse_ta"]) * 20 - 2, "— " + c["verse_source"], 9, fill=t["gold"])
    y0 = by + 26 + len(c["verse_ta"]) * 20 + 18
    for i, line in enumerate(c["verse_en"]):
        p2.en(y0 + i * 15, line, 11.5, italic=True)
    g.append(p2.svg())
    g.append("</g>")
    p.add("\n".join(g))
    return p.svg()


def programme_page(cfg, ox, W, H):
    pr, t = cfg["programme"], cfg["theme"]
    p = Page(cfg, ox, W, H)
    p.add(kolam_divider(p.cx, 46, t, half=110))
    p.ta_display(86, pr["title_ta"], 28, label="Programme title (Tamil)")
    p.script(114, pr["title_en"], 26, label="Programme title (English)")
    items = pr["items"]
    step = min(38, 320 / max(len(items), 1))
    y = 150
    g = ['<g inkscape:label="Order of ceremony">']
    for i, it in enumerate(items):
        yy = y + i * step
        nx = ox + 62
        g.append(f'<circle cx="{nx}" cy="{yy+3:.2f}" r="9" style="fill:none;stroke:{t["gold"]};stroke-width:0.9"/>')
        g.append(text(nx, yy + 7, str(i + 1), 11, t["serif_font"], t["maroon"], weight=700))
        g.append(text(ox + 82, yy + 2, it["ta"], 12.5, t["tamil_font"], t["maroon"], anchor="start",
                      weight=600, maxw=W - 130, label=f"Item {i+1} (Tamil)"))
        g.append(text(ox + 82, yy + 17, it["en"], 12, t["serif_font"], t["ink"], anchor="start",
                      italic=True, maxw=W - 130, label=f"Item {i+1} (English)"))
    g.append("</g>")
    p.add("\n".join(g))

    y = 150 + len(items) * step + 6
    p.add(kolam_divider(p.cx, y, t))
    p.ta(y + 30, pr["officiant_label_ta"], 10.5, fill=t["gold"], weight=600, label="Officiant label (Tamil)")
    p.en(y + 46, pr["officiant_label_en"], 11, italic=True, label="Officiant label (English)")
    p.ta(y + 70, pr["officiant_ta"], 14, fill=t["maroon"], weight=700, label="Officiant (Tamil)")
    p.en(y + 88, pr["officiant_en"], 11, label="Officiant (English)")

    fy = y + 128
    fams = pr["families"]
    colw = (W - 80) / len(fams)
    for k, f in enumerate(fams):
        cx = ox + 40 + colw * (k + 0.5)
        g = [f'<g inkscape:label="Family: {esc(f["label_en"].title())}">']
        g.append(text(cx, fy, f["label_ta"] + "  ·  " + f["label_en"], 9.5, t["serif_font"],
                      t["gold"], weight=700, spacing=1.5, maxw=colw - 10))
        # label mixes scripts; keep Tamil in Tamil font for reliable rendering
        g[-1] = (text(cx, fy, f["label_ta"], 11, t["tamil_font"], t["gold"], weight=700)
                 + text(cx, fy + 14, f["label_en"], 8.5, t["serif_font"], t["gold"],
                        weight=700, spacing=2))
        g.append(text(cx, fy + 46, f["name_ta"], 26, t["tamil_display_font"], t["maroon"],
                      maxw=colw - 10))
        g.append(text(cx, fy + 72, f["name_en"], 22, t["script_font"], t["ink"], maxw=colw - 10))
        yy = fy + 96
        for kind, s in f["lines"]:
            if kind == "ta":
                g.append(text(cx, yy, s, 11, t["tamil_font"], t["ink"], maxw=colw - 12))
                yy += 17
            else:
                g.append(text(cx, yy, s, 11, t["serif_font"], t["ink"], italic=True,
                              maxw=colw - 12))
                yy += 15
        g.append("</g>")
        p.add("\n".join(g))
    if len(fams) == 2:
        p.add(f'<line x1="{p.cx}" y1="{fy-8}" x2="{p.cx}" y2="{fy+150}" '
              f'style="stroke:{t["gold_light"]};stroke-width:0.8"/>')
    return p.svg()


def draw_grid(p, grid, gx, gy, cell, font, size, t, label, weight=600, lines=True):
    rows, cols = len(grid), len(grid[0])
    out = [f'<g inkscape:label="{label}">',
           f'<rect x="{gx:.2f}" y="{gy:.2f}" width="{cell*cols:.2f}" height="{cell*rows:.2f}" '
           f'style="fill:#ffffff;fill-opacity:0.7;stroke:{t["gold"]};stroke-width:1.2"/>']
    if lines:
        d = "".join(f"M {gx+cell*c:.2f},{gy:.2f} V {gy+cell*rows:.2f} " for c in range(1, cols))
        d += "".join(f"M {gx:.2f},{gy+cell*r:.2f} H {gx+cell*cols:.2f} " for r in range(1, rows))
        out.append(f'<path d="{d}" style="fill:none;stroke:{t["gold_light"]};stroke-width:0.7"'
                   f' inkscape:label="Cell lines"/>')
    for r in range(rows):
        row = [f'<g inkscape:label="Row {r+1}">']
        for c in range(cols):
            row.append(text(gx + cell * (c + 0.5), gy + cell * (r + 0.5) + size * 0.36,
                            grid[r][c], size, font, t["ink"], weight=weight))
        row.append("</g>")
        out.append("".join(row))
    out.append("</g>")
    return "\n".join(out)


def answer_lines(placed, gx, gy, cell, t):
    out = []
    for p in placed:
        dr, dc = DIRECTIONS[p["dir"]]
        n = len(p["toks"]) - 1
        out.append(f'<line x1="{gx+cell*(p["col"]+.5):.2f}" y1="{gy+cell*(p["row"]+.5):.2f}" '
                   f'x2="{gx+cell*(p["col"]+dc*n+.5):.2f}" y2="{gy+cell*(p["row"]+dr*n+.5):.2f}" '
                   f'inkscape:label="Answer {esc(p["word"])}" style="stroke:{t["marigold"]};'
                   f'stroke-opacity:0.4;stroke-width:{cell*0.72:.2f};stroke-linecap:round"/>')
    return "\n".join(out)


def checkbox(x, y, t):
    return (f'<rect x="{x:.2f}" y="{y-8:.2f}" width="8" height="8" rx="1" '
            f'style="fill:none;stroke:{t["gold"]};stroke-width:0.9"/>')


def tamil_puzzle_page(cfg, ox, W, H):
    tp, t = cfg["tamil_puzzle"], cfg["theme"]
    p = Page(cfg, ox, W, H)
    words = [w for w, _ in tp["words"]]
    grid, placed = make_word_search(words, tp["rows"], tp["cols"], tp["seed"], tp["directions"])
    p.ta_display(70, tp["title_ta"], 32, label="Puzzle title (Tamil)")
    p.script(98, tp["title_en"], 22, label="Puzzle title (English)")
    y = 124
    for i, line in enumerate(tp["instructions_ta"]):
        p.ta(y + i * 16, line, 10.5, label=f"Instructions (Tamil) {i+1}")
    y += len(tp["instructions_ta"]) * 16 + 2
    p.en(y, tp["instructions_en"], 10.5, italic=True, label="Instructions (English)")

    cell = min((W - 100) / tp["cols"], 380 / tp["rows"])
    gx, gy = p.cx - cell * tp["cols"] / 2, y + 16
    p.add(draw_grid(p, grid, gx, gy, cell, t["tamil_font"], cell * 0.37, t,
                    "Tamil word search grid", weight=500))
    key = answer_lines(placed, gx, gy, cell, t)

    ly = gy + cell * tp["rows"] + 30
    ncol = 3
    per = math.ceil(len(tp["words"]) / ncol)
    colw = (W - 70) / ncol
    g = ['<g inkscape:label="Tamil word list">']
    for i, (w, gloss) in enumerate(tp["words"]):
        col, row = divmod(i, per)
        x = ox + 35 + col * colw + 12
        yy = ly + row * 28
        g.append(checkbox(x, yy, t))
        g.append(text(x + 13, yy, w, 11.5, t["tamil_font"], t["maroon"], anchor="start",
                      weight=600, maxw=colw - 30))
        g.append(text(x + 13, yy + 11, gloss, 9.5, t["serif_font"], t["ink"], anchor="start",
                      italic=True, maxw=colw - 30))
    g.append("</g>")
    p.add("\n".join(g))
    return p.svg(), key, grid, placed


def english_puzzle_page(cfg, ox, W, H):
    ep, b, t = cfg["english_puzzle"], cfg["back"], cfg["theme"]
    p = Page(cfg, ox, W, H)
    grid, placed = make_word_search(ep["words"], ep["rows"], ep["cols"], ep["seed"], ep["directions"])
    p.script(68, ep["title_en"], 34, fill=t["maroon"], label="Puzzle title (English)")
    p.ta(90, ep["title_ta"], 10.5, fill=t["gold"], label="Puzzle title (Tamil)")
    p.en(108, ep["instructions_en"], 11.5, italic=True, label="Instructions")
    cell = min((W - 150) / ep["cols"], 290 / ep["rows"])
    gx, gy = p.cx - cell * ep["cols"] / 2, 120
    p.add(draw_grid(p, grid, gx, gy, cell, t["serif_font"], cell * 0.6, t,
                    "English word search grid"))
    key = answer_lines(placed, gx, gy, cell, t)

    ly = gy + cell * ep["rows"] + 26
    ncol = 4 if len(ep["words"]) > 9 else 3
    per = math.ceil(len(ep["words"]) / ncol)
    colw = (W - 70) / ncol
    g = ['<g inkscape:label="English word list">']
    for i, w in enumerate(ep["words"]):
        col, row = divmod(i, per)
        x = ox + 35 + col * colw + 8
        yy = ly + row * 18
        g.append(checkbox(x, yy, t))
        g.append(text(x + 13, yy, w.upper(), 10, t["serif_font"], t["ink"], anchor="start",
                      weight=600, spacing=1.2, maxw=colw - 24))
    g.append("</g>")
    p.add("\n".join(g))

    vy = ly + per * 18 + 12
    p.add(kolam_divider(p.cx, vy, t))
    vy += 30
    half = (W - 80) / 2
    ta_size = min([11] + [11 * (half - 12) / max(text_width(l, t["tamil_font"], 11), 1)
                          for l in b["verse_ta"]])
    en_size = min([11.5] + [11.5 * (half - 12) / max(text_width(l, t["serif_font"], 11.5, True), 1)
                            for l in b["verse_en"]])
    g = ['<g inkscape:label="Kurunthokai 40 (Tamil)">']
    for i, line in enumerate(b["verse_ta"]):
        g.append(text(ox + 40 + half / 2, vy + i * 19, line, ta_size, t["tamil_font"], t["maroon"],
                      weight=500, maxw=half - 12))
    g.append(text(ox + 40 + half / 2, vy + len(b["verse_ta"]) * 19 + 2, "— " + b["verse_source_ta"],
                  9, t["tamil_font"], t["gold"]))
    g.append("</g>")
    g.append('<g inkscape:label="Kurunthokai 40 (English)">')
    for i, line in enumerate(b["verse_en"]):
        g.append(text(ox + 40 + half * 1.5, vy + i * 19, line, en_size, t["serif_font"], t["ink"],
                      italic=True, maxw=half - 12))
    g.append(text(ox + 40 + half * 1.5, vy + len(b["verse_en"]) * 19 + 2, "— " + b["verse_source_en"],
                  10, t["serif_font"], t["gold"], weight=600))
    g.append("</g>")
    g.append(f'<line x1="{p.cx}" y1="{vy-14}" x2="{p.cx}" y2="{vy+len(b["verse_ta"])*19}" '
             f'style="stroke:{t["gold_light"]};stroke-width:0.8"/>')
    p.add("\n".join(g))

    p.ta_display(H - 62, b["thanks_ta"], 17, label="Thanks (Tamil)")
    p.script(H - 36, b["thanks_en"], 20, label="Thanks (English)")
    return p.svg(), key, grid, placed


# ------------------------------------------------------------ assemble
def build(cfg_path, out_path):
    cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
    t = cfg["theme"]
    W, H = t["page_width_mm"] * MM, t["page_height_mm"] * MM
    gap = 40
    xs = [i * (W + gap) for i in range(4)]
    p1 = cover_page(cfg, xs[0], W, H)
    p2 = programme_page(cfg, xs[1], W, H)
    p3, key3, grid3, placed3 = tamil_puzzle_page(cfg, xs[2], W, H)
    p4, key4, grid4, placed4 = english_puzzle_page(cfg, xs[3], W, H)
    total_w = xs[3] + W
    names = ["1 Cover", "2 Programme", "3 Tamil puzzle", "4 English puzzle"]
    pages = "\n".join(f'    <inkscape:page x="{x:.3f}" y="0" width="{W:.3f}" height="{H:.3f}" '
                      f'id="page{i+1}" inkscape:label="{n}"/>' for i, (x, n) in enumerate(zip(xs, names)))
    bgs = "\n".join(f'<rect x="{x:.3f}" y="0" width="{W:.3f}" height="{H:.3f}" '
                    f'style="fill:{t["background"]}" inkscape:label="Paper {i+1}"/>{frame(x, W, H, t)}'
                    for i, x in enumerate(xs))

    def layer(id_, label, body, hidden=False):
        st = ' style="display:none"' if hidden else ""
        return (f'  <g inkscape:groupmode="layer" id="{id_}" inkscape:label="{label}"{st}>\n'
                f'{body}\n  </g>\n')

    svg = (f'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
           f'<!-- Generated by build.py from {Path(cfg_path).name}. Edit freely in Inkscape. -->\n'
           f'<svg xmlns="http://www.w3.org/2000/svg" '
           f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
           f'xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" '
           f'width="{total_w/MM:.3f}mm" height="{H/MM:.3f}mm" viewBox="0 0 {total_w:.3f} {H:.3f}" version="1.1">\n'
           f'  <title>{esc(cfg["cover"]["couple_en"])} - Wedding Programme</title>\n'
           f'  <sodipodi:namedview id="namedview" pagecolor="#e9e4da" bordercolor="#999999" '
           f'inkscape:document-units="mm" inkscape:pagecheckerboard="false">\n{pages}\n'
           f'  </sodipodi:namedview>\n'
           + layer("layer-bg", "Background", bgs)
           + layer("layer-p1", "Page 1 - Cover", p1)
           + layer("layer-p2", "Page 2 - Programme", p2)
           + layer("layer-p3", "Page 3 - Tamil puzzle", p3)
           + layer("layer-p4", "Page 4 - English puzzle &amp; verse", p4)
           + layer("layer-key", "Answer Keys (hidden)", key3 + "\n" + key4, hidden=True)
           + "</svg>\n")
    out = Path(out_path)
    out.write_text(svg, encoding="utf-8")

    lines = []
    for title, grid, placed in (("TAMIL WORD SEARCH", grid3, placed3),
                                ("ENGLISH WORD SEARCH", grid4, placed4)):
        lines += [title, ""] + ["  " + " ".join(f"{c:<3}" for c in row) for row in grid] + [""]
        lines += [f'  {p["word"]:<14} row {p["row"]+1:>2}, col {p["col"]+1:>2}, {p["dir"]}'
                  for p in placed] + ["", ""]
    out.with_name(out.stem + "-answer-key.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out.name}: Tamil {len(placed3)} words, English {len(placed4)} words")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else HERE / "wedding.json",
          sys.argv[2] if len(sys.argv) > 2 else HERE / "wedding-programme.svg")
