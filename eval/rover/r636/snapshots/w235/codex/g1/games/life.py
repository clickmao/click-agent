def solve(text: str) -> str:
    lines = text.split("\n")
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [[1 if c == "#" else 0 for c in lines[1 + i][:w]] for i in range(h)]

    def step(g):
        new = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and g[rr][cc]:
                            n += 1
                if g[r][c]:
                    new[r][c] = 1 if n == 2 or n == 3 else 0
                else:
                    new[r][c] = 1 if n == 3 else 0
        return new

    for _ in range(k):
        grid = step(grid)

    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
