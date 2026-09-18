from math import isqrt


def solve(text: str) -> str:
    a, b = map(int, text.split())
    L = max(a, b)
    los = {(0, 0)}
    for n in range(1, 2 * L + 3):
        x = n + (isqrt(5 * n * n) - n) // 2
        y = x + n
        if x > 2 * L + 2 or y > 2 * L + 2:
            break
        los.add((x, y))
        los.add((y, x))
    if (a, b) in los:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (a - i, b - j) in los:
                return f'WIN {i} {j}'
    return 'LOSE'
