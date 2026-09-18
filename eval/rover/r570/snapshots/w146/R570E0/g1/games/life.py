def solve(text):
    lines = text.splitlines()
    if not lines:
        return ''
    head = lines[0].split()
    if not head:
        return ''
    h = int(head[0])
    w = int(head[1])
    k = int(head[2]) if len(head) > 2 else 0
    grid = [list(lines[1 + r]) for r in range(h)]
    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                alive = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                            alive += 1
                if grid[r][c] == '#':
                    nxt[r][c] = '#' if alive == 2 or alive == 3 else '.'
                else:
                    nxt[r][c] = '#' if alive == 3 else '.'
        grid = nxt
    return '\n'.join(''.join(row) for row in grid)
