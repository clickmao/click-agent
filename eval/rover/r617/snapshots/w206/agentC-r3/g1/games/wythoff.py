def solve(text: str) -> str:
    nums = text.split()
    if len(nums) < 2:
        nums = (nums + ["0", "0"])[:2]
    a, b = int(nums[0]), int(nums[1])

    # 必败态: (floor(j*phi), floor(j*phi^2)) j>=0, 即差为 j
    phi = (1 + 5 ** 0.5) / 2
    cold = set()
    j = 0
    while True:
        x = int(j * phi)
        if x > 25 and x + j > 25:
            break
        if x <= 25 and x + j <= 25:
            cold.add((x, x + j))
            cold.add((x + j, x))
        j += 1

    if (a, b) in cold:
        return "LOSE"

    # 枚举全部必胜着法, 取字典序最小
    moves = []
    for i in range(a + 1):
        for jj in range(b + 1):
            if i == 0 and jj == 0:
                continue
            if i != 0 and jj != 0 and i != jj:
                continue
            na, nb = a - i, b - jj
            if (na, nb) in cold:
                moves.append((i, jj))
    moves.sort()
    i, jj = moves[0]
    return "WIN " + str(i) + " " + str(jj)
