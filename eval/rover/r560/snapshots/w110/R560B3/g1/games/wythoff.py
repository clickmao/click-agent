def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    # 必胜手：枚举 (i, j)，i,j >= 0，不同时为 0，且是合法着法
    # 合法着法：(i>0 and j==0) or (i==0 and j>0) or (i==j>0)
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            legal = (i > 0 and j == 0) or (i == 0 and j > 0) or (i == j and i > 0)
            if not legal:
                continue
            na, nb = a - i, b - j
            if _is_losing(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best


def _is_losing(a: int, b: int) -> bool:
    # Wythoff 必败点：(floor(n*phi), floor(n*phi^2)) 及其交换
    if a > b:
        a, b = b, a
    if a == 0 and b == 0:
        return True
    # 用递推够小范围直接枚举
    seen = set()
    n = 0
    while True:
        x = (n * 1618033988749894848204586834365638117720309179805762862135448622705260462818902449707207204189391137484754088075386891752126633862223536931793180060766726354433) // 1000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
        y = x + n
        if x > a or y > b:
            break
        if (x == a and y == b) or (x == b and y == a):
            return True
        n += 1
    return False
