def solve(text: str) -> str:
    lines = text.split()
    if not lines:
        return "LOSE"
    m = int(lines[0])
    piles = [int(x) for x in lines[1:1 + m]]

    x = 0
    for a in piles:
        x ^= a

    if x == 0:
        return "LOSE"

    best_p = None
    best_r = None
    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            best_p = idx + 1
            best_r = a - target
            break

    return "WIN " + str(best_p) + " " + str(best_r)
