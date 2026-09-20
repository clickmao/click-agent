"""Conway's Game of Life: k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return ""
    h, w, k = (int(x) for x in lines[0].split())
    grid = [line[:w] for line in lines[1:1 + h]]
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
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == "#":
                            cnt += 1
                alive = grid[r][c] == "#"
                if alive:
                    row.append("#" if cnt in (2, 3) else ".")
                else:
                    row.append("#" if cnt == 3 else ".")
            nxt.append("".join(row))
        grid = nxt
    return "\n".join(grid)
