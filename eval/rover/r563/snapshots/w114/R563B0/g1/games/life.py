# Conrad's Game of Life: output the grid after k generations.

def solve(text: str) -> str:
    lines = text.split(chr(10))
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    grid = []
    for i in range(h):
        row = lines[idx + 1 + i]
        grid.append([1 if ch == '#' else 0 for ch in row[:w]])
    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            cnt += 1
                if grid[r][c]:
                    nxt[r][c] = 1 if cnt in (2, 3) else 0
                else:
                    nxt[r][c] = 1 if cnt == 3 else 0
        grid = nxt
    out = []
    for r in range(h):
        out.append(''.join('#' if v else '.' for v in grid[r]))
    return chr(10).join(out)
