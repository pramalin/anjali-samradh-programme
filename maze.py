#!/usr/bin/env python3
"""
Generate an original square maze as SVG (black lines, transparent background),
plus a solution version.

    python3 maze.py                         # 21x21, seed 1511 -> output/maze.svg, output/maze-solution.svg
    python3 maze.py --size 25 --seed 7      # bigger / different maze
    python3 maze.py --color "#59362A"       # line colour (e.g. the booklet's brown)
    python3 maze.py --size 27 --hardest 300 # try 300 mazes, keep the one with the longest solution

Every maze has exactly one path from the entrance arrow (top left) to the exit
arrow (bottom right). Convert to PNG with Inkscape:
    inkscape output/maze.svg --export-type=png --export-dpi=192 --export-background-opacity=0
"""
import argparse
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def carve(n, seed):
    """Randomised depth-first search: long, winding corridors like hand-drawn mazes."""
    rng = random.Random(seed)
    # walls: right[r][c] = wall on the east side of cell (r,c); down[r][c] = wall on the south side
    right = [[True] * n for _ in range(n)]
    down = [[True] * n for _ in range(n)]
    seen = [[False] * n for _ in range(n)]
    stack = [(0, 0)]
    seen[0][0] = True
    while stack:
        r, c = stack[-1]
        nbrs = [(r + dr, c + dc, dr, dc) for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0))
                if 0 <= r + dr < n and 0 <= c + dc < n and not seen[r + dr][c + dc]]
        if not nbrs:
            stack.pop()
            continue
        nr, nc, dr, dc = rng.choice(nbrs)
        if dc == 1:
            right[r][c] = False
        elif dc == -1:
            right[r][nc] = False
        elif dr == 1:
            down[r][c] = False
        else:
            down[nr][c] = False
        seen[nr][nc] = True
        stack.append((nr, nc))
    return right, down


def solve(n, right, down):
    """Breadth-first search from the top-left cell to the bottom-right cell."""
    from collections import deque
    prev = {(0, 0): None}
    q = deque([(0, 0)])
    while q:
        r, c = q.popleft()
        if (r, c) == (n - 1, n - 1):
            break
        moves = []
        if c + 1 < n and not right[r][c]:
            moves.append((r, c + 1))
        if c > 0 and not right[r][c - 1]:
            moves.append((r, c - 1))
        if r + 1 < n and not down[r][c]:
            moves.append((r + 1, c))
        if r > 0 and not down[r - 1][c]:
            moves.append((r - 1, c))
        for m in moves:
            if m not in prev:
                prev[m] = (r, c)
                q.append(m)
    path, cur = [], (n - 1, n - 1)
    while cur:
        path.append(cur)
        cur = prev[cur]
    return path[::-1]


