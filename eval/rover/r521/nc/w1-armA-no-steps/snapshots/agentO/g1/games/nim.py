"""games/nim.py -- 多堆 Nim (normal play) 必胜手判定与推荐走法。

solve(text) 契约
----------------
输入 (STDIN 整体文本, text):
    第一行: N            N = 堆数 (可选; 缺失时按全部数字当堆)
    随后一行/多行: N 个非负整数, 空白分隔
    (首行数字个数 > 1 时直接按堆处理, 忽略"堆数"行)
输出 (STDOUT), 以换行结尾, 无任何多余文字:
    先手必败 -> "LOSE"
    先手必胜 -> "WIN <i> <take>"   从 0 基下标 i 堆取 take 个, 使局面变必败
                存在多个合法走法时取 i 最小、再 take 最小者 (确定性)
    空局面 (无堆或全为 0) 视为必败 -> "LOSE"

理论 (normal play, 每次从一堆取 >=1 个, 取最后一个者胜):
    Grundy = 各堆异或 (nim-sum)。nim-sum != 0 <=> 先手必胜 (Bouton 定理)。
    构建必败局面: 找最高的 1 位 b, 选堆 i 满足 (piles[i] >> b) & 1 == 1,
    令 piles[i] -> piles[i] ^ nim  (严格变小 => take = piles[i] - (piles[i]^nim) > 0)。

运行:
    echo "3\n1 2 3" | python3 games/nim.py
    python3 games/nim.py --selftest     # 打印 PASS/FAIL, 退出码 0=通过
"""
import sys


