def solve(text):
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    a, b = map(int, lines[0].split())
    lim = max(a, b)
    pairs = []
    n = 0
    while True:
        x = (n * (1 + 5 ** 0.5)) / 2.0
        aa = int(x)
        bb = aa + n
        if aa > lim and bb > lim:
            break
        pairs.append((aa, bb))
        n += 1
        if n > lim + 5:
            break
    losing = False
    for aa, bb in pairs:
        if (a == aa and b == bb) or (a == bb and b == aa):
            losing = True
            break
    if losing:
        return "LOSE"
    cands = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)):
                continue
            na, nb = a - i, b - j
            if na > nb:
                na, nb = nb, na
            if (na, nb) in pairs:
                cands.append((i, j))
    cands.sort()
    i, j = cands[0]
    return "WIN %d %d" % (i, j)
