# Original simple icons in a 100 x 100 box. Each part: (path d, "fill") or (path d, "stroke", width).
HEART = "M50 90 C22 70 6 54 6 34 C6 19 17 9 31 9 C40 9 46 14 50 22 C54 14 60 9 69 9 C83 9 94 19 94 34 C94 54 78 70 50 90 Z"
def small_heart(cx, cy, s):
    import re
    nums = iter(float(x) for x in re.findall(r"-?\d+\.?\d*", HEART))
    out, toks = [], re.findall(r"[MCZ]|-?\d+\.?\d*", HEART)
    i = 0
    for t in toks:
        if t in "MCZ": out.append(t); continue
        v = float(t)
        out.append(f"{(cx + (v - 50) * s) if i % 2 == 0 else (cy + (v - 50) * s):.1f}"); i += 1
    return " ".join(out)

ICONS = {
    "heart": [(HEART, "fill")],
    "kindness": [                                   # two cupped hands holding a small heart
        (small_heart(50, 33, 0.36), "fill"),
        ("M4 58 C12 55 26 63 40 74 L50 81 L60 74 C74 63 88 55 96 58 C97 72 80 90 50 95 C20 90 3 72 4 58 Z", "fill"),
    ],
    "cooking": [                                    # pot with lid and steam
        ("M16 52 H84 V72 C84 83 76 90 65 90 H35 C24 90 16 83 16 72 Z", "fill"),
        ("M6 54 H16 V64 H6 Z", "fill"), ("M84 54 H94 V64 H84 Z", "fill"),
        ("M12 47 C18 36 82 36 88 47 Z", "fill"),
        ("M43 37 C43 30 57 30 57 37 Z", "fill"),
        ("M36 27 C29 20 42 15 35 5", "stroke", 5), ("M50 27 C43 20 56 15 49 5", "stroke", 5),
        ("M64 27 C57 20 70 15 63 5", "stroke", 5),
    ],
    "food": [                                       # banana leaf meal: solid leaf, food cut out
        ("M2 64 C16 34 68 24 98 40 C86 74 32 88 2 64 Z", "fill"),
        ("M10 63 C40 53 68 47 92 42", "knock", 3),
        ("M22 58 C22 46 46 43 46 55 Z", "knockfill"),
        ("M58 50 m-9 0 a9 9 0 1 0 18 0 a9 9 0 1 0 -18 0 Z", "knockfill"),
        ("M80 50 m-6 0 a6 6 0 1 0 12 0 a6 6 0 1 0 -12 0 Z", "knockfill"),
        ("M40 69 m-7 0 a7 5.5 0 1 0 14 0 a7 5.5 0 1 0 -14 0 Z", "knockfill"),
    ],
    "india": [                                      # flag: saffron, white, green, navy wheel
        ("M10 22 H90 V42 H10 Z", "color", "#FF9933"),
        ("M10 42 H90 V62 H10 Z", "color", "#FFFFFF"),
        ("M10 62 H90 V82 H10 Z", "color", "#138808"),
        ("M50 52 m-8 0 a8 8 0 1 0 16 0 a8 8 0 1 0 -16 0", "colorstroke", "#000080", 2.6),
        ("M42 52 H58 M50 44 V60 M44.3 46.3 L55.7 57.7 M55.7 46.3 L44.3 57.7", "colorstroke", "#000080", 1.4),
        ("M10 22 H90 V82 H10 Z", "stroke", 2.5),
    ],
    "usa": [                                        # flag: stripes and a blue corner with stars
        ("M10 22 H90 V82 H10 Z", "color", "#FFFFFF"),
        ("M10 22.00 H90 V26.62 H10 Z", "color", "#B22234"),
        ("M10 31.23 H90 V35.85 H10 Z", "color", "#B22234"),
        ("M10 40.46 H90 V45.08 H10 Z", "color", "#B22234"),
        ("M10 49.69 H90 V54.31 H10 Z", "color", "#B22234"),
        ("M10 58.92 H90 V63.54 H10 Z", "color", "#B22234"),
        ("M10 68.15 H90 V72.77 H10 Z", "color", "#B22234"),
        ("M10 77.38 H90 V82.00 H10 Z", "color", "#B22234"),
        ("M10 22 H46 V54.3 H10 Z", "color", "#3C3B6E"),
        ("M18 28 m-2.4 0 a2.4 2.4 0 1 0 4.8 0 a2.4 2.4 0 1 0 -4.8 0 Z", "color", "#ffffff"),
        ("M28 28 m-2.4 0 a2.4 2.4 0 1 0 4.8 0 a2.4 2.4 0 1 0 -4.8 0 Z", "color", "#ffffff"),
        ("M38 28 m-2.4 0 a2.4 2.4 0 1 0 4.8 0 a2.4 2.4 0 1 0 -4.8 0 Z", "color", "#ffffff"),
        ("M23 36 m-2.4 0 a2.4 2.4 0 1 0 4.8 0 a2.4 2.4 0 1 0 -4.8 0 Z", "color", "#ffffff"),
        ("M33 36 m-2.4 0 a2.4 2.4 0 1 0 4.8 0 a2.4 2.4 0 1 0 -4.8 0 Z", "color", "#ffffff"),
        ("M18 44 m-2.4 0 a2.4 2.4 0 1 0 4.8 0 a2.4 2.4 0 1 0 -4.8 0 Z", "color", "#ffffff"),
        ("M28 44 m-2.4 0 a2.4 2.4 0 1 0 4.8 0 a2.4 2.4 0 1 0 -4.8 0 Z", "color", "#ffffff"),
        ("M38 44 m-2.4 0 a2.4 2.4 0 1 0 4.8 0 a2.4 2.4 0 1 0 -4.8 0 Z", "color", "#ffffff"),
        ("M10 22 H90 V82 H10 Z", "stroke", 2.5),
    ],
    "education": [                                  # graduation cap with tassel
        ("M50 16 L96 36 L50 56 L4 36 Z", "fill"),
        ("M24 46 V68 C24 80 76 80 76 68 V46 L50 58 Z", "fill"),
        ("M84 40 V66", "stroke", 4),
        ("M84 70 m-5 0 a5 6 0 1 0 10 0 a5 6 0 1 0 -10 0 Z", "fill"),
    ],
    "engineering": [                                # gear
        ("M 84.1 42.0 L 95.5 43.1 L 95.5 56.9 L 84.1 58.0 L 79.7 68.5 L 87.0 77.3 L 77.3 87.0 L 68.5 79.7 L 58.0 84.1 L 56.9 95.5 L 43.1 95.5 L 42.0 84.1 L 31.5 79.7 L 22.7 87.0 L 13.0 77.3 L 20.3 68.5 L 15.9 58.0 L 4.5 56.9 L 4.5 43.1 L 15.9 42.0 L 20.3 31.5 L 13.0 22.7 L 22.7 13.0 L 31.5 20.3 L 42.0 15.9 L 43.1 4.5 L 56.9 4.5 L 58.0 15.9 L 68.5 20.3 L 77.3 13.0 L 87.0 22.7 L 79.7 31.5 Z", "fill"),
        ("M50 50 m-14 0 a14 14 0 1 0 28 0 a14 14 0 1 0 -28 0 Z", "knockfill"),
    ],
    "cat": [                                        # sitting cat, tail curled round the front
        ("M30 92 C14 92 14 70 24 58 C30 50 30 44 28 38 C26 30 28 22 32 16 L34 4 L44 14 C48 13 52 13 56 14 L66 4 "
         "L68 16 C72 22 74 30 72 38 C70 44 70 50 76 58 C84 68 84 88 70 92 Z", "fill"),
        ("M66 92 C80 92 94 88 94 76 C94 68 86 66 84 72 C84 78 90 78 88 82 C84 86 74 86 66 86 Z", "fill"),
        ("M40 30 m-3 0 a3 3.5 0 1 0 6 0 a3 3.5 0 1 0 -6 0 Z", "knockfill"),
        ("M60 30 m-3 0 a3 3.5 0 1 0 6 0 a3 3.5 0 1 0 -6 0 Z", "knockfill"),
    ],
    "motorcycle": [                                 # side view
        ("M20 70 m-15 0 a15 15 0 1 0 30 0 a15 15 0 1 0 -30 0 Z", "stroke", 8),
        ("M80 70 m-15 0 a15 15 0 1 0 30 0 a15 15 0 1 0 -30 0 Z", "stroke", 8),
        ("M20 70 L34 52 H70 L80 70 L68 74 H34 Z", "fill"),
        ("M36 54 C36 40 66 38 68 52 Z", "fill"),
        ("M16 50 H42 V56 H18 Z", "fill"),
        ("M70 56 L58 30 H72", "stroke", 7),
        ("M80 46 m-5 0 a5 5 0 1 0 10 0 a5 5 0 1 0 -10 0 Z", "fill"),
    ],
}
ORDER = ["india", "education", "engineering", "usa", "kindness", "cooking", "food", "cat", "motorcycle", "heart"]

def svg_group(name, x, y, size, color, paper="#fbf6ec"):
    s = size / 100
    parts = []
    for part in ICONS[name]:
        d, kind = part[0], part[1]
        if kind == "fill":
            parts.append(f'<path d="{d}" style="fill:{color};stroke:none"/>')
        elif kind == "knockfill":
            parts.append(f'<path d="{d}" style="fill:{paper};stroke:none"/>')
        elif kind == "color":
            parts.append(f'<path d="{d}" style="fill:{part[2]};stroke:none"/>')
        elif kind == "colorstroke":
            parts.append(f'<path d="{d}" style="fill:none;stroke:{part[2]};stroke-width:{part[3]};stroke-linecap:round"/>')
        elif kind == "knock":
            parts.append(f'<path d="{d}" style="fill:none;stroke:{paper};stroke-width:{part[2]};stroke-linecap:round"/>')
        else:
            parts.append(f'<path d="{d}" style="fill:none;stroke:{color};stroke-width:{part[2]};stroke-linecap:round;stroke-linejoin:round"/>')
    return f'<g transform="translate({x:.2f},{y:.2f}) scale({s:.4f})" inkscape:label="Stop: {name}">' + "".join(parts) + "</g>"
