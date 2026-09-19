import sys


def solve(text):
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    moves = sorted(map(int, lines[1].split()))
    win = [False] * (n + 1)
    best = [0] * (n + 1)
    for m in range(1, n + 1):
        for take in moves:
            if take <= m and not win[m - take]:
                win[m] = True
                best[m] = take
                break
    if not win[n]:
        return "LOSE"
    return "WIN %d" % best[n]


if __name__ == "__main__":
    sys.stdout.write(solve(sys.stdin.read()))
