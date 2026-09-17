"""Conway's Game of Life: H-generation synchronous evolution.

Input text format:
    line 1: H W k
    next H lines: W chars of '.' (dead) / '#' (alive)

solve(text) -> grid after k generations, H lines x W chars, no trailing newline.
"""


def _step(grid, H, W):
    """One synchronous generation; cells outside the finite grid are dead."""
    out = []
    for r in range(H):
        row = []
        for c in range(W):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr = r + dr
                    cc = c + dc
                    if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] == '#':
                        n += 1
            if grid[r][c] == '#':
                row.append('#' if n in (2, 3) else '.')
            else:
                row.append('#' if n == 3 else '.')
        out.append(''.join(row))
    return out


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    H, W, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = []
    for _ in range(H):
        row = lines[idx] if idx < len(lines) else ''
        idx += 1
        grid.append(row.ljust(W, '.')[:W])
    for _ in range(k):
        grid = _step(grid, H, W)
    return '\n'.join(grid)


if __name__ == '__main__':
    import sys
    sys.stdout.write(solve(sys.stdin.read()))
