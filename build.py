#!/usr/bin/env python3
"""
Fill an SVG template with the content of a JSON file.

    python3 build.py                                   # defaults below
    python3 build.py -t templates/programme-a5.svg -d wedding.json -o output/wedding-programme.svg

The design lives entirely in the template (edit it in Inkscape). This script
knows nothing about weddings. It only understands these template conventions:

  {{path.to.value}}   in any text is replaced from the JSON (lists count from 0:
                      {{programme.items.2.en}}). Values may contain placeholders.

  ?Label              an element whose Inkscape label starts with "?" is removed
                      when any placeholder inside it is missing or empty
                      (e.g. unused ceremony-item slots).

  [w=300]             in a text's label: shrink the text to fit 300 units wide.
                      Texts without it are kept inside their page's margins.

  #puzzle KEY         a group holding a rect labelled "area" (the grid box) and a
                      text labelled "letter" (its font/colour is used for the grid).
                      The word search for JSON section KEY is drawn there.
                      Optional: an element labelled "answer" sets the answer-key colour.

  #wordlist KEY       a group holding a rect labelled "area" and a group labelled
                      "entry" drawn at the area's top-left cell. The entry is repeated
                      for each word in a grid of KEY.list_columns columns; inside it,
                      {{word}} and {{gloss}} are replaced per word.

Answer keys go on a hidden "Answer Keys" layer and into a .txt beside the output.
Only the Python 3 standard library is required; with Pillow installed, text
fitting measures the real fonts in fonts/ (otherwise it estimates).
"""
import argparse
import copy
import json
import math
import random
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent

NS = {
    "svg": "http://www.w3.org/2000/svg",
    "inkscape": "http://www.inkscape.org/namespaces/inkscape",
    "sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd",
    "xlink": "http://www.w3.org/1999/xlink",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "cc": "http://creativecommons.org/ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
}
for p, u in NS.items():
    ET.register_namespace("" if p == "svg" else p, u)
SVG = "{%s}" % NS["svg"]
LABEL = "{%s}label" % NS["inkscape"]
GROUPMODE = "{%s}groupmode" % NS["inkscape"]
PLACEHOLDER = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
PAGE_MARGIN = 40

DIRECTIONS = {
    "right": (0, 1), "down": (1, 0), "down-right": (1, 1), "up-right": (-1, 1),
    "left": (0, -1), "up": (-1, 0), "up-left": (-1, -1), "down-left": (1, -1),
}


# ====================================================================== data
class Data:
    def __init__(self, root):
        self.root = root
        self.missing = set()

    def get(self, path, local=None):
        if local and path in local:
            return str(local[path])
        cur = self.root
        for part in path.split("."):
            if isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
                cur = cur[int(part)]
            elif isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return None
        if isinstance(cur, (dict, list)):
            return None
        return str(cur)

    def node(self, path):
        cur = self.root
        for part in [p for p in path.split(".") if p]:
            if isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
                cur = cur[int(part)]
            elif isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return None
        return cur

    def fill(self, s, local=None, depth=0):
        def rep(m):
            v = self.get(m.group(1), local)
            if v is None:
                self.missing.add(m.group(1))
                return ""
            return self.fill(v, local, depth + 1) if depth < 5 else v
        return PLACEHOLDER.sub(rep, s)

    def all_present(self, s, local=None):
        for m in PLACEHOLDER.finditer(s):
            v = self.get(m.group(1), local)
            if v is None or self.fill(v, local).strip() == "":
                return False
        return True


# ====================================================================== tamil letters + puzzle
TAMIL_MARKS = set(range(0x0BBE, 0x0BCE)) | {0x0B82, 0x0BD7, 0x200C, 0x200D}


def letters(word):
    """Split into letters as a reader sees them (க், கா, கொ = one box each)."""
    out = []
    for ch in word:
        if ch.isspace() or ch in "-'.,?!·":
            continue
        if out and ord(ch) in TAMIL_MARKS:
            out[-1] += ch
        else:
            out.append(ch.upper())
    return out


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
            n, opts = len(toks), []
            for d in dirs:
                dr, dc = DIRECTIONS[d]
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
            d_pick = rng.choice(sorted({o[4] for o in opts}))  # vary directions
            opts = sorted((o for o in opts if o[4] == d_pick), key=lambda o: (-min(o[0], 1), o[1]))
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


def puzzle_words(section):
    out = []
    for w in section.get("words", []):
        out.append(w if isinstance(w, dict) else {"word": w})
    return out


