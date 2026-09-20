"""Wythoff's game: a b."""
import sys


def solve(text: str) -> str:
    nums = [int(x) for x in text.split()]
    a, b = nums[0], nums[1]
    start = (a, b)
    seen = {}
    stack = [start]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        x, y = cur
        dead = True
        for i in range(0, x + 1):
            if (x - i, y) in seen:
                dead = False
                break
        if dead:
            for j in range(0, y + 1):
                if (x, y - j) in seen:
                    dead = False
                    break
        if dead:
            for t in range(1, min(x, y) + 1):
                if (x - t, y - t) in seen:
                    dead = False
                    break
        seen[cur] = dead
        if dead:
            continue
        for i in range(0, x + 1):
            stack.append((x - i, y))
        for j in range(0, y + 1):
            stack.append((x, y - j))
        for t in range(1, min(x, y) + 1):
            stack.append((x - t, y - t))
    # recompute properly with DP over positions sorted by total
    lose = {}
    moves = []
    for x in range(0, a + 1):
        for y in range(0, b + 1):
            moves.append((x, y))
    moves.sort(key=lambda p: (p[0] + p[1], p[0], p[1]))
    for (x, y) in moves:
        is_win = False
        for i in range(1, x + 1):
            if (x - i, y) in lose and lose[(x - i, y)]:
                is_win = True
                break
        if not is_win:
            for j in range(1, y + 1):
                if (x, y - j) in lose and lose[(x, y - j)]:
                    is_win = True
                    break
        if not is_win:
            for t in range(1, min(x, y) + 1):
                if (x - t, y - t) in lose and lose[(x - t, y - t)]:
                    is_win = True
                    break
        lose[(x, y)] = not is_win
    if lose[(a, b)]:
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        if lose.get((a - i, b)) and not (a - i == a and b == b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    for j in range(0, b + 1):
        if lose.get((a, b - j)) and not (a == a and b - j == b):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    for t in range(1, min(a, b) + 1):
        if lose.get((a - t, b - t)):
            cand = (t, t)
            if best is None or cand < best:
                best = cand
    return "WIN %d %d" % (best[0], best[1])
