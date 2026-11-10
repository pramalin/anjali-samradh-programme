#!/usr/bin/env python3
"""
Generate an original square maze as SVG (black lines, transparent background),
plus a solution version.

    python3 maze.py                         # 21x21, seed 1511 -> output/maze.svg, output/maze-solution.svg
    python3 maze.py --size 25 --seed 7      # bigger / different maze
    python3 maze.py --color "#59362A"       # line colour (e.g. the booklet's brown)
    python3 maze.py --size 27 --hardest 300 # try 300 mazes, keep the trickiest (see below)
    python3 maze.py --size 27 --seed 1964 --branchy 0.95 --color "#3a2c24"   # the booklet's maze
    python3 maze.py --size 27 --seed 1964 --branchy 0.95 --report            # how tricky is it?
    python3 maze.py --story --size 25 --seed 409 --color "#3a2c24" --stroke 4   # the booklet + web maze (no icons)
    python3 maze.py --story --icons --size 25 --seed 37 --color "#3a2c24" --stroke 4   # same style with the story icons
    python3 maze.py --cat --size 25 --seed 1027 --color "#3a2c24" --stroke 4    # a cat hidden in the walls (not used now)

--branchy P carves with a "growing tree" (P = how often it keeps extending the newest corridor;
1.0 is the old long-corridor style). It branches more, so wrong turns lead somewhere.
--hardest N keeps the maze whose wrong turns off the solution go deepest: a wrong turn that is
a 2-cell stub is obvious; one that runs 15 cells before dead-ending is a real decoy.

Every maze has exactly one path from the entrance arrow (top left) to the exit
arrow (bottom right). Convert to PNG with Inkscape:
    inkscape output/maze.svg --export-type=png --export-dpi=192 --export-background-opacity=0
"""
import argparse
import math
from collections import deque
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


def carve_branchy(n, seed, newest=0.95):
    """Growing-tree maze: mostly extends the newest corridor (winding), sometimes restarts from an
    older cell (side branches that run a long way before dead-ending)."""
    rng = random.Random(seed)
    right = [[True] * n for _ in range(n)]
    down = [[True] * n for _ in range(n)]
    seen = [[False] * n for _ in range(n)]
    active = [(rng.randrange(n), rng.randrange(n))]
    seen[active[0][0]][active[0][1]] = True
    while active:
        i = len(active) - 1 if rng.random() < newest else rng.randrange(len(active))
        r, c = active[i]
        nbrs = [(r + dr, c + dc, dr, dc) for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0))
                if 0 <= r + dr < n and 0 <= c + dc < n and not seen[r + dr][c + dc]]
        if not nbrs:
            active.pop(i)
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
        active.append((nr, nc))
    return right, down


def make(n, seed, branchy=None):
    return carve_branchy(n, seed, branchy) if branchy else carve(n, seed)


def wrong_turns(n, right, down, path):
    """Depth (cells to the furthest dead end) of every wrong turn leading off the solution."""
    nb = {(r, c): [] for r in range(n) for c in range(n)}
    for r in range(n):
        for c in range(n):
            if c + 1 < n and not right[r][c]:
                nb[(r, c)].append((r, c + 1)); nb[(r, c + 1)].append((r, c))
            if r + 1 < n and not down[r][c]:
                nb[(r, c)].append((r + 1, c)); nb[(r + 1, c)].append((r, c))
    on, depths = set(path), []
    for p in path:
        for q in nb[p]:
            if q in on:
                continue
            stack, deepest = [(q, p, 1)], 0
            while stack:
                x, par, d = stack.pop()
                deepest = max(deepest, d)
                stack += [(y, x, d + 1) for y in nb[x] if y != par]
            depths.append(deepest)
    return depths


def trickiness(n, right, down, path):
    """Reward long decoys, penalise obvious stubs; solutions shorter than 3n don't qualify."""
    if len(path) < 3 * n:
        return float("-inf")
    d = wrong_turns(n, right, down, path)
    return 12 * sum(x >= 10 for x in d) + 5 * sum(6 <= x < 10 for x in d) - 4 * sum(x <= 3 for x in d)