# ====================================================================== geometry
def parse_transform(s):
    m = [1, 0, 0, 1, 0, 0]
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", s or ""):
        a = [float(v) for v in re.split(r"[\s,]+", args.strip()) if v]
        if name == "translate":
            t = [1, 0, 0, 1, a[0], a[1] if len(a) > 1 else 0]
        elif name == "scale":
            t = [a[0], 0, 0, a[1] if len(a) > 1 else a[0], 0, 0]
        elif name == "matrix":
            t = a
        elif name == "rotate":
            r = math.radians(a[0])
            cx, cy = (a[1], a[2]) if len(a) > 2 else (0, 0)
            t = mul([1, 0, 0, 1, cx, cy], mul([math.cos(r), math.sin(r), -math.sin(r), math.cos(r), 0, 0],
                                              [1, 0, 0, 1, -cx, -cy]))
        else:
            continue
        m = mul(m, t)
    return m


def mul(a, b):
    return [a[0]*b[0] + a[2]*b[1], a[1]*b[0] + a[3]*b[1], a[0]*b[2] + a[2]*b[3],
            a[1]*b[2] + a[3]*b[3], a[0]*b[4] + a[2]*b[5] + a[4], a[1]*b[4] + a[3]*b[5] + a[5]]


def apply(m, x, y):
    return m[0]*x + m[2]*y + m[4], m[1]*x + m[3]*y + m[5]


class Tree:
    def __init__(self, root):
        self.root = root
        self.parent = {c: p for p in root.iter() for c in p}

    def ctm(self, el, include_self=True):
        chain = []
        e = el if include_self else self.parent.get(el)
        while e is not None:
            chain.append(e.get("transform"))
            e = self.parent.get(e)
        m = [1, 0, 0, 1, 0, 0]
        for t in reversed(chain):
            m = mul(m, parse_transform(t))
        return m

    def remove(self, el):
        p = self.parent.get(el)
        if p is not None:
            p.remove(el)

    def reindex(self):
        self.parent = {c: p for p in self.root.iter() for c in p}


def label(el):
    return el.get(LABEL, "")


