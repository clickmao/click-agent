def solve(text):
    a, b = map(int, text.split())
    if a > b:
        a, b = b, a
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            # same amount from both piles
            if i == j and a - i >= 0 and b - j >= 0:
                rem = sorted((a - i, b - j))
                if is_lose(rem[0], rem[1]):
                    return "WIN %d %d" % (i, j)
            # only one pile touched
            if i == 0 or j == 0:
                rem = sorted((a - i, b - j))
                if is_lose(rem[0], rem[1]):
                    return "WIN %d %d" % (i, j)
    return "LOSE"


def is_lose(a, b):
    # a <= b ; Wythoff losing positions are (floor(n*phi), floor(n*phi^2))
    n = b - a
    return a == (n * 5 ** 0.5 + n) // 2 and b == a + n
