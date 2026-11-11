#!/usr/bin/env python3
"""
Generate the booklet's maze as SVG (lines only, transparent background), plus a solution version.
The website builds the same maze (web/build_web.py calls kruskal_maze).

    python3 maze.py --color "#3a2c24" --stroke 4 --out assets/maze.svg   # the booklet + web maze (20 x 23, seed 648)
    python3 maze.py --report                                               # how tricky is it?
    python3 maze.py --seed 7                                               # a different maze

Every maze has exactly one path from the entrance arrow (top left) to the exit arrow (bottom right).
Convert to PNG with Inkscape:
    inkscape assets/maze.svg --export-type=png --export-dpi=192 --export-background-opacity=0
"""
import argparse
import random
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent


# ---------------------------------------------------------------- even-textured rectangular maze (the booklet's)
def kruskal_maze(seed=648, rows=23, cols=20):
    """Randomly knock down walls between unconnected areas until everything joins (Kruskal). The texture is
    even - short dead ends and long walls everywhere, so the true route doesn't stand out - and choices come
    every few steps. Seed 648 gives a long route (118 squares) that winds at both ends.
    Groom: left of the top-left square; bride: right of the bottom-right square."""
    rng = random.Random(seed)
    walls = [((r, c), (r, c + 1)) for r in range(rows) for c in range(cols - 1)] + \
            [((r, c), (r + 1, c)) for r in range(rows - 1) for c in range(cols)]
    rng.shuffle(walls)
    parent = {(r, c): (r, c) for r in range(rows) for c in range(cols)}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    edges = set()
    for a, b in walls:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb; edges.add(frozenset((a, b)))
    adj = {}
    for e in edges:
        x, y = tuple(e); adj.setdefault(x, []).append(y); adj.setdefault(y, []).append(x)
    start, end = (0, 0), (rows - 1, cols - 1)
    prev, q = {start: None}, deque([start])
    while q:
        p = q.popleft()
        for x in adj.get(p, []):
            if x not in prev: prev[x] = p; q.append(x)
    path, p = [], end
    while p is not None: path.append(p); p = prev[p]
    cells = {(r, c) for r in range(rows) for c in range(cols)}
    return dict(rows=rows, cols=cols, n=max(rows, cols), cells=cells, edges=edges, start=start, end=end,
                path=path[::-1], rooms=[])


def svg_grid(m, cell, stroke, color, margin, solution=False, sol_color="#C05C27"):
    """Draw a rectangular maze: entrance left of the top-left square, exit right of the bottom-right one."""
    R, C, edges = m["rows"], m["cols"], m["edges"]
    W, H = C * cell + 2 * margin, R * cell + 2 * margin
    X = lambda c: margin + c * cell
    Y = lambda r: margin + r * cell
    segs = [(X(0), Y(0), X(C), Y(0)), (X(0), Y(R), X(C), Y(R)), (X(0), Y(1), X(0), Y(R)), (X(C), Y(0), X(C), Y(R - 1))]
    for r in range(R):
        for c in range(C):
            if c + 1 < C and frozenset(((r, c), (r, c + 1))) not in edges:
                segs.append((X(c + 1), Y(r), X(c + 1), Y(r + 1)))
            if r + 1 < R and frozenset(((r, c), (r + 1, c))) not in edges:
                segs.append((X(c), Y(r + 1), X(c + 1), Y(r + 1)))
    d = " ".join(f"M {a:.1f},{b:.1f} L {c_:.1f},{e:.1f}" for a, b, c_, e in segs)
    a = cell * 0.45
    ey, xy = Y(0) + cell / 2, Y(R - 1) + cell / 2
    arrows = (f'<path d="M {X(0) - a*1.6:.1f},{ey - a/2:.1f} L {X(0) - a*0.5:.1f},{ey:.1f} L {X(0) - a*1.6:.1f},{ey + a/2:.1f} Z" '
              f'style="fill:{color}" inkscape:label="Entrance arrow"/>'
              f'<path d="M {X(C) + a*0.5:.1f},{xy - a/2:.1f} L {X(C) + a*1.6:.1f},{xy:.1f} L {X(C) + a*0.5:.1f},{xy + a/2:.1f} Z" '
              f'style="fill:{color}" inkscape:label="Exit arrow"/>')
    sol = ""
    if solution:
        pts = [(X(0) - cell * .4, ey)] + [(X(c) + cell / 2, Y(r) + cell / 2) for r, c in m["path"]] + [(X(C) + cell * .4, xy)]
        sol = (f'<path d="M ' + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f'" style="fill:none;stroke:{sol_color};'
               f'stroke-width:{cell*.3:.1f};stroke-linecap:round;stroke-linejoin:round;stroke-opacity:.8" inkscape:label="Solution"/>')
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="{W:.1f}px" height="{H:.1f}px" '
            f'viewBox="0 0 {W:.1f} {H:.1f}">\n  <title>Maze {C}x{R}</title>\n  {sol}\n'
            f'  <path d="{d}" style="fill:none;stroke:{color};stroke-width:{stroke};stroke-linecap:square" inkscape:label="Walls"/>\n'
            f'  {arrows}\n</svg>\n')


def route_analysis(m, edges):
    adj = {p: [] for p in m['cells']}
    for e in edges:
        a, b = tuple(e); adj[a].append(b); adj[b].append(a)
    path = m['path']; on = set(path)
    room = set()
    depths, junction = [], []
    for p in path:
        k = 0
        for q in adj[p]:
            if q in on or q in room: continue
            k += 1
            st, deep, seen = [(q, 1)], 0, {p} | on | room
            while st:
                x, d = st.pop()
                if x in seen: continue
                seen.add(x); deep = max(deep, d); st += [(y, d + 1) for y in adj[x] if y not in seen]
            depths.append(deep)
        junction.append(k > 0 or p in room)
    runs, cur = [], 0
    for j in junction:
        if j: runs.append(cur); cur = 0
        else: cur += 1
    runs.append(cur)
    return depths, runs


def main():
    ap = argparse.ArgumentParser(description="Generate the booklet's rectangular maze (SVG).")
    ap.add_argument("--seed", type=int, default=648, help="change for a different maze")
    ap.add_argument("--rows", type=int, default=23)
    ap.add_argument("--cols", type=int, default=20)
    ap.add_argument("--cell", type=float, default=None, help="cell size in px (default: whole image 960 px)")
    ap.add_argument("--stroke", type=float, default=None, help="line width in px (default: scales with cell)")
    ap.add_argument("--color", default="#000000")
    ap.add_argument("--report", action="store_true", help="only print how tricky the maze is")
    ap.add_argument("--out", default=str(HERE / "output" / "maze.svg"))
    a = ap.parse_args()
    m = kruskal_maze(a.seed, a.rows, a.cols)
    d, runs = route_analysis(m, m["edges"])
    info = (f"{a.cols}x{a.rows} maze, seed {a.seed}: route {len(m['path'])}, {len(d)} openings along it, "
            f"longest stretch without one {max(runs)}")
    if a.report:
        print(info); return
    cell = a.cell or 960 / (max(a.rows, a.cols) + 3)
    stroke = a.stroke or max(2.0, cell / 8)
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg_grid(m, cell, stroke, a.color, cell * 1.5), encoding="utf-8")
    sol = out.with_name(out.stem + "-solution.svg")
    sol.write_text(svg_grid(m, cell, stroke, a.color, cell * 1.5, solution=True), encoding="utf-8")
    print(f"Wrote {out} and {sol}: {info}")


if __name__ == "__main__":
    main()
