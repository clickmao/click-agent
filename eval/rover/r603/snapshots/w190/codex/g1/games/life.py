def solve(text: str) -> str:
    lines = text.split('\n')
    H, W, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + r].strip()[:W].ljust(W, '.')) for r in range(H)]
    for _ in range(k):
        new = [['.'] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < H and 0 <= nc < W and grid[nr][nc] == '#':
                            cnt += 1
                if grid[r][c] == '#':
                    new[r][c] = '#' if cnt in (2, 3) else '.'
                else:
                    new[r][c] = '#' if cnt == 3 else '.'
        grid = new
    return '\n'.join(''.join(row) for row in grid)


if __name__ == '__main__':
    import sys
    sys.stdout.write(solve(sys.stdin.read()))
