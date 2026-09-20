def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    g = [list(lines[1 + i][:w].ljust(w, '.')) for i in range(h)]
    for _ in range(k):
        n = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and g[rr][cc] == '#':
                            cnt += 1
                if g[r][c] == '#':
                    n[r][c] = '#' if cnt in (2, 3) else '.'
                else:
                    n[r][c] = '#' if cnt == 3 else '.'
        g = n
    return '\n'.join(''.join(row) for row in g)
