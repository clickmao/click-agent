#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""games/nim.py -- 多堆 Nim 的必胜手 (normal play, 取尽者胜)。

接口
----
solve(text) -> str

输入 (STDIN 整体文本):
    第一行  k            堆数 (k >= 0)
    第二行  a1 a2 ... ak 各堆石子数 (非负整数)
允许第一行后堆数不足/多余: 少则按 0 补齐, 多则忽略多余项 (容错)。

输出 (STDOUT, 单行):
    LOSE                       -- 先手必败 (各堆 xor == 0), 不存在必胜手
    WIN i j c                  -- 先手必胜: 从第 i 堆 (1-based) 取走 c 颗, 取后该堆为 j
    取法规范化: 在使局面异或和为 0 的所有取法中, 选 (i 最小, 取走数 c 最大)
               的那一手, 保证输出确定唯一。

自检
----
    python3 games/nim.py --selftest     # 打印 PASS/FAIL, 退出码 0=通过

零第三方依赖; 单文件。
"""

import sys

__all__ = ["solve", "main"]


def _parse_ints(line):
    """按空白切分并转成整数; 非法 token 忽略。"""
    out = []
    for tok in line.split():
        try:
            out.append(int(tok))
        except ValueError:
            continue
    return out


def _parse(text):
    """-> list[int] 各堆石子数 (已截断负数到 0)。空输入 -> []。"""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    k = _parse_ints(lines[0])
    k = k[0] if k else 0
    piles = _parse_ints(lines[1]) if len(lines) > 1 else []
    if k < 0:
        k = 0
    if len(piles) < k:
        piles = piles + [0] * (k - len(piles))
    else:
        piles = piles[:k]
    return [p if p > 0 else 0 for p in piles]  # 负堆按 0 处理


def _best_move(piles):
    """
    -> (i, take) 或 None
    i: 1-based 堆号; take: 取走颗数 (>0)。
    规则: 选 (i 最小, take 最大) 的制胜手; 无制胜手返回 None。
    """
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return None
    best = None
    for idx, p in enumerate(piles, 1):
        target = p ^ x          # 取后该堆剩余
        if target < p:          # 合法: 只能减少
            take = p - target
            if best is None or take > best[1]:
                best = (idx, take)
    return best


def solve(text):
    piles = _parse(text)
    mv = _best_move(piles)
    if mv is None:
        return "LOSE"
    i, take = mv
    j = piles[i - 1] - take
    return "WIN %d %d %d" % (i, j, take)


# ---------------------------------------------------------------- selftest --

def _selftest():
    fails = []

    def eq(actual, expected, label):
        if actual != expected:
            fails.append("%s: got %r want %r" % (label, actual, expected))

    # 1) 必败局面: 异或和 == 0
    for piles in [[0], [1, 1], [2, 3, 1], [4, 4, 4, 4], [5, 5], [1, 2, 3],
                  [7, 8, 15], [0, 0, 0]]:
        eq(solve("%d\n%s\n" % (len(piles), " ".join(map(str, piles)))),
           "LOSE", "xor0 %r" % (piles,))

    # 2) 必胜局面: 输出的手必须合法且把异或和归零; 并对 1 堆验证最优性闭式
    cases = [[1], [3], [1, 2], [2, 4, 7], [10, 1, 1], [100, 100, 1], [1, 1, 1]]
    for piles in cases:
        r = solve("%d\n%s\n" % (len(piles), " ".join(map(str, piles))))
        if not r.startswith("WIN "):
            fails.append("win-shape %r -> %r" % (piles, r))
            continue
        _, si, sj, sc = r.split()
        i, j, c = int(si), int(sj), int(sc)
        if not (1 <= i <= len(piles)):
            fails.append("idx-range %r -> %r" % (piles, r))
            continue
        if not (piles[i - 1] - c == j and c > 0 and j >= 0):
            fails.append("legal-move %r -> %r" % (piles, r))
            continue
        nxt = list(piles)
        nxt[i - 1] = j
        x = 0
        for p in nxt:
            x ^= p
        if x != 0:
            fails.append("not-zeroing %r -> %r" % (piles, r))

    # 3) 单堆闭式: 全取走
    eq(solve("1\n7\n"), "WIN 1 0 7", "single-pile")
    # 4) 规范化: (i 最小, take 最大)  --  [2,4,7] 异或=1;
    #    堆1: 2^1=3>2 不合法; 堆2: 4^1=5>4 不合法; 堆3: 7^1=6 -> take=1
    eq(solve("3\n2 4 7\n"), "WIN 3 6 1", "canon-1")
    #    [10,1,1]: 异或=10; 堆1: 10^10=0 -> take=10; 堆2/3: 1^10=11>1 不合法
    eq(solve("2\n10 1\n"), "WIN 1 1 9", "canon-2")
    #    [3,5]: 异或=6; 堆1: 3^6=5>3 不合法; 堆2: 5^6=3 -> take=2
    eq(solve("2\n3 5\n"), "WIN 2 3 2", "canon-3")

    # 5) 边界/容错
    eq(solve(""), "LOSE", "empty")
    eq(solve("0\n"), "LOSE", "zero-piles")
    eq(solve("3\n1 1\n"), "LOSE", "short-pad")       # 缺的堆补 0
    eq(solve("2\n1 1 9\n"), "LOSE", "trailing-ignored")
    eq(solve("2\n1 -5\n"), "WIN 1 0 1", "negpile")   # -5 -> 0, 异或=1
    eq(solve("2\nabc 3\n"), "WIN 1 0 3", "garbage")  # 非法 token 忽略, 剩 [3]

    # 6) 负向控制: 若把"归零手"写成"任意合法取法", 下列断言必须变红 ——
    #    这里直接验证"取后异或非零"的取法不会出现在输出里
    for piles in [[2, 4, 7], [3, 5], [1, 2, 4]]:
        r = solve("%d\n%s\n" % (len(piles), " ".join(map(str, piles))))
        _, si, sj, _sc = r.split()
        nxt = list(piles)
        nxt[int(si) - 1] = int(sj)
        x = 0
        for p in nxt:
            x ^= p
        if x != 0:
            fails.append("negctrl-nonzeroing %r -> %r" % (piles, r))

    if fails:
        print("FAIL")
        for f in fails:
            print("  " + f)
        return 1
    print("PASS")
    return 0


def main(argv):
    if len(argv) > 1 and argv[1] == "--selftest":
        return _selftest()
    data = sys.stdin.read()
    sys.stdout.write(solve(data) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