def describe(n, right, down, path):
    d = sorted(wrong_turns(n, right, down, path))
    return (f"solution {len(path)} of {n*n} cells; {len(d)} wrong turns off it: "
            f"{sum(x <= 3 for x in d)} end within 3 cells, {sum(4 <= x < 10 for x in d)} go 4-9, "
            f"{sum(x >= 10 for x in d)} go 10+ (median {d[len(d)//2] if d else 0})")


# ---------------------------------------------------------------- square maze with a cat hidden in it
def in_tri(px, py, a, b, c):
    def s(p, q, r): return (p[0] - r[0]) * (q[1] - r[1]) - (q[0] - r[0]) * (p[1] - r[1])
    d1, d2, d3 = s((px, py), a, b), s((px, py), b, c), s((px, py), c, a)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))

def cat_mask(R=31, C=31, scale=1.22):
    """Sitting cat seen from the front: head with two ears, round body, tail curling up on the right."""
    cells = set()
    for r in range(R):
        for c in range(C):
            x, y = (c + .5) / scale, (r + .5) / scale
            head = ((x - 9.5) / 6.3) ** 2 + ((y - 7.6) / 5.0) ** 2 <= 1
            ears = in_tri(x, y, (3.4, 6.6), (4.2, -0.8), (9.4, 3.6)) or in_tri(x, y, (9.6, 3.6), (14.8, -0.8), (15.6, 6.6))
            body = ((x - 10.5) / 7.6) ** 2 + ((y - 17.6) / 7.2) ** 2 <= 1 and y > 10.5
            neck = 6.5 <= x <= 13.5 and 10 <= y <= 13
            # tail: a thick arc from the lower right of the body curling up the right side
            dx, dy = x - 17.4, y - 16.0
            rr, ang = math.hypot(dx, dy), math.degrees(math.atan2(dy, dx))
            tail = 3.7 <= rr <= 5.7 and -100 <= ang <= 118
            tip = math.hypot(x - 17.2, y - 10.6) <= 1.3
            if head or ears or body or neck or tail or tip:
                cells.add((r, c))
    return cells


N4 = ((0, 1), (1, 0), (0, -1), (-1, 0))

def picture(n=25, dr=0, dc=2):
    raw = cat_mask(n, n, n / 25)
    return {(r + dr, c + dc) for r, c in raw if 0 <= r + dr < n and 0 <= c + dc < n}

def components(cells, n):
    comp, out = {}, []
    for p in cells:
        if p in comp: continue
        k = len(out); out.append(set()); st = [p]
        while st:
            x = st.pop()
            if x in comp or x not in cells: continue
            comp[x] = k; out[k].add(x)
            st += [(x[0] + a, x[1] + b) for a, b in N4]
    return out

def bfs_path(adj, a, b):
    prev = {a: None}; q = deque([a])
    while q:
        p = q.popleft()
        if p == b: break
        for x in adj[p]:
            if x not in prev: prev[x] = p; q.append(x)
    out, p = [], b
    while p is not None: out.append(p); p = prev[p]
    return out[::-1]

def grow(region, rng, newest, edges):
    start = rng.choice(sorted(region)); seen = {start}; active = [start]
    while active:
        k = len(active) - 1 if rng.random() < newest else rng.randrange(len(active))
        p = active[k]
        nb = [(p[0] + a, p[1] + b) for a, b in N4 if (p[0] + a, p[1] + b) in region and (p[0] + a, p[1] + b) not in seen]
        if not nb: active.pop(k); continue
        q = rng.choice(nb); edges.add(frozenset((p, q))); seen.add(q); active.append(q)

