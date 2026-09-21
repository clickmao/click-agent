def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    h = int(first[0])
    w = int(first[1])
    k = int(first[2])
    rows = []
    for i in range(1, 1 + h):
        rows.append(list(lines[i][:w]))
    for _ in range(k):
        nxt = []
        for r in range(h):
            row = []
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
                    row.append('#' if cnt == 2 or cnt == 3 else '.')
                else:
                    row.append('#' if cnt == 3 else '.')
            nxt.append(row)
        rows = nxt
    return '\n'.join(''.join(r) for r in rows)
