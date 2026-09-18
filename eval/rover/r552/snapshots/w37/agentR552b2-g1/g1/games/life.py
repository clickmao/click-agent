"""Conway 生命游戏: 演化 k 代。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    alive = set()
    for r in range(h):
        row = lines[1 + r]
        for c in range(w):
            if row[c] == '#':
                alive.add((r, c))
    for _ in range(k):
        counts = {}
        for (r, c) in alive:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    p = (r + dr, c + dc)
                    counts[p] = counts.get(p, 0) + 1
        new = set()
        for cell, n in counts.items():
            r, c = cell
            if not (0 <= r < h and 0 <= c < w):
                continue
            if cell in alive:
                if n == 2 or n == 3:
                    new.add(cell)
            else:
                if n == 3:
                    new.add(cell)
        alive = new
    return '\n'.join(''.join('#' if (r, c) in alive else '.' for c in range(w)) for r in range(h))
