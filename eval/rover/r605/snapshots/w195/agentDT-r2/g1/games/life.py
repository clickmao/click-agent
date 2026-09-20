"""Conway's Game of Life: k generations.

Input layout (whole stdin text):
    H W k
    H lines of W chars from {'.', '#'}
Output: grid after k generations, no trailing newline.
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    if not lines or not lines[0].strip():
        return ''
    h, w, k = map(int, lines[0].split()[:3])
    grid = [list(lines[1 + r].strip()) for r in range(h)]
    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                            cnt += 1
                if grid[r][c] == '#':
                    nxt[r][c] = '#' if cnt in (2, 3) else '.'
                else:
                    nxt[r][c] = '#' if cnt == 3 else '.'
        grid = nxt
    return '\n'.join(''.join(row) for row in grid)
