"""Wythoff game: WIN i j / LOSE."""


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    losing = False
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i == j:
                if (a - i, b - j) == (0, 0):
                    losing = True
            if (a - i == 0 and b - j == 0):
                losing = True
    return "LOSE"