def style_dict(el):
    out = {}
    for part in (el.get("style") or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = v.strip()
    for k in ("font-family", "font-size", "font-style", "font-weight", "fill", "text-anchor"):
        if el.get(k) and k not in out:
            out[k] = el.get(k)
    return out


def style_str(d):
    return ";".join(f"{k}:{v}" for k, v in d.items())


def num(v, default=0.0):
    m = re.match(r"\s*(-?[\d.]+)", str(v or ""))
    return float(m.group(1)) if m else default


def rect_box(el):
    return num(el.get("x")), num(el.get("y")), num(el.get("width")), num(el.get("height"))


# ====================================================================== text measuring
WEIGHTS = {"thin": 100, "extralight": 200, "light": 300, "regular": 400, "medium": 500,
           "semibold": 600, "bold": 700, "extrabold": 800, "black": 900}


class Fonts:
    """Finds the font file for a family/weight/italic in fonts/ to measure text widths."""
    def __init__(self, folder):
        self.faces = {}   # (family, italic) -> [(weight, path, variable)]
        self.cache = {}
        try:
            from PIL import ImageFont
            self.IF = ImageFont
        except ImportError:
            self.IF = None
            return
        for f in sorted(Path(folder).glob("*.[ot]tf")):
            try:
                font = ImageFont.truetype(str(f), 10)
                fam, sty = font.getname()
            except Exception:
                continue
            try:
                variable = any(a.get("name") in (b"Weight", "Weight") for a in font.get_variation_axes())
            except Exception:
                variable = False
            sty_l = (sty or "").lower().replace(" ", "")
            italic = "italic" in sty_l or "italic" in f.name.lower()
            w = next((v for k, v in sorted(WEIGHTS.items(), key=lambda kv: -len(kv[0])) if k in sty_l), 400)
            self.faces.setdefault((fam.lower(), italic), []).append((w, f, variable))

    def width(self, s, family, size, italic, weight=400):
        fam = family.split(",")[0].strip().strip("'\"").lower()
        faces = self.faces.get((fam, italic)) or self.faces.get((fam, False))
        if not self.IF or not faces:
            return len(s) * size * 0.55
        w, path, variable = min(faces, key=lambda t: abs(t[0] - weight) if not t[2] else 0)
        k = (path, round(size * 4), weight if variable else w)
        if k not in self.cache:
            try:
                font = self.IF.truetype(str(path), size, layout_engine=self.IF.Layout.RAQM)
            except Exception:
                font = self.IF.truetype(str(path), size)
            if variable:
                try:
                    axes = font.get_variation_axes()
                    font.set_variation_by_axes([weight if a.get("name") in (b"Weight", "Weight")
                                                else a.get("default", 100) for a in axes])
                except Exception:
                    pass
            self.cache[k] = font
        return self.cache[k].getlength(s)


def weight_of(st):
    v = str(st.get("font-weight", "400")).strip().lower()
    return {"normal": 400, "bold": 700, "lighter": 300, "bolder": 700}.get(v, int(num(v, 400)) or 400)


def text_style(el):
    st = {}
    for e in [el] + [d for d in el.iter() if d is not el and (d.text or "").strip()][:1]:
        st.update(style_dict(e))
    return st


def scale_font(el, factor):
    for e in el.iter():
        st = style_dict(e)
        changed = False
        for k in ("font-size", "letter-spacing"):
            if k in st and re.match(r"\s*-?[\d.]", st[k]):
                unit = re.sub(r"^\s*-?[\d.]+", "", st[k])
                st[k] = f"{num(st[k]) * factor:.2f}{unit}"
                changed = True
        if changed:
            e.set("style", style_str(st))
        if e.get("font-size"):
            e.set("font-size", f"{num(e.get('font-size')) * factor:.2f}")


def fit_text(el, tree, fonts, pages):
    s = "".join(el.itertext())
    if not s.strip():
        return
    st = text_style(el)
    size = num(st.get("font-size"), 16)
    italic = "italic" in st.get("font-style", "")
    spacing = num(st.get("letter-spacing"), 0)
    lab = label(el)
    m = re.search(r"\[w=([\d.]+)\]", lab)
    if m:
        avail = float(m.group(1))
    else:
        anchor = st.get("text-anchor", "start")
        first = next((e for e in el.iter() if e.get("x")), el)
        ctm = tree.ctm(first)
        ax, ay = apply(ctm, num(first.get("x")), num(first.get("y")))
        page = next((p for p in pages if p[0] <= ax <= p[0] + p[2] and p[1] <= ay <= p[1] + p[3]), None)
        if not page:
            return
        left, right = page[0] + PAGE_MARGIN, page[0] + page[2] - PAGE_MARGIN
        avail_abs = {"middle": 2 * min(ax - left, right - ax), "end": ax - left}.get(anchor, right - ax)
        avail = avail_abs / (math.hypot(ctm[0], ctm[1]) or 1)
    w = fonts.width(s, st.get("font-family", ""), size, italic, weight_of(st)) + spacing * len(s)
    if avail > 0 and w > avail:
        scale_font(el, max(avail / w, 0.3))


# ====================================================================== template features
def parse_marker(lab):
    """'#puzzle tamil_puzzle lines=off scale=0.4' -> ('tamil_puzzle', {'lines': 'off', 'scale': '0.4'})"""
    parts = lab.split()
    opts = dict(p.split("=", 1) for p in parts[2:] if "=" in p)
    return (parts[1] if len(parts) > 1 else ""), opts


def truthy(v):
    return str(v).strip().lower() not in ("off", "no", "false", "0", "none")


def expand_puzzle(group, key, data, tree, answers_layer, key_lines, opts=None):
    opts = opts or {}
    cfg = data.root.get(key)
    if cfg is None:
        print(f"  ! no '{key}' section in JSON - puzzle left empty")
        return
    area = next((c for c in group if label(c) == "area"), None)
    sample = next((c for c in group.iter() if label(c) == "letter"), None)
    ans = next((c for c in group.iter() if label(c) == "answer"), None)
    tile = next((c for c in group.iter() if label(c) == "cell"), None)
    cline = next((c for c in group.iter() if label(c) == "cell line"), None)
    show_lines = truthy(opts.get("lines", cfg.get("cell_lines", True)))
    scale = float(opts.get("scale", cfg.get("letter_scale", 0.5)))
    inset = float(opts.get("inset", 0.08))
    if area is None:
        sys.exit(f"#puzzle {key}: needs a rect labelled 'area'")
    words = [w["word"] for w in puzzle_words(cfg)]
    rows, cols = int(cfg.get("rows", 12)), int(cfg.get("cols", 12))
    grid, placed = make_word_search(words, rows, cols, int(cfg.get("seed", 1)),
                                    cfg.get("directions", ["right", "down"]))
    x, y, w, h = rect_box(area)
    cell = min(w / cols, h / rows)
    gx, gy = x + (w - cell * cols) / 2, y + (h - cell * rows) / 2
    area.set("x", f"{gx:.2f}"); area.set("y", f"{gy:.2f}")
    area.set("width", f"{cell*cols:.2f}"); area.set("height", f"{cell*rows:.2f}")
    area_style = style_dict(area)
    tile_style = style_dict(tile) if tile is not None else None
    tile_rx = (num(tile.get("rx")) / max(num(tile.get("width"), 1), 1)) if tile is not None else 0
    cline_style = style_dict(cline) if cline is not None else None
    for c in list(group):
        if c is not area:
            group.remove(c)
    holder = ET.SubElement(group, SVG + "g", {LABEL: "Grid"})
    if area.get("transform"):
        holder.set("transform", area.get("transform"))
    if tile_style:
        tg = ET.SubElement(holder, SVG + "g", {LABEL: "Cell tiles"})
        ts = cell * (1 - 2 * inset)
        for r in range(rows):
            for c in range(cols):
                ET.SubElement(tg, SVG + "rect", {
                    "x": f"{gx + cell*c + cell*inset:.2f}", "y": f"{gy + cell*r + cell*inset:.2f}",
                    "width": f"{ts:.2f}", "height": f"{ts:.2f}", "rx": f"{ts*tile_rx:.2f}",
                    "style": style_str(tile_style)})
    if show_lines:
        d = "".join(f"M {gx+cell*c:.2f},{gy:.2f} V {gy+cell*rows:.2f} " for c in range(1, cols))
        d += "".join(f"M {gx:.2f},{gy+cell*r:.2f} H {gx+cell*cols:.2f} " for r in range(1, rows))
        ls = dict(cline_style) if cline_style else {
            "stroke": area_style.get("stroke", "#999999"), "stroke-opacity": "0.35", "stroke-width": "0.7"}
        ls["fill"] = "none"
        ET.SubElement(holder, SVG + "path", {"d": d, LABEL: "Cell lines", "style": style_str(ls)})
    lst = text_style(sample) if sample is not None else {}
    for k in ("letter-spacing", "text-align", "line-height"):
        lst.pop(k, None)
    size = cell * scale
    lst.update({"font-size": f"{size:.2f}px", "text-anchor": "middle"})
    for r in range(rows):
        rg = ET.SubElement(holder, SVG + "g", {LABEL: f"Row {r+1}"})
        for c in range(cols):
            t = ET.SubElement(rg, SVG + "text", {
                "x": f"{gx + cell*(c+.5):.2f}", "y": f"{gy + cell*(r+.5) + size*0.36:.2f}",
                "style": style_str(lst), "{http://www.w3.org/XML/1998/namespace}space": "preserve"})
            t.text = grid[r][c]
    # answer key, drawn in absolute coordinates on the hidden layer
    acolor = "#e8962e"
    if ans is not None:
        ast = style_dict(ans)
        acolor = ast.get("stroke") if ast.get("stroke", "none") != "none" else ast.get("fill", acolor)
    m = tree.ctm(area)
    ag = ET.SubElement(answers_layer, SVG + "g", {LABEL: f"Answers {key}",
                                                  "transform": "matrix(%s)" % ",".join(f"{v:.6f}" for v in m)})
    for p in placed:
        dr, dc = DIRECTIONS[p["dir"]]
        n = len(p["toks"]) - 1
        ET.SubElement(ag, SVG + "line", {
            "x1": f"{gx+cell*(p['col']+.5):.2f}", "y1": f"{gy+cell*(p['row']+.5):.2f}",
            "x2": f"{gx+cell*(p['col']+dc*n+.5):.2f}", "y2": f"{gy+cell*(p['row']+dr*n+.5):.2f}",
            LABEL: f"Answer {p['word']}",
            "style": f"stroke:{acolor};stroke-opacity:0.4;stroke-width:{cell*0.72:.2f};stroke-linecap:round"})
    key_lines += [key.upper().replace("_", " "), ""]
    key_lines += ["  " + " ".join(f"{c:<3}" for c in row) for row in grid] + [""]
    key_lines += [f"  {p['word']:<14} row {p['row']+1:>2}, col {p['col']+1:>2}, {p['dir']}"
                  for p in placed] + ["", ""]
    print(f"  puzzle {key}: {len(placed)} words in {rows}x{cols}")


BLANK = {".", "x", "X", "-", "_", "#"}


def scramble(word):
    toks = letters(word)
    rng = random.Random(word)
    out = toks[:]
    for _ in range(30):
        rng.shuffle(out)
        if out != toks:
            break
    return "".join(out)


def entry_fit_labels(e, x, colw):
    """Give every text in a repeated entry a [w=] so it stays inside its column."""
    for el in e.iter(SVG + "text"):
        tx = num(next((d.get("x") for d in el.iter() if d.get("x")), x))
        anchor = text_style(el).get("text-anchor", "start")
        if anchor == "middle":
            w = 2 * min(tx - x, x + colw - tx) - 4
        elif anchor == "end":
            w = tx - x - 4
        else:
            w = x + colw - tx - 4
        m = re.search(r"\[w=([\d.]+)\]", label(el))
        if m:  # a width set in the template wins if it is tighter
            w = min(w, float(m.group(1)))
        el.set(LABEL, re.sub(r"\s*\[w=[\d.]+\]", "", label(el)) + f" [w={max(w, 10):.0f}]")


def expand_list(group, path, data, opts=None):
    """Repeat the group's 'entry' for every item of the JSON list at PATH."""
    opts = opts or {}
    items = data.node(path)
    if not isinstance(items, list):
        print(f"  ! no list at '{path}' in JSON - left empty")
        group.clear()
        return
    area = next((c for c in group if label(c) == "area"), None)
    entry = next((c for c in group if label(c) == "entry"), None)
    if area is None or entry is None:
        sys.exit(f"#list {path}: needs a rect labelled 'area' and a group labelled 'entry'")
    items = [it if isinstance(it, dict) else {"word": it} for it in items]
    order = list(range(len(items)))
    if "shuffle" in opts:
        rng = random.Random(int(num(opts["shuffle"], 1)))
        for _ in range(20):
            rng.shuffle(order)
            if len(order) < 2 or all(o != i for i, o in enumerate(order)):
                break
    ncol = max(1, int(num(opts.get("columns"), 1)))
    per = max(1, math.ceil(len(items) / ncol), int(num(opts.get("rows"), 0)))
    x, y, w, h = rect_box(area)
    colw, rowh = w / ncol, h / per
    group.remove(area)
    group.remove(entry)
    letter_of = {}
    phon = data.root.get("phonetics", {}) if isinstance(data.root.get("phonetics"), dict) else {}
    uses_ph = re.search(r"\{\{ph(_paren)?\}\}", ET.tostring(entry, encoding="unicode")) is not None
    missing_ph = []
    for pos, idx in enumerate(order):
        it = items[idx]
        col, row = divmod(pos, per)
        local = {k: v for k, v in it.items() if not isinstance(v, (dict, list))}
        for k, v in (("n", pos + 1), ("letter", chr(65 + pos)), ("number", idx + 1)):
            local.setdefault(k, v)   # an item's own field (e.g. a crossword clue number) wins
        if "word" in it:
            local["scrambled"] = scramble(str(it["word"]))
        if "ph" not in local:  # phonetic form from the shared "phonetics" dictionary
            key_text = str(it.get("ta", it.get("word", "")))
            local["ph"] = phon.get(key_text, "")
            if not local["ph"] and uses_ph and key_text:
                missing_ph.append(key_text)
        local.setdefault("ph_paren", f" ({local['ph']})" if local.get("ph") else "")
        letter_of[idx] = chr(65 + pos)
        e = copy.deepcopy(entry)
        e.set(LABEL, f"Item {pos+1}")
        t = f"translate({col*colw:.2f},{row*rowh:.2f})"
        e.set("transform", t + (" " + entry.get("transform") if entry.get("transform") else ""))
        for el in e.iter():
            for attr in ("text", "tail"):
                v = getattr(el, attr)
                if v and "{{" in v:
                    setattr(el, attr, data.fill(v, local))
        entry_fit_labels(e, x, colw)
        group.append(e)
    if missing_ph:
        print(f"  ! no phonetics for: {', '.join(missing_ph)} (add them to \"phonetics\" in games.json)")
    # answer strings for the template, e.g. {{trivia.questions_answers}}
    parent_path, _, leaf = path.rpartition(".")
    parent = data.node(parent_path) if parent_path else data.root
    if isinstance(parent, dict):
        if any("answer" in it for it in items):
            parent[f"{leaf}_answers"] = "  ".join(f"{i+1}-{it.get('answer', '?')}" for i, it in enumerate(items))
        elif any("word" in it for it in items):
            parent[f"{leaf}_answers"] = "  ".join(f"{i+1}. {it['word']}" for i, it in enumerate(items))
        if "shuffle" in opts:
            parent[f"{leaf}_match"] = "  ".join(f"{i+1}-{letter_of[i]}" for i in range(len(items)))


def prepare_crossword(cfg, key):
    """Number the grid and collect across/down answers into cfg['across'] / cfg['down']."""
    rows = [str(r).split() for r in cfg.get("grid", [])]
    R, C = len(rows), max((len(r) for r in rows), default=0)
    cell = lambda r, c: (rows[r][c] if 0 <= r < R and 0 <= c < len(rows[r]) and rows[r][c] not in BLANK else None)
    clues = cfg.get("clues", {})
    across, down, numbers = [], [], {}
    n = 0
    for r in range(R):
        for c in range(C):
            if not cell(r, c):
                continue
            a = cell(r, c - 1) is None and cell(r, c + 1) is not None
            d = cell(r - 1, c) is None and cell(r + 1, c) is not None
            alone = not any(cell(r + dr, c + dc) for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)))
            if not (a or d or alone):
                continue
            n += 1
            numbers[(r, c)] = n
            for flag, dr, dc, lst in ((a or alone, 0, 1, across), (d, 1, 0, down)):
                if not flag:
                    continue
                toks, rr, cc = [], r, c
                while cell(rr, cc):
                    toks.append(cell(rr, cc))
                    rr, cc = rr + dr, cc + dc
                ans = "".join(toks)
                if ans not in clues:
                    print(f"  ! {key}: no clue for '{ans}' ({n} {'across' if lst is across else 'down'})")
                lst.append({"n": n, "answer": ans, "clue": clues.get(ans, "…"), "len": len(toks),
                            "row": r, "col": c})
    cfg["across"], cfg["down"] = across, down
    return rows, R, C, cell, numbers


