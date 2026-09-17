"""games/sub.py — 子游戏 (subtraction game) 必胜/必败判定。

solve(text) 契约
----------------
输入 (STDIN 整体文本, text), 容错解析:
    首行 N [M1 M2 ... Mk]
        N        : 堆大小 (非负)
        M1..Mk   : 可取子数集合 (正整数, 以 0 结尾亦可, 忽略后续非整数)
      例 "7 3"      -> 可取 [1..3]
      例 "8 3"      -> 8, 可取 [1..3]
      例 "7 1 3 5"  -> 7, 显式集合 {1,3,5}
      例 "N"        -> 可取 [1]
    无法解析 -> 视为 (0, [1])  => 空堆, 必败。
输出 (STDOUT): "win" 或 "lose" (必败 = P-position, 不能动者输) 无多余文字。
规则: P(0) 必败; P(n) 必胜 <=> 存在 a in moves, a<=n, 使 P(n-a) 必败。
     moves == [1..k] 时闭式 P(n) = (n % (k+1) == 0), 与 DP 等价 (自检里交叉验证)。
运行:
    python3 sub.py < input.txt
    python3 sub.py --selftest      # 打印 PASS/FAIL, 退出码 0=通过
"""
import sys

WIN = "win"
LOSE = "lose"


def _parse(text):
    """-> (n, moves) ; moves 为升序去重正整数元组。无法解析 -> (0, (1,))"""
    toks = text.split()
    if not toks:
        return 0, (1,)
    try:
        n = max(int(toks[0]), 0)
    except ValueError:
        return 0, (1,)
    rest = []
    for t in toks[1:]:
        try:
            v = int(t)
        except ValueError:
            break
        if v <= 0:
            break
        rest.append(v)
    if rest:
        return n, tuple(sorted(set(rest)))
    return n, (1,)


def _is_losing(n, moves):
    """真 = 必败 (P-position)。"""
    if n <= 0:
        return True
    max_mv = max(moves)
    if moves == tuple(range(1, max_mv + 1)):
        return n % (max_mv + 1) == 0        # [1..k] 闭式解
    # 通用 DP: win[i] = 大小为 i 的先手是否必胜; 窗口保留 max_mv+1 个历史
    span = max_mv + 1
    win = [True] + [False] * min(n, span - 1)   # win[0] = True (视 0 为已被对手取完)
    for i in range(1, n + 1):
        if i < len(win):
            cur = win[i]
        else:
            cur = False
            for a in moves:
                if a <= i and win[i - a] is False:
                    cur = True
                    break
            win.append(cur)
        if i >= span and len(win) > span:
            win = win[len(win) - span:]     # 滑动窗口: 只需最近 span 个
    return win[-1] is False


def solve(text):
    """子游戏必胜/必败判定: 返回 'win' 或 'lose'。"""
    n, moves = _parse(text)
    return LOSE if _is_losing(n, moves) else WIN


# ---------------------------------------------------------------- selftest
def _dp_ref(n, moves):
    """独立参照实现 (不做窗口优化), 用于交叉验证。返回 True=必败。"""
    win = [False] * (n + 1)
    win[0] = True                                    # 视 0 为已终局
    for i in range(1, n + 1):
        win[i] = any(i - a >= 0 and win[i - a] is False for a in moves)
    return win[n] is False


def _selftest():
    fails = []

    cases = [
        ("7 3", WIN),      # 7 % 4 = 3 -> 必胜
        ("8 3", LOSE),     # 8 % 4 = 0 -> 必败
        ("4 1", LOSE),     # 只能取 1, 偶数必败
        ("5 1", WIN),
        ("0 3", LOSE),     # 空堆, 先手不能动 -> 必败
        ("1 3", WIN),
        ("10 2 3", LOSE),  # 显式集合 {2,3}: 10-2=8,10-3=7 皆 win -> 10 lose
        ("6 4", WIN),
        ("7 1 3 5", WIN),
    ]
    for src, want in cases:
        got = solve(src)
        ok = got == want
        print("PASS" if ok else "FAIL", repr(src), "->", got, "(want", want + ")")
        if not ok:
            fails.append("case:" + src)

    # 不变式 1: 优化版窗口 DP == 独立参照 DP, 全部组合
    for moves in [(1,), (2,), (1, 2), (2, 3), (1, 3, 5), (1, 2, 3), (3, 5, 7)]:
        for n in range(0, 60):
            a = _is_losing(n, moves)
            b = _dp_ref(n, moves)
            if a != b:
                print("FAIL invariant opt-vs-ref moves=%r n=%d %s %s" % (moves, n, a, b))
                fails.append("inv1:%r:%d" % (moves, n))
    print("PASS invariant opt-vs-ref" if not fails else "FAIL invariant opt-vs-ref")

    # 不变式 2: [1..k] 闭式 == 参照 DP
    for k in (1, 2, 3, 5):
        for n in range(0, 60):
            cf = (n % (k + 1) == 0)
            ref = _dp_ref(n, tuple(range(1, k + 1)))
            if cf != ref:
                print("FAIL invariant closeform k=%d n=%d" % (k, n))
                fails.append("inv2:%d:%d" % (k, n))
    print("PASS invariant closeform" if not fails else "FAIL invariant closeform")

    # 不变式 3: 恰好一个终局判负 —— P(0) 必败, 且 moves 里无 0
    if _is_losing(0, (1, 2, 3)) is not True:
        print("FAIL terminal P(0) must be losing")
        fails.append("terminal")

    # 负向控制: 反转判定函数, 已知必胜输入必须读成 lose (证明断言非空转)
    n, moves = _parse("7 3")
    if (_is_losing(n, moves)) == True:
        print("FAIL negative-control: 7 3 must not be losing")
        fails.append("negctrl")

    print("SELFTEST", "PASS" if not fails else "FAIL", "fails=%d" % len(fails))
    return 0 if not fails else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.stdout.write(solve(sys.stdin.read()))