def cat_picture_maze(seed=1027, n=25, newest=0.9, stops=5, with_cat=True):
    """A square maze with a cat hidden in it: the cat's outline is a wall with one doorway into each outside area,
    so the route from the groom (top left) to the bride (bottom right) must pass through the cat.
    'stops' 2x2 rooms on the route hold the story icons (maze_icons.ORDER)."""
    rng = random.Random(seed)
    cat = picture(n) if with_cat else set()
    allc = {(r, c) for r in range(n) for c in range(n)}
    outs = components(allc - cat, n)
    start, end = (0, 0), (n - 1, n - 1)
    region = {}
    for k, comp in enumerate(outs):
        for p in comp: region[p] = k
    for p in cat: region[p] = 'cat'
    if with_cat and region[start] == region[end]:
        return None                                   # the cat must separate the groom from the bride
    edges = set()
    if cat:
        grow(cat, rng, newest, edges)
    for comp in outs: grow(comp, rng, newest, edges)
    # one doorway from each outside area into the cat
    doors = []
    for comp in (outs if cat else []):
        pairs = [(p, (p[0] + a, p[1] + b)) for p in comp for a, b in N4 if (p[0] + a, p[1] + b) in cat]
        if not pairs: return None
        p, q = rng.choice(sorted(pairs)); edges.add(frozenset((p, q))); doors.append((p, q))
    adj = {p: [] for p in allc}
    for e in edges:
        a, b = tuple(e); adj[a].append(b); adj[b].append(a)
    path = bfs_path(adj, start, end)
    if path[0] != start: return None
    # rooms on the route, each wholly inside one area
    onp = set(path); rooms, blocked, room_edges, L = [], set(), set(), len(path)
    for k in range(stops):
        target = int(L * (k + 0.6) / (stops + 0.2)); best = None
        for j in sorted(range(2, L - 3), key=lambda j: abs(j - target)):
            if abs(j - target) > L / stops / 2.5: break
            a, b = path[j], path[j + 1]
            if region[a] != region[b]: continue
            for side in (1, -1):
                extra = [(a[0] + side, a[1]), (b[0] + side, b[1])] if a[0] == b[0] else [(a[0], a[1] + side), (b[0], b[1] + side)]
                if all(e in allc and e not in onp and e not in blocked and region[e] == region[a] for e in extra):
                    best = (a, b, extra); break
            if best: break
        if not best: return None
        a, b, extra = best; four = [a, b] + extra
        for x in four:
            for y in four:
                if x < y and abs(x[0] - y[0]) + abs(x[1] - y[1]) == 1: room_edges.add(frozenset((x, y)))
        rooms.append((min(x[0] for x in four), min(x[1] for x in four)))
        blocked |= {(r + i, c + j) for r, c in four for i in (-1, 0, 1) for j in (-1, 0, 1)}
    parent = {p: p for p in allc}
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    keep = set(room_edges)
    for e in room_edges:
        a, b = tuple(e); parent[find(a)] = find(b)
    for a, b in zip(path, path[1:]):
        e = frozenset((a, b)); keep.add(e); ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb
    rest = [e for e in edges if e not in keep]; rng.shuffle(rest)
    for e in rest:
        a, b = tuple(e); ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb; keep.add(e)
    # anything cut off rejoins within its own area (never a new gap in the cat's outline)
    cand = [frozenset((p, (p[0] + a, p[1] + b))) for p in allc for a, b in N4
            if (p[0] + a, p[1] + b) in allc and region[(p[0] + a, p[1] + b)] == region[p]]
    rng.shuffle(cand)
    for e in cand:
        a, b = tuple(e); ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb; keep.add(e)
    if len({find(p) for p in allc}) != 1: return None
    return dict(n=n, cells=allc, cat=cat, region=region, edges=keep, start=start, end=end, path=path, rooms=rooms, doors=doors)

def story_maze(seed=409, n=25, newest=1.0, stops=0):
    """The standard square maze (groom top left, bride bottom right) with a long route that wanders across
    the grid, and the rest reshaped into fewer, long dead ends: a wrong turn typically runs 10-20 squares
    before it ends. stops=None puts a 2x2 room with a story icon (maze_icons.ORDER) on the route for each
    icon (seed 37 suits that); stops=0 (the default) has no icons."""
    if stops is None:
        import maze_icons
        stops = len(maze_icons.ORDER)
    m = cat_picture_maze(seed, n, newest, stops, with_cat=False)
    if not m:
        return None
    return improve(m, random.Random(seed), 4000, gap=12, deep="deeper")


def route_analysis(m, edges):
    adj = {p: [] for p in m['cells']}
    for e in edges:
        a, b = tuple(e); adj[a].append(b); adj[b].append(a)
    path = m['path']; on = set(path)
    room = {(r0 + i, c0 + j) for r0, c0 in m['rooms'] for i in (0, 1) for j in (0, 1)}
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

