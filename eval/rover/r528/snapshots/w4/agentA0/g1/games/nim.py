"""多堆 Nim: 先手必胜时给出 (堆号最小, 从该堆取走数)。

石子堆数 m<=4, 每堆 ai<=15。取尽最后一颗者胜。
必胜依据: 各堆异或和非零; 最小堆号 i 上取 r 使新的异或和为 0。
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    # 从堆号最小者起寻找可制胜的取法
    for i in range(m):
        target = piles[i] ^ x
        if target < piles[i]:
            r = piles[i] - target
            return 'WIN %d %d' % (i + 1, r)
    return 'LOSE'  # 理论不可达
