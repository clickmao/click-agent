"""games/wythoff.py -- Wythoff 博弈 (两堆) 必败点判定。

solve(text) 契约
----------------
输入 (STDIN 整体文本, text):
    第一行: 两个非负整数 a b (空白分隔)。
    兼容形态: 首行声明规模 (如 "1") 后跟若干行 "a b", 逐对判定并逐行输出。
    兼容形态: 多行数字 > 2 个时, 取前两个作为一堆? -> 不做推断, 只取每行前两个。
输出 (STDOUT), 每行一个结果, 行间 "\n", 结尾换行, 无任何多余文字:
    "LOSE"  <=> (a, b) 是必败点 (P-position)
    "WIN"   <=> 其余局面 (先手必胜)

规则 (Wythoff 博弈): 两堆各若干, 每步可
    ① 从任意一堆取 >=1 个; ② 从两堆同时取相同个数 (>=1)。
    取最后一个者胜 (normal play)。

理论 (Beatty 定理 / Wythoff 序列):
    必败点恰为 (⌊n*φ⌋, ⌊n*φ^2⌋), n = 0,1,2,...  φ = (1+√5)/2, φ^2 = φ+1。
    记 a = ⌊n*φ⌋, b = a + n  (= ⌊n*φ⌋ + n = ⌊n*φ^2⌋)。
    判定闭式: 设 x = min(a,b), y = max(a,b), d = y - x,
              x == ⌊d*φ⌋  <=> LOSE。   (由 (x,y)=(⌊nφ⌋,⌊nφ⌋+n) 且 d=n 得)
    实现用整数牛顿法算 isqrt 避免浮点误差: ⌊k*φ⌋ = ⌊k*(1+√5)/2⌋。

运行:
    printf "1 2\n"      | python3 games/wythoff.py    # -> LOSE
    printf "1\n1 2\n3 5\n4 7\n" | python3 games/wythoff.py
    python3 games/wythoff.py --selftest    # 打印 PASS/FAIL, 退出码 0=通过
"""
import sys

__all__ = ["solve", "is_cold", "wythoff_pair", "beatty_floor_phi"]


