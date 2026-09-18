"""Conway's Game of Life: evolve a grid H generations."""


def solve(text: str) -> str:
    data = text.split()
    pos = 0
    h = int(data[pos]); w = int(data[pos + 1]); k = int(data[pos + 2])
    pos += 3
    rows = [list(data[pos + i]) for i in range(h)]

    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and rows[rr][cc] == '#':
                            cnt += 1
                if rows[r][c] == '#':
                    nxt[r][c] = '#' if cnt == 2 or cnt == 3 else '.'
                else:
                    nxt[r][c] = '#' if cnt == 3 else '.'
        rows = nxt

    return '\n'.join(''.join(row) for row in rows)
