def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    h, w, k = map(int, lines[0].split())
    grid = [[c == '#' for c in row] for row in lines[1:1 + h]]
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            n += 1
                if grid[r][c]:
                    nxt[r][c] = n == 2 or n == 3
                else:
                    nxt[r][c] = n == 3
        grid = nxt
    return '\n'.join(''.join('#' if grid[r][c] else '.' for c in range(w)) for r in range(h))