def expand_crossword(group, key, data, tree, answers_layer, key_lines):
    cfg = data.root.get(key)
    if not isinstance(cfg, dict) or "across" not in cfg:
        print(f"  ! no crossword '{key}' in JSON")
        return
    rows, R, C, cell, numbers = cfg["_grid"]
    area = next((c for c in group if label(c) == "area"), None)
    sample = {lab: next((c for c in group.iter() if label(c) == lab), None) for lab in ("cell", "number", "letter")}
    if area is None:
        sys.exit(f"#crossword {key}: needs a rect labelled 'area'")
    x, y, w, h = rect_box(area)
    size = min(w / C, h / R)
    gx, gy = x + (w - size * C) / 2, y + (h - size * R) / 2
    cst = style_dict(sample["cell"]) if sample["cell"] is not None else {"fill": "#ffffff", "stroke": "#333333", "stroke-width": "1"}
    nst = text_style(sample["number"]) if sample["number"] is not None else {"font-size": "7px", "fill": "#333333"}
    lst = text_style(sample["letter"]) if sample["letter"] is not None else {"fill": "#333333"}
    nsize = num(nst.get("font-size"), 7)
    nst.update({"text-anchor": "start"})
    lst.update({"text-anchor": "middle", "font-size": f"{size*0.42:.2f}px"})
    for k in ("letter-spacing",):
        nst.pop(k, None); lst.pop(k, None)
    for c in list(group):
        group.remove(c)
    cells_g = ET.SubElement(group, SVG + "g", {LABEL: "Cells"})
    nums_g = ET.SubElement(group, SVG + "g", {LABEL: "Numbers"})
    key_g = ET.SubElement(answers_layer, SVG + "g", {LABEL: f"Answers {key}", "transform":
                          "matrix(%s)" % ",".join(f"{v:.6f}" for v in tree.ctm(group))})
    for r in range(R):
        for c in range(C):
            v = cell(r, c)
            if not v:
                continue
            cx, cy = gx + c * size, gy + r * size
            ET.SubElement(cells_g, SVG + "rect", {"x": f"{cx:.2f}", "y": f"{cy:.2f}", "width": f"{size:.2f}",
                                                  "height": f"{size:.2f}", "style": style_str(cst)})
            if (r, c) in numbers:
                t = ET.SubElement(nums_g, SVG + "text", {"x": f"{cx + size*0.07:.2f}", "y": f"{cy + nsize + size*0.04:.2f}",
                                                         "style": style_str(nst)})
                t.text = str(numbers[(r, c)])
            t = ET.SubElement(key_g, SVG + "text", {"x": f"{cx + size/2:.2f}", "y": f"{cy + size*0.66:.2f}",
                                                    "style": style_str(lst)})
            t.text = v
    key_lines += [key.upper().replace("_", " "), ""]
    key_lines += ["  " + " ".join(f"{(cell(r, c) or '·'):<3}" for c in range(C)) for r in range(R)] + [""]
    for name in ("across", "down"):
        key_lines += [f"  {name.upper()}"] + [f"   {e['n']:>2}. {e['answer']}" for e in cfg[name]]
    key_lines += ["", ""]
    print(f"  crossword {key}: {len(cfg['across'])} across, {len(cfg['down'])} down")