def _parse_int(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


def isqrt(n):
    """整数平方根 (向下取整), 只用整数运算, 不依赖 math 浮点。"""
    if n < 0:
        raise ValueError("isqrt of negative number")
    if n == 0:
        return 0
    x = 1 << ((n.bit_length() + 1) // 2)
    while True:
        y = (x + n // x) // 2
        if y >= x:
            return x
        x = y


def beatty_floor_phi(k):
    """⌊k * φ⌋, φ = (1+√5)/2, 纯整数实现 (k >= 0)。

    k*φ = k/2 + k*√5/2 。k*√5 = isqrt(5*k*k) 在 k 为整数时是无理数部分的
    精确下取整 (5*k*k 非完全平方数, 恒有 (isqrt)^2 < 5k^2 < (isqrt+1)^2),
    故 ⌊k*√5⌋ = isqrt(5*k*k)。再处理 k 的奇偶:
        k = 2m   : k*φ = m + m√5   -> ⌊⌋ = m + ⌊m√5⌋        = m + isqrt(5m^2)
        k = 2m+1 : k*φ = m + 0.5 + (m+0.5)√5
                   由于 (m+0.5)√5 的小数部分恰为 0.5 时不可能 (√5 无理),
                   等价用 2*(⌊k*φ⌋) 判定更稳 -> 取 (k + ⌊k√5⌋) // 2
    统一形式: ⌊k*φ⌋ = (k + isqrt(5*k*k)) // 2  (对整数 k>=0 严格成立;
    因为 k + ⌊k√5⌋ 与 2⌊kφ⌋ 相差 0 或 1, 取 //2 即得)。
    """
    if k < 0:
        raise ValueError("k must be >= 0")
    return (k + isqrt(5 * k * k)) // 2


def wythoff_pair(n):
    """第 n 个必败点 (⌊nφ⌋, ⌊nφ⌋ + n)。n >= 0。"""
    a = beatty_floor_phi(n)
    return a, a + n


def is_cold(a, b):
    """(a, b) 是否必败点。允许乱序输入。"""
    x, y = (a, b) if a <= b else (b, a)
    d = y - x
    return x == beatty_floor_phi(d)


# --------------------------------------------------------------------------
# 独立参照实现: 小范围直接 DP 求 P-position (不依赖 Beatty 公式)
# 用于交叉不变式, 防止闭式写错时自检空转。
# --------------------------------------------------------------------------
def _ref_cold_table(nmax):
    """返回 bool 表 table[x][y], True 表示 (x,y) 必败。0 <= x,y <= nmax。

    DP 依据: (x,y) 必败 <=> 所有合法后继均必胜。
    """
    table = [[False] * (nmax + 1) for _ in range(nmax + 1)]
    for x in range(nmax + 1):
        for y in range(nmax + 1):
            if x == 0 and y == 0:
                table[x][y] = True       # 空局面, 无路可走 => 必败
                continue
            win = False
            # ① 从第一堆取
            for t in range(1, x + 1):
                if table[x - t][y]:
                    win = True
                    break
            # ② 从第二堆取
            if not win:
                for t in range(1, y + 1):
                    if table[x][y - t]:
                        win = True
                        break
            # ③ 两堆同取
            if not win:
                for t in range(1, min(x, y) + 1):
                    if table[x - t][y - t]:
                        win = True
                        break
            table[x][y] = not win
    return table


def solve(text):
    """把输入文本解析成若干 (a, b) 对, 逐行返回 'LOSE' / 'WIN'。"""
    lines = [ln.strip() for ln in text.replace("\r\n", "\n").split("\n")]
    lines = [ln for ln in lines if ln]
    pairs = []
    for idx, ln in enumerate(lines):
        toks = ln.split()
        nums = [_parse_int(t) for t in toks]
        if any(n is None for n in nums):
            continue
        if len(nums) > 2:
            continue                     # 声明行 (如 "1") 或杂项, 跳过
        if len(nums) == 2:
            pairs.append((nums[0], nums[1]))
        elif len(nums) == 1 and idx == len(lines) - 1:
            pairs.append((nums[0], 0))   # 单数字结尾行: 视作 (n, 0)
    out = []
    for a, b in pairs:
        if a < 0 or b < 0:
            continue
        out.append("LOSE" if is_cold(a, b) else "WIN")
    return "\n".join(out) + ("\n" if out else "")


# --------------------------------------------------------------------------
# 自检
# --------------------------------------------------------------------------
def _selftest():
    results = []

    def check(name, got, want):
        ok = got == want
        results.append((name, ok, got, want))

    # 1) 已知必败点 (Beatty 序列前 10 个: (0,0),(1,2),(3,5),(4,7),(6,10),
    #    (8,13),(9,15),(11,18),(12,20),(14,23))
    known_cold = [(0, 0), (1, 2), (3, 5), (4, 7), (6, 10),
                  (8, 13), (9, 15), (11, 18), (12, 20), (14, 23)]
    for (a, b) in known_cold:
        check("cold(%d,%d)" % (a, b), is_cold(a, b), True)
        check("cold-rev(%d,%d)" % (b, a), is_cold(b, a), True)

    # 2) 已知必胜点
    for (a, b) in [(1, 1), (2, 2), (1, 3), (2, 3), (5, 5), (5, 6), (0, 1), (0, 5)]:
        check("hot(%d,%d)" % (a, b), is_cold(a, b), False)

    # 3) 生成器自洽: wythoff_pair(n) 必须判 LOSE, 且相邻必败点严格递增
    prev = (-1, -1)
    gen_ok = True
    for n in range(0, 200):
        a, b = wythoff_pair(n)
        if not is_cold(a, b) or not (a > prev[0] and b > prev[1]):
            gen_ok = False
            break
        prev = (a, b)
    check("generator-monotone-and-cold(0..199)", gen_ok, True)

    # 4) 闭式 vs 独立 DP 交叉不变式 (0..60 全状态)
    nmax = 60
    table = _ref_cold_table(nmax)
    mismatch = []
    for x in range(nmax + 1):
        for y in range(nmax + 1):
            if is_cold(x, y) != table[x][y]:
                mismatch.append((x, y))
    check("closed-form vs reference-DP (0..60)^2 mismatches",
          len(mismatch), 0)

    # 5) 必败点行列不冲突 (Wythoff 序列是 0,1,2,... 的一个置换)
    rows = set()
    cols = set()
    perm_ok = True
    for n in range(1, 200):
        a, b = wythoff_pair(n)
        if a in rows or b in rows or a in cols or b in cols or a == b:
            perm_ok = False
            break
        rows.add(a)
        cols.add(b)
    check("Beatty sequence is a permutation of N", perm_ok, True)

    # 6) beatty_floor_phi 整数实现 vs 高精度浮点参照 (k <= 5000)
    #    浮点仅作参照, 允许误差 0 (比较前先取整; k 小范围不会有 ULP 问题)
    import math
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    bad = [k for k in range(0, 5001) if beatty_floor_phi(k) != int(math.floor(k * phi))]
    check("beatty int vs float reference k<=5000", len(bad), 0)

    # 7) 端到端 solve()
    check("solve single cold", solve("1 2\n"), "LOSE\n")
    check("solve single hot", solve("2 3\n"), "WIN\n")
    check("solve multi row", solve("1\n1 2\n3 5\n2 3\n0 0\n"), "LOSE\nLOSE\nWIN\nLOSE\n")
    check("solve empty input", solve(""), "")

    # 8) 负向控制: 故意破坏判定, 断言必须变红
    #    (把 d 用 x+y 代替, 语义错误 -> 结果必须与正确判定不同)
    def _broken(a, b):
        x, y = (a, b) if a <= b else (b, a)
        return x == beatty_floor_phi(x + y)
    diff = 0
    for x in range(0, 30):
        for y in range(0, 30):
            if _broken(x, y) != is_cold(x, y):
                diff += 1
    check("negctrl: broken rule detectable (diff > 0)", diff > 0, True)

    passed = sum(1 for _, ok, _, _ in results if ok)
    total = len(results)
    for name, ok, got, want in results:
        if not ok:
            print("FAIL %s: got=%r want=%r" % (name, got, want))
    print("PASS %d/%d" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        sys.exit(_selftest())
    sys.stdout.write(solve(sys.stdin.read()))
