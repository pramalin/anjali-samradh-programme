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
class Fonts:
    def __init__(self, folder):
        self.files = {}
        self.cache = {}
        try:
            from PIL import ImageFont
            self.IF = ImageFont
        except ImportError:
            self.IF = None
            return
        for f in sorted(Path(folder).glob("*.[ot]tf")):
            try:
                fam, sty = ImageFont.truetype(str(f), 10).getname()
            except Exception:
                continue
            key = (fam.lower(), "italic" in (sty or "").lower() or "italic" in f.name.lower())
            self.files.setdefault(key, f)

    def width(self, s, family, size, italic):
        fam = family.split(",")[0].strip().strip("'\"").lower()
        f = self.files.get((fam, italic)) or self.files.get((fam, False))
        if not self.IF or not f:
            return len(s) * size * 0.55
        k = (f, round(size * 4))
        if k not in self.cache:
            try:
                self.cache[k] = self.IF.truetype(str(f), size, layout_engine=self.IF.Layout.RAQM)
            except Exception:
                self.cache[k] = self.IF.truetype(str(f), size)
        return self.cache[k].getlength(s)


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
    w = fonts.width(s, st.get("font-family", ""), size, italic) + spacing * len(s)
    if avail > 0 and w > avail:
        scale_font(el, max(avail / w, 0.3))


# ====================================================================== template features
def expand_puzzle(group, key, data, tree, answers_layer, key_lines):
    cfg = data.root.get(key)
    if cfg is None:
        print(f"  ! no '{key}' section in JSON - puzzle left empty")
        return
    area = next((c for c in group if label(c) == "area"), None)
    sample = next((c for c in group.iter() if label(c) == "letter"), None)
    ans = next((c for c in group.iter() if label(c) == "answer"), None)
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
    for c in list(group):
        if c is not area:
            group.remove(c)
    holder = ET.SubElement(group, SVG + "g", {LABEL: "Grid"})
    if area.get("transform"):
        holder.set("transform", area.get("transform"))
    if cfg.get("cell_lines", True):
        d = "".join(f"M {gx+cell*c:.2f},{gy:.2f} V {gy+cell*rows:.2f} " for c in range(1, cols))
        d += "".join(f"M {gx:.2f},{gy+cell*r:.2f} H {gx+cell*cols:.2f} " for r in range(1, rows))
        ET.SubElement(holder, SVG + "path", {"d": d, LABEL: "Cell lines", "style": style_str({
            "fill": "none", "stroke": area_style.get("stroke", "#999999"),
            "stroke-opacity": "0.35", "stroke-width": "0.7"})})
    lst = text_style(sample) if sample is not None else {}
    for k in ("letter-spacing", "text-align", "line-height"):
        lst.pop(k, None)
    size = cell * float(cfg.get("letter_scale", 0.5))
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


def expand_wordlist(group, key, data):
    cfg = data.root.get(key)
    if cfg is None:
        print(f"  ! no '{key}' section in JSON - word list left empty")
        return
    area = next((c for c in group if label(c) == "area"), None)
    entry = next((c for c in group if label(c) == "entry"), None)
    if area is None or entry is None:
        sys.exit(f"#wordlist {key}: needs a rect labelled 'area' and a group labelled 'entry'")
    words = puzzle_words(cfg)
    ncol = max(1, int(cfg.get("list_columns", 3)))
    per = max(1, math.ceil(len(words) / ncol))
    x, y, w, h = rect_box(area)
    colw, rowh = w / ncol, h / per
    group.remove(area)
    group.remove(entry)
    for i, wd in enumerate(words):
        col, row = divmod(i, per)
        e = copy.deepcopy(entry)
        e.set(LABEL, f"Word {wd['word']}")
        t = f"translate({col*colw:.2f},{row*rowh:.2f})"
        e.set("transform", t + (" " + entry.get("transform") if entry.get("transform") else ""))
        local = {"word": wd["word"], "gloss": wd.get("gloss", "")}
        for el in e.iter():
            for attr in ("text", "tail"):
                v = getattr(el, attr)
                if v and "{{" in v:
                    setattr(el, attr, data.fill(v, local))
            if el.tag == SVG + "text":
                tx = num(next((d.get("x") for d in el.iter() if d.get("x")), x))
                el.set(LABEL, re.sub(r"\s*\[w=[\d.]+\]", "", label(el)) + f" [w={x + colw - tx - 4:.0f}]")
        group.append(e)


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


# ====================================================================== main
def build(template, data_path, out_path):
    data = Data(json.loads(Path(data_path).read_text(encoding="utf-8")))
    for k, v in data.root.items():  # handy derived values, e.g. {{tamil_puzzle.count}}
        if isinstance(v, dict) and "words" in v:
            v.setdefault("count", len(v["words"]))
    tree_et = ET.parse(template)
    root = tree_et.getroot()
    if normalize_pages(root):
        print("  note: page 1 covered the whole canvas (Inkscape does this on save); "
              "fixed in the output. Run with --fix-template to fix the template too.")
    tree = Tree(root)
    fonts = Fonts(HERE / "fonts")
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
            expand_puzzle(g, lab.split(None, 1)[1].strip(), data, tree, answers, key_lines)
        elif lab.startswith("#wordlist "):
            expand_wordlist(g, lab.split(None, 1)[1].strip(), data)
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


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Fill an SVG template from JSON.")
    ap.add_argument("-t", "--template", default=HERE / "templates" / "programme-a5.svg")
    ap.add_argument("-d", "--data", default=HERE / "wedding.json")
    ap.add_argument("-o", "--output", default=HERE / "output" / "wedding-programme.svg")
    ap.add_argument("--fix-template", action="store_true",
                    help="repair page 1 / document size in the template file itself, then build")
    a = ap.parse_args()
    if a.fix_template:
        t = ET.parse(a.template)
        if normalize_pages(t.getroot()):
            t.write(a.template, encoding="UTF-8", xml_declaration=True)
            print(f"Fixed page sizes in {a.template}")
        else:
            print("Template page sizes already fine")
    build(a.template, a.data, a.output)