# ====================================================================== pages
def normalize_pages(root):
    """Inkscape (1.2+) treats the document's width/height/viewBox as page 1.
    If that covers the whole multi-page canvas, every PDF page comes out wrong.
    Shrink page 1 to the size of the other pages and make the document size match it."""
    nv = root.find("{%s}namedview" % NS["sodipodi"])
    pages = list(nv.iter("{%s}page" % NS["inkscape"])) if nv is not None else []
    if not pages:
        return False
    box = lambda p: [num(p.get(k)) for k in ("x", "y", "width", "height")]
    p1 = box(pages[0])
    changed = False
    if len(pages) > 1:
        others = [box(p) for p in pages[1:]]
        swallows = any(p1[0] <= o[0] + 1 and o[0] + o[2] <= p1[0] + p1[2] + 1 for o in others)
        if swallows:
            p1[2], p1[3] = others[0][2], others[0][3]
            pages[0].set("width", f"{p1[2]:.3f}")
            pages[0].set("height", f"{p1[3]:.3f}")
            changed = True
    vb = [float(v) for v in (root.get("viewBox") or "").replace(",", " ").split()] or None
    if vb and [round(v, 2) for v in vb] != [round(v, 2) for v in p1]:
        for attr, idx in (("width", 2), ("height", 3)):
            m = re.match(r"\s*([\d.]+)\s*([a-z%]*)", root.get(attr) or "")
            if m and vb[idx]:
                root.set(attr, f"{float(m.group(1)) * p1[idx] / vb[idx]:.3f}{m.group(2)}")
        root.set("viewBox", " ".join(f"{v:.3f}" for v in p1))
        changed = True
    return changed


