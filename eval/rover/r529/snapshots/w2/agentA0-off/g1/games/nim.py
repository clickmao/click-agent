"""多堆 Nim：从某一堆取任意正数，取走最后一颗者胜。"""


def solve(text: str) -> str:
    lines = text.split("\n")
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()))[:m]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"

    # 堆号最小者：找到第一个可取的堆
    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:  # 取走后使异或和为 0
            return "WIN " + str(idx + 1) + " " + str(a - target)
    return "LOSE"
