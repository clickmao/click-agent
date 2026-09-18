def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    board = [[c == '#' for c in lines[1 + r][:w]] for r in range(h)]
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and board[rr][cc]:
                            cnt += 1
                alive = board[r][c]
                if alive:
                    nxt[r][c] = cnt == 2 or cnt == 3
                else:
                    nxt[r][c] = cnt == 3
        board = nxt
    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in board)