# ====================================================================== pdf via inkscape
WINDOWS_INKSCAPE = ["/mnt/c/Program Files/Inkscape/bin/inkscape.com",
                    "/mnt/c/Program Files/Inkscape/bin/inkscape.exe",
                    "/mnt/c/Program Files (x86)/Inkscape/bin/inkscape.com"]


def find_inkscape():
    """INKSCAPE env var, then inkscape on PATH, then a Windows install reached from WSL."""
    import os
    import shutil
    for c in [os.environ.get("INKSCAPE"), shutil.which("inkscape"), shutil.which("inkscape.com"),
              *WINDOWS_INKSCAPE]:
        if c and Path(c).exists():
            return c
    return None


def to_pdf(svg_path, text_to_path=False):
    import subprocess
    ink = find_inkscape()
    if not ink:
        print("  ! Inkscape not found. Install Inkscape 1.2+ or set INKSCAPE=/path/to/inkscape")
        return None
    windows = ink.startswith("/mnt/") or ink.lower().endswith((".exe", ".com"))

    def arg(p):  # Windows Inkscape needs Windows-style paths
        p = str(Path(p).resolve())
        if windows:
            return subprocess.run(["wslpath", "-w", p], capture_output=True, text=True).stdout.strip()
        return p

    ver = subprocess.run([ink, "--version"], capture_output=True, text=True).stdout
    m = re.search(r"Inkscape (\d+)\.(\d+)", ver)
    if m and (int(m.group(1)), int(m.group(2))) < (1, 2):
        print(f"  ! {ver.strip()} is too old for multi-page PDFs; install Inkscape 1.2 or newer")
        return None
    import time
    pdf = Path(svg_path).with_suffix(".pdf")
    if pdf.exists():  # remove the old PDF so a stale file can never pass as the new one
        try:
            pdf.unlink()
        except OSError:
            print(f"  ! cannot replace {pdf} - is it open in a PDF viewer? Close it and run again.")
            return None
    cmd = [ink, arg(svg_path), "--export-type=pdf", f"--export-filename={arg(pdf)}"]
    if text_to_path:
        cmd.append("--export-text-to-path")
    started = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not pdf.exists() or pdf.stat().st_mtime < started - 2:
        print("  ! Inkscape did not write a new PDF (is the file open in a viewer?)")
        msg = (r.stderr or r.stdout or "").strip()
        if msg:
            print("    " + msg[-800:].replace("\n", "\n    "))
        return None
    stamp = time.strftime("%H:%M:%S", time.localtime(pdf.stat().st_mtime))
    print(f"  PDF: {pdf}  (written {stamp})" + ("  (text converted to paths)" if text_to_path else ""))
    return pdf


