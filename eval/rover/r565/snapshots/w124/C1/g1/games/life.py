from typing import List


def solve(text: str) -> str:
    data = text.split()
    idx = 0
    H = int(data[idx]); idx += 1
    W = int(data[idx]); idx += 1
    k = int(data[idx]); idx += 1
    grid: List[List[str]] = []
    for _ in range(H):
        row = data[idx]; idx += 1
        grid.append(list(row[:W]))

    for _ in range(k):
        new: List[List[str]] = []
        for y in range(H):
            line = []
            for x in range(W):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and grid[ny][nx] == '#':
                            cnt += 1
                alive = grid[y][x] == '#'
                if alive:
                    line.append('#' if cnt in (2, 3) else '.')
                else:
                    line.append('#' if cnt == 3 else '.')
            new.append(line)
        grid = new

    return '\n'.join(''.join(row) for row in grid)
