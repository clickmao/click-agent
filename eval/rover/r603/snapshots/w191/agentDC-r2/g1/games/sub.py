import sys


def solve(text: str) -> str:
    tokens = text.split()
    it = iter(tokens)
    n = int(next(it))
    k = int(next(it))
    moves = [int(next(it)) for _ in range(k)]
    moves = [m for m in moves if m <= n]
    moves_sorted = sorted(set(moves))
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for m in moves_sorted:
            if m > x:
                break
            if not win[x - m]:
                win[x] = True
                break
    if not win[n]:
        return "LOSE"
    for m in moves_sorted:
        if m <= n and not win[n - m]:
            return "WIN " + str(m)
    return "LOSE"


if __name__ == "__main__":
    sys.stdout.write(solve(sys.stdin.read()))
