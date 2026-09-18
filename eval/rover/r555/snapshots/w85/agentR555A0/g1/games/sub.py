"""取石子（子游戏）：先手必胜/必败判定，必胜时给出数值最小的首取数。

输入：第一行 n k；第二行 k 个互不相同且含 1 的整数。
输出：'WIN m' 或 'LOSE'，末尾不带换行。
"""


def solve(text):
    lines = text.split('\n')
    p = 0
    while p < len(lines) and lines[p].strip() == '':
        p += 1
    n, k = map(int, lines[p].split())
    p += 1
    moves = []
    while len(moves) < k and p < len(lines):
        row = lines[p].split()
        p += 1
        for tok in row:
            moves.append(int(tok))
            if len(moves) == k:
                break
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s <= x and not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
