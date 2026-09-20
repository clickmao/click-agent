import sys


def _read(text):
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    return lines


def solve(text: str) -> str:
    lines = _read(text)
    if not lines:
        return ''
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + r]) for r in range(h)]
    for _ in range(k):
        new = [['.' for _ in range(w)] for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == '#':
                            cnt += 1
                if grid[r][c] == '#':
                    new[r][c] = '#' if cnt in (2, 3) else '.'
                else:
                    new[r][c] = '#' if cnt == 3 else '.'
        grid = new
    return '\n'.join(''.join(row) for row in grid)


def main():
    data = sys.stdin.read()
    sys.stdout.write(solve(data))
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
