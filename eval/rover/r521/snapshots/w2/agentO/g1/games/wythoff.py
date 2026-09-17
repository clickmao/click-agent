#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""games/wythoff.py —— Wythoff 博弈的必败点判定。

规则 (normal play, 取尽者胜):
    两堆 (a, b) 石子。每步可任选其一:
      1) 从单堆中取走任意正数颗;
      2) 从两堆中同时取走相同正数颗。
    无法行动者负 (即取尽者胜)。

必败点 (P-positions) 闭式 (Beatty 序列):
    排序后记 a <= b, d = b - a。存在唯一 n = d >= 0 使得
        (a, b) == (floor(n*phi), floor(n*phi) + n),   phi = (1+sqrt(5))/2
    故判据:  a == floor(d * phi)   (d == 0 时即 (0,0) 为必败点)。

    精确整数实现 (无浮点、无误差):
        floor(n*phi) = (n + isqrt(5*n*n)) // 2
    该恒等式对整数 n >= 0 成立: n*phi = (n + n*sqrt5)/2,
    且 floor((n + sqrt(5n^2))/2) == (n + isqrt(5n^2)) // 2 (n 为整数)。

接口:
    solve(text) -> "LOSE" | "WIN"
        "LOSE": 当前局面是必败点 (先手必败)
        "WIN" : 先手必胜

输入 (STDIN 整体交给 solve):
    第一行两个整数 a b (允许任意顺序; 负值按 0 处理)。
    多余 token 忽略; 不足则补 0; 非法 token 跳过。
    空输入 -> "LOSE" ((0,0) 是必败点)。

运行:
    echo "2 1" | python3 games/wythoff.py
    python3 games/wythoff.py --selftest     # 无头自检, PASS 退出码 0

