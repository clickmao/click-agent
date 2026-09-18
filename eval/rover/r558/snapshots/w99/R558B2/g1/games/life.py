"""Conway's Game of Life: k generations, 8-neighbourhood, outside = dead."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    grid = []
    for i in range(1, h + 1):
        row = lines[idx + i]
        if len(row) < w:
            row = row.ljust(w, ".")
        grid.append(list(row[:w]))

    cur = grid
    for _ in range(k):
        nxt = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and cur[rr][cc] == "#":
                            n += 1
                if cur[r][c] == "#":
                    nxt[r][c] = "#" if n in (2, 3) else "."
                else:
                    nxt[r][c] = "#" if n == 3 else "."
        cur = nxt

    return "\n".join("".join(row) for row in cur)