def route_score(m, edges, gap=5, deep=False):
    """Many openings along the route, none of them giveaway stubs, and no long stretch without a choice.
    deep=True favours fewer, deeper wrong turns (for long routes that leave less room for branches)."""
    d, runs = route_analysis(m, edges)
    if deep == "deeper":
        w = sum(-14 if x <= 3 else -6 if x <= 6 else 0 if x <= 9 else 7 if x <= 13 else 12 if x <= 18 else 15 for x in d)
    elif deep:
        w = sum(-10 if x <= 2 else -4 if x == 3 else 1 if x <= 5 else 5 if x <= 8 else 9 for x in d)
    else:
        w = sum(-6 if x <= 2 else -2 if x == 3 else 3 if x <= 6 else 6 if x <= 9 else 9 for x in d)
    return w - 3 * max(runs) - sum(max(0, r - gap) for r in runs), d, runs

def improve(m, rng, iters=2500, **score_opts):
    """Reshape the branches (never the route or the rooms) by moving one dead-end section at a time to
    another wall, keeping changes that score better (simulated annealing)."""
    cells, path = m['cells'], m['path']
    keep = {frozenset(e) for e in zip(path, path[1:])}
    room = {(r0 + i, c0 + j) for r0, c0 in m['rooms'] for i in (0, 1) for j in (0, 1)}
    for x in room:
        for a, b in N4:
            y = (x[0] + a, x[1] + b)
            if y in room: keep.add(frozenset((x, y)))
    edges = set(m['edges'])
    cur, _, _ = route_score(m, edges, **score_opts)
    for it in range(iters):
        movable = [e for e in edges if e not in keep]
        e = rng.choice(movable)
        a, b = tuple(e)
        edges.discard(e)
        # the side cut off from the route
        adj = {}
        for f in edges:
            u, v = tuple(f); adj.setdefault(u, []).append(v); adj.setdefault(v, []).append(u)
        side, st = set(), [path[0]]
        while st:
            x = st.pop()
            if x in side: continue
            side.add(x); st += adj.get(x, [])
        cut = cells - side
        options = [frozenset((x, (x[0] + p, x[1] + q))) for x in cut for p, q in N4
                   if (x[0] + p, x[1] + q) in side and frozenset((x, (x[0] + p, x[1] + q))) != e]
        if not options:
            edges.add(e); continue
        f = rng.choice(options)
        edges.add(f)
        new, _, _ = route_score(m, edges, **score_opts)
        T = max(0.05, 2.0 * (1 - it / iters))
        if new >= cur or rng.random() < pow(2.718, (new - cur) / T):
            cur = new
        else:
            edges.discard(f); edges.add(e)
    out = dict(m); out['edges'] = edges
    return out


def deepen(m, rng, max_short=4, rounds=6):
    cells, edges, region = m['cells'], set(m['edges']), m['region']
    on = set(m['path']); room = {(r0 + i, c0 + j) for r0, c0 in m['rooms'] for i in (0, 1) for j in (0, 1)}
    for _ in range(rounds):
        changed = False
        adj = {p: set() for p in cells}
        for e in edges:
            a, b = tuple(e); adj[a].add(b); adj[b].add(a)
        for p in m['path']:
            for q in list(adj[p]):
                if q in on or q in room or region[q] != region[p]: continue
                stub, st, deep = set(), [(q, 1)], 0
                while st:
                    x, d = st.pop()
                    if x in stub or x == p: continue
                    stub.add(x); deep = max(deep, d); st += [(y, d + 1) for y in adj[x] if y not in stub and y != p]
                if deep > max_short: continue
                opts = [(x, y) for x in stub for a, b in N4 for y in [(x[0] + a, x[1] + b)]
                        if y in cells and y not in stub and y not in on and y not in room and y not in adj[x] and region[y] == region[x]]
                if not opts: continue
                x, y = rng.choice(opts)
                edges.discard(frozenset((p, q))); edges.add(frozenset((x, y)))
                adj[p].discard(q); adj[q].discard(p); adj[x].add(y); adj[y].add(x); changed = True
        if not changed: break
    m = dict(m); m['edges'] = edges
    return m

def cat_wrong_turns(m):
    adj = {p: [] for p in m['cells']}
    for e in m['edges']:
        a, b = tuple(e); adj[a].append(b); adj[b].append(a)
    on = set(m['path']); room = {(r0 + i, c0 + j) for r0, c0 in m['rooms'] for i in (0, 1) for j in (0, 1)}
    out = []
    for p in m['path']:
        for q in adj[p]:
            if q in on or q in room: continue
            st, deep, seen = [(q, 1)], 0, {p} | on | room
            while st:
                x, d = st.pop()
                if x in seen: continue
                seen.add(x); deep = max(deep, d); st += [(y, d + 1) for y in adj[x] if y not in seen]
            out.append(deep)
    return out