零第三方依赖, 单文件, 跨平台 (不调用 shell)。
"""

import sys

try:
    from math import isqrt
except ImportError:  # pragma: no cover
    def isqrt(n):
        if n < 0:
            raise ValueError("isqrt of negative")
        x = int(n ** 0.5)
        while x * x > n:
            x -= 1
        while (x + 1) * (x + 1) <= n:
            x += 1
        return x


def floor_phi_times(n):
    """精确求 floor(n * phi), n >= 0, 纯整数运算。

    phi = (1 + sqrt(5)) / 2  =>  n*phi = (n + n*sqrt(5)) / 2
    对整数 n >= 0: floor(n*phi) == (n + isqrt(5*n*n)) // 2
    """
    if n <= 0:
        return 0
    n2 = n * n
    return (n + isqrt(5 * n2)) // 2


def is_losing(a, b):
    """(a, b) 是否为必败点 (先手必败)。"""
    if a < 0:
        a = 0
    if b < 0:
        b = 0
    if a > b:
        a, b = b, a
    d = b - a
    return a == floor_phi_times(d)


def solve(text):
    """主入口: 返回 "LOSE" 或 "WIN"。"""
    nums = []
    for tok in (text if text else "").replace(",", " ").split():
        try:
            nums.append(int(tok))
        except ValueError:
            continue
    a = nums[0] if len(nums) > 0 else 0
    b = nums[1] if len(nums) > 1 else 0
    return "LOSE" if is_losing(a, b) else "WIN"


# --------------------------------------------------------------------------
# 自检
# --------------------------------------------------------------------------

def _brute_table(limit):
    """独立暴力 DP 求 limit x limit 内所有局面胜负 (第三只眼)。

    返回 px[a][b] = True 表示该局面先手必胜。
    与闭式实现完全独立地按规则枚举走法。
    """
    px = [[False] * (limit + 1) for _ in range(limit + 1)]
    for a in range(limit + 1):
        for b in range(limit + 1):
            win = False
            for x in range(a):                       # 单堆取 (a 堆)
                if not px[x][b]:
                    win = True
                    break
            if not win:
                for y in range(b):                   # 单堆取 (b 堆)
                    if not px[a][y]:
                        win = True
                        break
            if not win:
                for t in range(1, min(a, b) + 1):    # 两堆同时取 t
                    if not px[a - t][b - t]:
                        win = True
                        break
            px[a][b] = win
    return px


def _selftest():
    fails = []

    def check(name, got, want):
        if got != want:
            fails.append("%s: got=%r want=%r" % (name, got, want))

    # 1) 已知必败点 (Beatty 序列, 前 12 项), 交换对称
    known = [(0, 0), (1, 2), (3, 5), (4, 7), (6, 10), (8, 13),
             (9, 15), (11, 18), (12, 20), (14, 23), (16, 26), (17, 28)]
    for a, b in known:
        check("P-sorted-%d-%d" % (a, b), is_losing(a, b), True)
        check("P-swapped-%d-%d" % (a, b), is_losing(b, a), True)

    # 2) 已知必胜点
    for a, b in [(0, 1), (1, 1), (2, 2), (2, 3), (5, 6), (1, 3), (10, 12), (7, 8)]:
        check("N-%d-%d" % (a, b), is_losing(a, b), False)

    # 3) 与独立暴力 DP 逐点对账 (第三只眼) —— 覆盖 0..40 全部 1681 个局面
    L = 40
    px = _brute_table(L)
    bad = []
    for a in range(L + 1):
        for b in range(L + 1):
            brute_lose = not px[a][b]
            if brute_lose != is_losing(a, b):
                bad.append((a, b, brute_lose, is_losing(a, b)))
    check("brute-agreement-0..40", bad, [])

    # 4) 结构不变式: 每个差分 d >= 1 恰对应一个必败点; d 全覆盖 1..79
    covers = {}
    for n in range(0, 80):
        a = floor_phi_times(n)
        b = a + n
        if not is_losing(a, b):
            bad.append(("beatty-not-losing", n, a, b))
        if n >= 1:
            covers[n] = covers.get(n, 0) + 1
    check("beatty-self-consistent", [x for x in bad if x[0] == "beatty-not-losing"], [])
    check("diff-unique-1..79", [k for k, v in covers.items() if v != 1], [])
    check("diff-cover-1..79", sorted(covers.keys()), list(range(1, 80)))

    # 5) floor_phi_times 与高精度浮点对照 (小数范围, 独立口径)
    import math
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    fp_bad = []
    for n in range(0, 2000):
        if floor_phi_times(n) != int(math.floor(n * phi)):
            fp_bad.append(n)
    check("floor-phi-vs-float", fp_bad, [])

    # 6) 边界: 空输入 / 缺参 / 非法 token / 负值 / 逗号
    check("empty", solve(""), "LOSE")
    check("blank", solve("   \n  "), "LOSE")
    check("one-arg", solve("5"), "WIN")
    check("one-arg-1", solve("1"), "WIN")
    check("extra-tokens", solve("1 2 99 99"), "LOSE")
    check("junk", solve("x 1 2 y"), "LOSE")
    check("junk-only", solve("abc"), "LOSE")
    check("neg", solve("-3 -5"), "LOSE")
    check("neg-one", solve("-1 2"), "LOSE")
    check("comma", solve("1,2"), "LOSE")

    # 7) 负向控制: 若把判据反转, 已知必败点必须全部判红 (证明判据非空心)
    reverse_wrong = 0
    for a, b in known:
        if not is_losing(a, b):      # 反转后的"必败"判定
            reverse_wrong += 1
    check("neg-control-reverse-must-hit-all", reverse_wrong, len(known))

    # 8) 大数: Beatty 自洽 + 耗时
    import time
    t0 = time.time()
    ok_big = True
    for n in (10 ** 5, 10 ** 6, 10 ** 7, 10 ** 12):
        a = floor_phi_times(n)
        if not is_losing(a, a + n):
            ok_big = False
        if is_losing(a + 1, a + n):
            ok_big = False
    check("big-beatty", ok_big, True)
    dt = time.time() - t0
    if dt > 5.0:
        fails.append("big-beatty too slow: %.3fs" % dt)

    if fails:
        sys.stderr.write("FAIL\n")
        for f in fails:
            sys.stderr.write("  - %s\n" % f)
        return 1
    sys.stdout.write("PASS\n")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(_selftest())
    sys.stdout.write(solve(sys.stdin.read()) + "\n")
    sys.exit(0)
