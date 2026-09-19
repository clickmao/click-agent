import functools


def solve(text: str) -> str:
    lines = text.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    m = int(lines[0].strip())
    piles = [int(x) for x in lines[1].split()]
    v = 0
    for a in piles:
        v ^= a
    if v == 0:
        return "LOSE"

    @functools.lru_cache(maxsize=None)
    def win(state):
        if sum(state) == 0:
            return False
        for i in range(len(state)):
            for take in range(1, state[i] + 1):
                nxt = list(state)
                nxt[i] -= take
                if not win(tuple(nxt)):
                    return True
        return False

    st = tuple(piles)
    for i in range(m):
        for take in range(1, piles[i] + 1):
            nxt = list(st)
            nxt[i] -= take
            if not win(tuple(nxt)):
                return "WIN %d %d" % (i + 1, take)
    return "LOSE"