def check_fonts(root, fonts):
    """Warn about fonts used in the template that are not in fonts/."""
    fams = set()
    for el in root.iter():
        f = style_dict(el).get("font-family")
        if f:
            fams.add(f.split(",")[0].strip().strip("'\""))
    known = {fam for fam, _ in fonts.faces}
    missing = sorted(f for f in fams if f.lower() not in known)
    if fonts.IF and missing:
        print("  ! fonts used but not in fonts/: " + ", ".join(missing)
              + " (make sure they are installed where Inkscape runs)")


# ====================================================================== main
def merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            merge(a[k], v)
        else:
            a[k] = v
    return a


def load_data(paths):
    root = {}
    for p in paths:
        merge(root, json.loads(Path(p).read_text(encoding="utf-8")))
    return root


def build(template, data_paths, out_path):
    if isinstance(data_paths, (str, Path)):
        data_paths = [data_paths]
    data = Data(load_data(data_paths))
    for k, v in data.root.items():  # handy derived values, e.g. {{tamil_puzzle.count}}
        if isinstance(v, dict) and "words" in v:
            v.setdefault("count", len(v["words"]))
        if isinstance(v, dict) and "grid" in v:
            v["_grid"] = prepare_crossword(v, k)
    tree_et = ET.parse(template)
    root = tree_et.getroot()
    if normalize_pages(root):
        print("  note: page 1 covered the whole canvas (Inkscape does this on save); "
              "fixed in the output. Run with --fix-template to fix the template too.")
    tree = Tree(root)
    fonts = Fonts(HERE / "fonts")
    check_fonts(root, fonts)
    pages = [(num(p.get("x")), num(p.get("y")), num(p.get("width")), num(p.get("height")))
             for p in root.iter("{%s}page" % NS["inkscape"])]
    if not pages:
        vb = [float(v) for v in (root.get("viewBox") or "0 0 1000 1000").replace(",", " ").split()]
        pages = [tuple(vb)]

    # 1. optional elements
    for el in list(root.iter()):
        if label(el).startswith("?"):
            content = " ".join(t for e in el.iter() for t in (e.text, e.tail) if t)
            if not data.all_present(content):
                tree.remove(el)
    tree.reindex()

    # 2. puzzles and word lists
    answers = ET.SubElement(root, SVG + "g", {GROUPMODE: "layer", "id": "layer-answer-keys",
                                              LABEL: "Answer Keys (hidden)", "style": "display:none"})
    key_lines = []
    for g in list(root.iter(SVG + "g")):
        lab = label(g)
        if lab.startswith("#puzzle "):
            k, o = parse_marker(lab)
            expand_puzzle(g, k, data, tree, answers, key_lines, o)
        elif lab.startswith("#wordlist "):
            k, o = parse_marker(lab)
            expand_list(g, k + ".words", data, {"columns": data.root.get(k, {}).get("list_columns", 3), **o})
        elif lab.startswith("#list "):
            k, o = parse_marker(lab)
            expand_list(g, k, data, o)
        elif lab.startswith("#crossword "):
            k, o = parse_marker(lab)
            expand_crossword(g, k, data, tree, answers, key_lines)
    tree.reindex()

    # 3. placeholders, then 4. fit text that received content
    filled = []
    for t in root.iter(SVG + "text"):
        hit = False
        for el in t.iter():
            for attr in ("text", "tail"):
                v = getattr(el, attr)
                if v and "{{" in v:
                    setattr(el, attr, data.fill(v))
                    hit = True
        if hit or re.search(r"\[w=", label(t)):
            filled.append(t)
    for t in filled:
        fit_text(t, tree, fonts, pages)
    for el in root.iter():  # tidy fit markers out of labels
        if "[w=" in label(el):
            el.set(LABEL, re.sub(r"\s*\[w=[\d.]+\]", "", label(el)))

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tree_et.write(out, encoding="UTF-8", xml_declaration=True)
    if key_lines:
        out.with_name(out.stem + "-answer-key.txt").write_text("\n".join(key_lines), encoding="utf-8")
    if data.missing:
        print("  ! placeholders with no value in JSON: " + ", ".join(sorted(data.missing)))
    if not fonts.IF:
        print("  (Pillow not installed: text fitting used estimates)")
    print(f"Wrote {out}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Fill an SVG template from JSON.")
    ap.add_argument("-t", "--template", default=HERE / "templates" / "programme-a5.svg")
    ap.add_argument("-d", "--data", action="append",
                    help="JSON content file(s); later files add to / override earlier ones "
                         "(default: wedding.json plus games.json if present)")
    ap.add_argument("-o", "--output", default=HERE / "output" / "wedding-programme.svg")
    ap.add_argument("--fix-template", action="store_true",
                    help="repair page 1 / document size in the template file itself, then build")
    ap.add_argument("--all", action="store_true",
                    help="build every templates/*.svg to output/<template name>.svg")
    ap.add_argument("--pdf", action="store_true",
                    help="also export a PDF with Inkscape (1.2+; Windows Inkscape works from WSL)")
    ap.add_argument("--text-to-path", action="store_true",
                    help="with --pdf: convert text to outlines (for print shops)")
    a = ap.parse_args()
    if not a.data:
        a.data = [HERE / "wedding.json"] + ([HERE / "games.json"] if (HERE / "games.json").exists() else [])
    if a.all:
        for t in sorted((HERE / "templates").glob("*.svg")):
            print(f"[{t.stem}]")
            out = build(t, a.data, HERE / "output" / f"{t.stem}.svg")
            if a.pdf:
                to_pdf(out, a.text_to_path)
        sys.exit(0)
    if a.fix_template:
        t = ET.parse(a.template)
        if normalize_pages(t.getroot()):
            t.write(a.template, encoding="UTF-8", xml_declaration=True)
            print(f"Fixed page sizes in {a.template}")
        else:
            print("Template page sizes already fine")
    out = build(a.template, a.data, a.output)
    if a.pdf:
        to_pdf(out, a.text_to_path)
