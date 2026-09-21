"""取石子 (subtraction game): WIN m / LOSE。

输入首行: n k
第二行: k 个互不相同的可取数目 s1..sk (含 1)。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = (int(v) for v in lines[0].split())
    moves = [int(v) for v in lines[1].split()]

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    best = None
    for s in moves:
        if s <= n and not win[n - s]:
            if best is None or s < best:
                best = s
    return 'WIN %d' % best
