"""Wythoff game: decide LOSE or lexicographically smallest winning move."""


def _is_losing(a, b, memo):
    if a > b:
        a, b = b, a
    if (a, b) in memo:
        return memo[(a, b)]
    losing = True
    # (i) take from one heap
    for i in range(1, a + 1):
        if _is_losing(a - i, b, memo):
            losing = False
            break
    if losing:
        for j in range(1, b + 1):
            if _is_losing(a, b - j, memo):
                losing = False
                break
    # (ii) take the same positive number from both heaps
    if losing:
        for t in range(1, a + 1):
            if _is_losing(a - t, b - t, memo):
                losing = False
                break
    memo[(a, b)] = losing
    return losing


def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])
    memo = {}

    if _is_losing(a, b, memo):
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        maxj = b if i == 0 else b - i
        for j in range(0, maxj + 1):
            if i == 0 and j == 0:
                continue
            if i == 0:
                na, nb = a, b - j
            elif j <= b - i:
                na, nb = a - i, b - j
            else:
                continue
            if _is_losing(na, nb, memo):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
