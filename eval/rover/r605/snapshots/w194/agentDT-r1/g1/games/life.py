def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    grid = []
    for i in range(h):
        row = lines[idx + 1 + i]
        grid.append(row[:w])

    def step(g):
        ng = []
        for r in range(h):
            out = []
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and g[rr][cc] == "#":
                            cnt += 1
                if g[r][c] == "#":
                    out.append("#" if cnt == 2 or cnt == 3 else ".")
                else:
                    out.append("#" if cnt == 3 else ".")
            ng.append("".join(out))
        return ng

    for _ in range(k):
        grid = step(grid)
    return "\n".join(grid)