def svg_picture(m, cell, stroke, color, icon_color, margin, solution=False, sol_color="#C05C27", outline_k=1.8,
                shade="#d9c2a0", shade_opacity=0.45):
    n, edges, cat = m['n'], m['edges'], m['cat']
    W = n * cell + 2 * margin
    X = lambda c: margin + c * cell; Y = lambda r: margin + r * cell
    thin, thick = [], []
    def wall(a, b, seg):
        (thick if ((a in cat) != (b in cat)) else thin).append(seg)
    for r in range(n):
        for c in range(n):
            if c + 1 < n and frozenset(((r, c), (r, c + 1))) not in edges:
                wall((r, c), (r, c + 1), (X(c + 1), Y(r), X(c + 1), Y(r + 1)))
            if r + 1 < n and frozenset(((r, c), (r + 1, c))) not in edges:
                wall((r, c), (r + 1, c), (X(c), Y(r + 1), X(c + 1), Y(r + 1)))
    # outer border with the classic openings: left of the top-left square, right of the bottom-right square
    for c in range(n):
        (thick if (0, c) in cat else thin).append((X(c), Y(0), X(c + 1), Y(0)))
        (thick if (n - 1, c) in cat else thin).append((X(c), Y(n), X(c + 1), Y(n)))
    for r in range(n):
        if r != 0: (thick if (r, 0) in cat else thin).append((X(0), Y(r), X(0), Y(r + 1)))
        if r != n - 1: (thick if (r, n - 1) in cat else thin).append((X(n), Y(r), X(n), Y(r + 1)))
    d = lambda segs: " ".join(f"M {a:.1f},{b:.1f} L {c_:.1f},{e:.1f}" for a, b, c_, e in segs)
    a = cell * 0.45; ey = Y(0) + cell / 2; xy = Y(n - 1) + cell / 2
    arrows = (f'<path d="M {X(0) - a*1.6:.1f},{ey - a/2:.1f} L {X(0) - a*0.5:.1f},{ey:.1f} L {X(0) - a*1.6:.1f},{ey + a/2:.1f} Z" '
              f'style="fill:{color}" inkscape:label="Entrance arrow"/>'
              f'<path d="M {X(n) + a*0.5:.1f},{xy - a/2:.1f} L {X(n) + a*1.6:.1f},{xy:.1f} L {X(n) + a*0.5:.1f},{xy + a/2:.1f} Z" '
              f'style="fill:{color}" inkscape:label="Exit arrow"/>')
    import maze_icons
    icons = "".join(maze_icons.svg_group(nm, X(c0) + cell * .12, Y(r0) + cell * .12, cell * 1.76, icon_color)
                    for nm, (r0, c0) in zip(maze_icons.ORDER, m['rooms']))
    tint = "".join(f"M{X(c):.1f},{Y(r):.1f}h{cell:.1f}v{cell:.1f}h{-cell:.1f}Z" for r, c in sorted(cat))
    sol = ""
    if solution:
        pts = [(X(0) - cell * .4, ey)] + [(X(c) + cell / 2, Y(r) + cell / 2) for r, c in m['path']] + [(X(n) + cell * .4, xy)]
        sol = (f'<path d="M ' + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f'" style="fill:none;stroke:{sol_color};'
               f'stroke-width:{cell*.3:.1f};stroke-linecap:round;stroke-linejoin:round;stroke-opacity:.8" inkscape:label="Solution"/>')
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="{W:.1f}px" height="{W:.1f}px" '
            f'viewBox="0 0 {W:.1f} {W:.1f}">\n  <title>Maze with a hidden cat</title>\n'
            f'  <path d="{tint}" style="fill:{shade};fill-opacity:{shade_opacity};stroke:none" inkscape:label="Cat shading"/>\n  {sol}\n  <g inkscape:label="Stops">{icons}</g>\n'
            f'  <path d="{d(thin)}" style="fill:none;stroke:{color};stroke-width:{stroke};stroke-linecap:square" inkscape:label="Walls"/>\n'
            f'  <path d="{d(thick)}" style="fill:none;stroke:{color};stroke-width:{stroke * outline_k:.2f};stroke-linecap:square" '
            f'inkscape:label="Walls (cat outline)"/>\n  {arrows}\n</svg>\n')


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


