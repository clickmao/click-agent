"""Subtraction game: LOSE if the position is losing, else WIN with the
smallest winning first move."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    n, k = int(lines[idx].split()[0]), int(lines[idx].split()[1])
    moves = [int(x) for x in lines[idx + 1].split()]
    moves = [m for m in moves if 1 <= m <= n]

    wins = [False] * (n + 1)
    for pos in range(1, n + 1):
        for m in moves:
            if m <= pos and not wins[pos - m]:
                wins[pos] = True
                break

    if not wins[n]:
        return "LOSE"
    for m in sorted(moves):
        if m <= n and not wins[n - m]:
            return "WIN %d" % m
    return "LOSE"
