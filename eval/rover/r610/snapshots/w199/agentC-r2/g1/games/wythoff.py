"""Wythoff game: lexicographically minimal winning move."""


def _lose_table(limit: int):
    is_lose = [[False] * (limit + 1) for _ in range(limit + 1)]
    for a in range(limit + 1):
        for b in range(limit + 1):
            # (a, b) is a losing position for the player to move
            # iff every reachable position is a winning position.
            ok = False
            # move (i): take from pile 1 only: (a - t, b), t >= 1
            for t in range(1, a + 1):
                if is_lose[a - t][b]:
                    ok = True
                    break
            if not ok:
                # move (i): take from pile 2 only: (a, b - t), t >= 1
                for t in range(1, b + 1):
                    if is_lose[a][b - t]:
                        ok = True
                        break
            if not ok:
                # move (ii): take same amount from both piles
                for t in range(1, min(a, b) + 1):
                    if is_lose[a - t][b - t]:
                        ok = True
                        break
            is_lose[a][b] = not ok
    return is_lose


_LIMIT = 25
_IS_LOSE = _lose_table(_LIMIT)


def solve(text: str) -> str:
    toks = text.split()
    a = int(toks[0])
    b = int(toks[1])

    if _IS_LOSE[a][b]:
        return 'LOSE'

    n = max(a, b)
    cands = []
    for a2 in range(0, n + 1):
        for b2 in range(0, n + 1):
            if a2 == a and b2 == b:
                continue
            i = a - a2
            j = b - b2
            if i < 0 or j < 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue  # not a legal single move
            if i == 0 and j == 0:
                continue
            cands.append((i, j))
    cands.sort()
    for i, j in cands:
        if _IS_LOSE[a - i][b - j]:
            return 'WIN %d %d' % (i, j)
    return 'LOSE'
