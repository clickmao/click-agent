"""多堆 Nim: 必胜手输出。

输入格式:
    第一行一个整数 m (1<=m<=4, 石子堆数)
    第二行 m 个整数 a1..am (1<=ai<=15, 每堆石子数)

玩法: 每次从某一堆取走任意正数目石子(不能跨堆, 不超该堆现有数), 取走最后一颗者胜。

输出:
    先手必胜 => 一行 `WIN p r`: p 为必胜着法中堆号最小者(从 1 开始),
                r 为从该堆取走的石子数
    先手必败 => 一行 `LOSE`
"""


def solve(text: str) -> str:
    """入参=完整 stdin 文本, 返回=应当写出的 stdout 文本(末尾不带换行)。"""
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]

    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"

    # 堆号升序扫描: 首个能把手牌变为必败态的堆即为堆号最小的必胜着法。
    # 该堆至多存在一个必胜着法(不同赢法需两种不同新值, 但目标值唯一 = a ^ xor)。
    for idx, a in enumerate(piles):
        target = a ^ xor
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"
