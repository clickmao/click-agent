def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _is_losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"


_PHI = (1 + 5 ** 0.5) / 2


def _is_losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    diff = b - a
    for k in range(0, diff + 2):
        if int(k * _PHI) == a and int(k * _PHI) + k == b:
            return True
    return False
