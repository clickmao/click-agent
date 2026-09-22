_LIM = 30
_TABLE = {}


def _build():
    for a in range(_LIM + 1):
        for b in range(_LIM + 1):
            if a == 0 and b == 0:
                _TABLE[(a, b)] = None
                continue
            if a == 0 and b == 0:
                continue
            best = None
            # take i>0 from pile 1 only
            for i in range(1, a + 1):
                st = _TABLE.get((a - i, b))
                if st is None:
                    cand = (i, 0)
                    if best is None or cand < best:
                        best = cand
                    break
            # take j>0 from pile 2 only
            for j in range(1, b + 1):
                st = _TABLE.get((a, b - j))
                if st is None:
                    cand = (0, j)
                    if best is None or cand < best:
                        best = cand
                    break
            # take t>0 from both
            for t in range(1, min(a, b) + 1):
                st = _TABLE.get((a - t, b - t))
                if st is None:
                    cand = (t, t)
                    if best is None or cand < best:
                        best = cand
                    break
            _TABLE[(a, b)] = best


_build()


def solve(text: str) -> str:
    line = text.strip().split('\n')[0]
    a, b = map(int, line.split())
    move = _TABLE.get((a, b))
    if move is None:
        return 'LOSE'
    return 'WIN ' + str(move[0]) + ' ' + str(move[1])
