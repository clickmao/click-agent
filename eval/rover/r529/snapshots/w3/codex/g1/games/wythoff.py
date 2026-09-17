def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                if _is_lose(a - i, b - j):
                    return "WIN %d %d" % (i, j)
    return "LOSE"


_LOSE = set()


def _build(limit: int = 30):
    global _LOSE
    if _LOSE:
        return
    memo = {}

    def win(x, y):
        if x > y:
            x, y = y, x
        key = (x, y)
        if key in memo:
            return memo[key]
        res = False
        for i in range(x + 1):
            for j in range(y + 1):
                if i == 0 and j == 0:
                    continue
                if i == 0 or j == 0 or i == j:
                    if not win(x - i, y - j):
                        res = True
                        break
            if res:
                break
        memo[key] = res
        return res

    for x in range(limit + 1):
        for y in range(x, limit + 1):
            if not win(x, y):
                _LOSE.add((x, y))


def _is_lose(x: int, y: int) -> bool:
    _build()
    if x > y:
        x, y = y, x
    return (x, y) in _LOSE
