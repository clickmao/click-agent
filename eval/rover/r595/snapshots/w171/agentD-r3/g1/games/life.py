"""Conway's Game of Life: evolve H x W grid k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split()[:3])
    rows = [lines[idx + 1 + i].ljust(w, ".")[:w] for i in range(h)]

    grid = [[1 if ch == "#" else 0 for ch in row] for row in rows]
    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w:
                            n += grid[rr][cc]
                if grid[r][c] == 1:
                    nxt[r][c] = 1 if n in (2, 3) else 0
                else:
                    nxt[r][c] = 1 if n == 3 else 0
        grid = nxt

    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
