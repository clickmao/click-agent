"""Conway's Game of Life.

stdin format:
    H W k
    H lines of W chars in {'.', '#'}
Output: grid after k generations, H lines of W chars.
"""


def _step(cells, h, w):
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and cells[rr][cc]:
                        n += 1
            if cells[r][c]:
                out[r][c] = 1 if (n == 2 or n == 3) else 0
            else:
                out[r][c] = 1 if n == 3 else 0
    return out


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split())
    cells = [[1 if ch == "#" else 0 for ch in lines[1 + r]] for r in range(h)]
    for _ in range(k):
        cells = _step(cells, h, w)
    return "\n".join("".join("#" if v else "." for v in row) for row in cells)
