"""Multi-pile Nim: last player to take the final stone wins."""


def solve(text: str) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m]

    x = 0
    for p in piles:
        x ^= p

    if x == 0:
        return "LOSE"

    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            take = piles[idx] - target
            return "WIN %d %d" % (idx + 1, take)
    return "LOSE"
