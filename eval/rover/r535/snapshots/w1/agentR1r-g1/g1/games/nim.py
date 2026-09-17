def solve(text: str) -> str:
    lines = [l for l in text.split("\n") if l.strip()]
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    x = 0
    for v in piles:
        x ^= v
    if x == 0:
        return "LOSE"
    for idx, v in enumerate(piles):
        target = v ^ x
        if target < v:
            return "WIN " + str(idx + 1) + " " + str(v - target)
    return "LOSE"
