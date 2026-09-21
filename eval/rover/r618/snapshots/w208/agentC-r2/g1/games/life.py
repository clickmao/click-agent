def solve(text: str) -> str:
    lines = text.split('\n')
    head = lines[0].split()
    h, w, k = int(head[0]), int(head[1]), int(head[2])
    grid = [[c == '#' for c in lines[1 + r]] for r in range(h)]
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            cnt += 1
                if grid[r][c]:
                    nxt[r][c] = cnt == 2 or cnt == 3
                else:
                    nxt[r][c] = cnt == 3
        grid = nxt
    return '\n'.join(''.join('#' if grid[r][c] else '.' for c in range(w)) for r in range(h))