def svg(n, right, down, cell, stroke, color, margin, solution=None, sol_color="#C05C27"):
    size = n * cell + 2 * margin
    x0 = y0 = margin
    segs = []
    # outer border, leaving gaps for entrance (left of top-left cell) and exit (right of bottom-right cell)
    segs.append((x0, y0, x0 + n * cell, y0))                       # top
    segs.append((x0, y0 + n * cell, x0 + n * cell, y0 + n * cell))  # bottom
    segs.append((x0, y0 + cell, x0, y0 + n * cell))                 # left, gap at row 0
    segs.append((x0 + n * cell, y0, x0 + n * cell, y0 + (n - 1) * cell))  # right, gap at last row
    # interior walls, merged into long runs
    for r in range(n):          # vertical walls (east side of cells), merged down each column line
        pass
    for c in range(n - 1):
        start = None
        for r in range(n + 1):
            wall = r < n and right[r][c]
            if wall and start is None:
                start = r
            if not wall and start is not None:
                X = x0 + (c + 1) * cell
                segs.append((X, y0 + start * cell, X, y0 + r * cell))
                start = None
    for r in range(n - 1):
        start = None
        for c in range(n + 1):
            wall = c < n and down[r][c]
            if wall and start is None:
                start = c
            if not wall and start is not None:
                Y = y0 + (r + 1) * cell
                segs.append((x0 + start * cell, Y, x0 + c * cell, Y))
                start = None
    d = " ".join(f"M {a:.1f},{b:.1f} L {c_:.1f},{e:.1f}" for a, b, c_, e in segs)
    a = cell * 0.45  # arrow size
    ey = y0 + cell / 2
    xy = y0 + (n - 0.5) * cell
    arrows = (f'<path d="M {x0 - a*1.6:.1f},{ey - a/2:.1f} L {x0 - a*0.5:.1f},{ey:.1f} L {x0 - a*1.6:.1f},{ey + a/2:.1f} Z" '
              f'style="fill:{color}" inkscape:label="Entrance arrow"/>'
              f'<path d="M {x0 + n*cell + a*0.5:.1f},{xy - a/2:.1f} L {x0 + n*cell + a*1.6:.1f},{xy:.1f} '
              f'L {x0 + n*cell + a*0.5:.1f},{xy + a/2:.1f} Z" style="fill:{color}" inkscape:label="Exit arrow"/>')
    sol = ""
    if solution:
        pts = [(x0 - cell * 0.4, ey)] + [(x0 + (c + .5) * cell, y0 + (r + .5) * cell) for r, c in solution] \
              + [(x0 + n * cell + cell * 0.4, xy)]
        sol = (f'<path d="M ' + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f'" '
               f'style="fill:none;stroke:{sol_color};stroke-width:{cell*0.3:.1f};stroke-linecap:round;'
               f'stroke-linejoin:round;stroke-opacity:0.8" inkscape:label="Solution"/>')
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
            f'width="{size}px" height="{size}px" viewBox="0 0 {size} {size}">\n'
            f'  <title>Maze {n}x{n}</title>\n'
            f'  {sol}\n'
            f'  <path d="{d}" style="fill:none;stroke:{color};stroke-width:{stroke};stroke-linecap:square" '
            f'inkscape:label="Walls"/>\n  {arrows}\n</svg>\n')


def main():
    ap = argparse.ArgumentParser(description="Generate an original square maze (SVG).")
    ap.add_argument("--size", type=int, default=21, help="cells per side (default 21)")
    ap.add_argument("--seed", type=int, default=1511, help="change for a different maze")
    ap.add_argument("--cell", type=float, default=None, help="cell size in px (default: whole image 960 px)")
    ap.add_argument("--stroke", type=float, default=None, help="line width in px (default: scales with cell)")
    ap.add_argument("--hardest", type=int, default=0, metavar="N",
                    help="try N seeds starting at --seed and keep the maze with the longest solution")
    ap.add_argument("--color", default="#000000")
    ap.add_argument("--out", default=str(HERE / "output" / "maze.svg"))
    a = ap.parse_args()
    if a.size < 3:
        sys.exit("size must be at least 3")
    best = None
    for seed in range(a.seed, a.seed + max(1, a.hardest)):
        right, down = carve(a.size, seed)
        path = solve(a.size, right, down)
        turns = sum(1 for i in range(1, len(path) - 1)
                    if (path[i][0] - path[i-1][0], path[i][1] - path[i-1][1]) !=
                       (path[i+1][0] - path[i][0], path[i+1][1] - path[i][1]))
        score = len(path) + turns
        if best is None or score > best[0]:
            best = (score, seed, right, down, path, turns)
    _, seed, right, down, path, turns = best
    if a.cell is None:
        a.cell = 960 / (a.size + 3)   # whole image = 960 px (1920 px PNG at 2x)
    if a.stroke is None:
        a.stroke = max(2.0, a.cell / 8)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    margin = a.cell * 1.5
    out.write_text(svg(a.size, right, down, a.cell, a.stroke, a.color, margin), encoding="utf-8")
    sol = out.with_name(out.stem + "-solution.svg")
    sol.write_text(svg(a.size, right, down, a.cell, a.stroke, a.color, margin, solution=path), encoding="utf-8")
    print(f"Wrote {out} and {sol} ({a.size}x{a.size}, seed {seed}, solution {len(path)} cells, {turns} turns)")


if __name__ == "__main__":
    main()
