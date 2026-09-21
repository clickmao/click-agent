def solve(text):
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(t) for t in tokens[1:1 + m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for i in range(m):
        a = piles[i]
        target = a ^ x
        if target < a:
            return "WIN " + str(i + 1) + " " + str(a - target)
    return "LOSE"
