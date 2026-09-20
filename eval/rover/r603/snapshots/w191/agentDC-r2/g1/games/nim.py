import sys


def solve(text: str) -> str:
    tokens = text.split()
    it = iter(tokens)
    m = int(next(it))
    piles = [int(next(it)) for _ in range(m)]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return "LOSE"
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            return "WIN " + str(i + 1) + " " + str(piles[i] - target)
    return "LOSE"


if __name__ == "__main__":
    sys.stdout.write(solve(sys.stdin.read()))