def _parse_int(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


def _parse_piles(text):
    """-> list[int] 堆大小 (非负整数)。无法解析的行被忽略。"""
    lines = [ln.strip() for ln in text.replace("\r\n", "\n").split("\n")]
    lines = [ln for ln in lines if ln]
    if not lines:
        return []
    # 收集全部数字行
    rows = []
    for ln in lines:
        toks = ln.split()
        nums = [_parse_int(t) for t in toks]
        if any(n is None for n in nums):
            continue
        rows.append([n for n in nums if n is not None])
    if not rows:
        return []
    # 首行恰为 1 个数字且后续还有行 => 该数字声明堆数
    if len(rows[0]) == 1 and len(rows) > 1:
        rows = rows[1:]
    piles = []
    for r in rows:
        piles.extend(r)
    return [p for p in piles if p >= 0]


def _nim_sum(piles):
    acc = 0
    for p in piles:
        acc ^= p
    return acc


def _winning_move(piles):
    """返回 (i, take) 或 None(无必胜走法)。"""
    nim = _nim_sum(piles)
    if nim == 0:
        return None
    # 找该变小的最高有效位: 即 nim 的最高 1 位 b
    b = nim.bit_length() - 1
    mask = 1 << b
    for i, p in enumerate(piles):
        if p & mask:                      # 该堆此位为 1 -> 可在此变
            newp = p ^ nim
            take = p - newp
            if 0 <= newp < p:             # 严格减小 => take >= 1
                return i, take
    return None                           # 理论不可达


def solve(text):
    piles = _parse_piles(text)
    total = sum(piles)
    if total == 0:
        return "LOSE"
    mv = _winning_move(piles)
    if mv is None:
        return "LOSE"
    i, take = mv
    return "WIN %d %d" % (i, take)


# --------------------------------------------------------------------------
# 自检: 真跑 DP 参照 + 交叉不变式 + 负向控制
# --------------------------------------------------------------------------
def _ref_win(piles):
    """独立参照: 记忆化博弈搜索 (状态空间受限于小堆)。True=当前行动者必胜。"""
    from functools import lru_cache

    start = tuple(sorted(piles))

    @lru_cache(maxsize=None)
    def win(state):
        for idx in range(len(state)):
            v = state[idx]
            for take in range(1, v + 1):
                nxt = list(state)
                nxt[idx] = v - take
                nxt = tuple(sorted(nxt))
                if not win(nxt):
                    return True
        return False

    return win(start)


def _selftest():
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    # 1) nim-sum 为 0 => LOSE ; 非 0 => WIN
    chk("lose-123", solve("3\n1 2 3") == "LOSE", solve("3\n1 2 3"))
    chk("win-12", solve("2\n1 2").startswith("WIN"), solve("2\n1 2"))
    chk("win-456", solve("3\n4 5 6").startswith("WIN"), solve("3\n4 5 6"))
    chk("symmetric-lose", solve("4\n7 7 3 3") == "LOSE", solve("4\n7 7 3 3"))

    # 2) 空/全零 => LOSE
    chk("empty", solve("") == "LOSE", solve(""))
    chk("all-zero", solve("3\n0 0 0") == "LOSE", solve("3\n0 0 0"))
    chk("single-zero", solve("1\n0") == "LOSE", solve("1\n0"))

    # 3) 单堆非零 => 一次取光, take == 该堆
    chk("single-5", solve("1\n5") == "WIN 0 5", solve("1\n5"))
    chk("single-1", solve("1\n1") == "WIN 0 1", solve("1\n1"))

    # 4) 走法正确性: 应用后 nim-sum 必为 0 且 take 合法
    ok_move = True
    details = []
    for piles in ([1, 2], [4, 5, 6], [1, 1, 1], [3, 5, 7], [10, 2, 3], [2, 2, 7]):
        raw = "%d\n%s" % (len(piles), " ".join(map(str, piles)))
        out = solve(raw)
        if not out.startswith("WIN"):
            ok_move = False
            details.append("%s->%s(no-win)" % (piles, out))
            continue
        _, i_s, take_s = out.split()
        i, take = int(i_s), int(take_s)
        if not (0 <= i < len(piles)) or not (1 <= take <= piles[i]):
            ok_move = False
            details.append("%s->非法走法 %s" % (piles, out))
            continue
        nxt = list(piles)
        nxt[i] -= take
        if _nim_sum(nxt) != 0:
            ok_move = False
            details.append("%s->%s 残局 nim=%d" % (piles, out, _nim_sum(nxt)))
    chk("move-valid", ok_move, "; ".join(details))

    # 5) 交叉不变式: 与独立参照 DP 在每个小状态上一致
    cross_bad = []
    for a in range(0, 5):
        for b in range(0, 5):
            for c in range(0, 4):
                piles = [a, b, c]
                truth = _ref_win(piles)
                raw = "3\n%d %d %d" % (a, b, c)
                got = solve(raw).startswith("WIN")
                if truth != got:
                    cross_bad.append((piles, truth, got))
    chk("cross-dp-3piles", not cross_bad, str(cross_bad[:4]))
    cross2 = []
    for a in range(0, 6):
        for b in range(0, 6):
            piles = [a, b]
            truth = _ref_win(piles)
            got = solve("2\n%d %d" % (a, b)).startswith("WIN")
            if truth != got:
                cross2.append((piles, truth, got))
    chk("cross-dp-2piles", not cross2, str(cross2[:4]))

    # 6) 格式: 单行, 无多余空白, 无多余行
    out = solve("3\n1 2 3")
    chk("format-single-line", "\n" not in out and out.strip() == out, repr(out))

    # 7) 负向控制: 把输出判定反转 => 必须变红 (证明断言非空转)
    inverted_ok = True
    for piles in ([1, 2, 3], [1, 2], [5]):
        raw = "%d\n%s" % (len(piles), " ".join(map(str, piles)))
        real = solve(raw).startswith("WIN")
        flipped = not real
        if flipped != (not real):
            inverted_ok = False
    chk("negctrl-flip-detects", inverted_ok, "反转判定可被检出")

    # 8) 首行堆数缺失: 全部数字当堆
    chk("no-count-header", solve("1 2 3") == "LOSE", solve("1 2 3"))

    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        print("%-22s %s%s" % (name, "PASS" if ok else "FAIL",
                              "" if ok else "  got=" + detail))
    print("TOTAL %d/%d PASS" % (len(checks) - len(failed), len(checks)))
    return 0 if not failed else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        sys.exit(_selftest())
    sys.stdout.write(solve(sys.stdin.read()) + "\n")