def cat_main(a):
    best = None
    for seed in range(a.seed, a.seed + max(1, a.hardest)):
        if a.story:
            m = story_maze(seed, a.size, a.branchy or 1.0, None if a.icons else 0)
        else:
            m = cat_picture_maze(seed, a.size, a.branchy or 0.9)
            m = deepen(m, random.Random(seed)) if m else None
        if not m:
            continue
        d = cat_wrong_turns(m)
        score = 12 * sum(x >= 10 for x in d) + 5 * sum(6 <= x < 10 for x in d) - 6 * sum(x <= 3 for x in d) + len(m["path"]) // 4
        if best is None or score > best[0]:
            best = (score, seed, m, d)
    if best is None:
        sys.exit("no maze found - try other seeds")
    _, seed, m, d = best
    d = sorted(d)
    if a.story:
        d, runs = route_analysis(m, m["edges"])
    info = (f"{a.size}x{a.size} {'story' if a.story else 'hidden-cat'} maze, seed {seed}: route {len(m['path'])}; {len(d)} wrong turns off it: "
            f"{sum(x <= 3 for x in d)} end within 3, {sum(4 <= x < 10 for x in d)} go 4-9, {sum(x >= 10 for x in d)} go 10+"
            + (f"; longest stretch without an opening {max(runs)}" if a.story else ""))
    if a.report:
        print(info); return
    cell = a.cell or 960 / (a.size + 3)
    stroke = a.stroke or max(2.0, cell / 8)
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg_picture(m, cell, stroke, a.color, a.icon_color, cell * 1.5), encoding="utf-8")
    sol = out.with_name(out.stem + "-solution.svg")
    sol.write_text(svg_picture(m, cell, stroke, a.color, a.icon_color, cell * 1.5, solution=True), encoding="utf-8")
    print(f"Wrote {out} and {sol}: {info}")


def main():
    ap = argparse.ArgumentParser(description="Generate an original square maze (SVG).")
    ap.add_argument("--size", type=int, default=21, help="cells per side (default 21)")
    ap.add_argument("--seed", type=int, default=1511, help="change for a different maze")
    ap.add_argument("--cell", type=float, default=None, help="cell size in px (default: whole image 960 px)")
    ap.add_argument("--stroke", type=float, default=None, help="line width in px (default: scales with cell)")
    ap.add_argument("--hardest", type=int, default=0, metavar="N",
                    help="try N seeds starting at --seed and keep the trickiest maze")
    ap.add_argument("--branchy", type=float, default=None, metavar="P",
                    help="growing-tree carving, P = 0.5..1 (e.g. 0.95); omit for the long-corridor style")
    ap.add_argument("--report", action="store_true", help="only print how tricky the maze is")
    ap.add_argument("--story", action="store_true",
                    help="standard maze with the story icons on the true route (uses --size, --seed)")
    ap.add_argument("--cat", action="store_true",
                    help="square maze with a cat hidden in it, 5 story icons on the true route (uses --size, --seed)")
    ap.add_argument("--icon-color", default="#b5651d")
    ap.add_argument("--icons", action="store_true", help="with --story: put the story icons on the route")
    ap.add_argument("--color", default="#000000")
    ap.add_argument("--out", default=str(HERE / "output" / "maze.svg"))
    a = ap.parse_args()
    if a.size < 3:
        sys.exit("size must be at least 3")
    if a.cat or a.story:
        return cat_main(a)
    best = None
    for seed in range(a.seed, a.seed + max(1, a.hardest)):
        right, down = make(a.size, seed, a.branchy)
        path = solve(a.size, right, down)
        score = trickiness(a.size, right, down, path) if a.hardest else 0
        if best is None or score > best[0]:
            best = (score, seed, right, down, path)
    _, seed, right, down, path = best
    if a.report:
        print(f"{a.size}x{a.size}, seed {seed}: {describe(a.size, right, down, path)}")
        return
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
    print(f"Wrote {out} and {sol} ({a.size}x{a.size}, seed {seed}): {describe(a.size, right, down, path)}")


if __name__ == "__main__":
    main()
