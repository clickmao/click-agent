"""Conway's Game of Life: evolve the grid k generations."""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx >= len(lines):
        return ""
    h, w, k = (int(x) for x in lines[idx].split()[:3])
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx] if idx < len(lines) else ""
        idx += 1
        row = (row + "." * w)[:w]
        grid.append([1 if c == "#" else 0 for c in row])

    cur = grid
    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                nb = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and cur[rr][cc]:
                            nb += 1
                if cur[r][c]:
                    nxt[r][c] = 1 if nb in (2, 3) else 0
                else:
                    nxt[r][c] = 1 if nb == 3 else 0
        cur = nxt

    return "\n".join("".join("#" if v else "." for v in row) for row in cur)
