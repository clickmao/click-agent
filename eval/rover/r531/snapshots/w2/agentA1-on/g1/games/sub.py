"""取石子子游戏: n 颗石子, 可取的数目集合 s, 最后一颗者胜。"""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    s = sorted({int(x) for x in tokens[2:2 + k]})

    # win[i] = 剩余 i 颗石子时, 轮到行动的一方是否必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for step in s:
            if step > i:
                break
            if not win[i - step]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    for step in s:
        if step <= n and not win[n - step]:
            return 'WIN %d' % step
    return 'LOSE'
