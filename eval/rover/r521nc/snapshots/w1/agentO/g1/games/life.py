"""games/life.py — 康威生命游戏 (Conway's Game of Life) 演化。

solve(text) 契约
----------------
输入 (STDIN 整体文本, text):
    第一行: R C [G]        R 行 C 列, G = 演化代数 (可选, 默认 1)
    随后 R 行: 网格; 紧凑 (每行 C 字符) 或空格分隔均可
    (无法解析出首行 R C 时, 整体当作网格, 演化 1 代)
输出 (STDOUT):
    演化 G 代后的网格, 每行 C 个字符, 活=1 死=0, 行间 '\n', 无多余文字。

活细胞字符: 1 # * x X +   其余字符视为死。
规则: 活细胞邻居数 2/3 存活; 死细胞邻居数恰为 3 诞生; 边界外视为死。
输出统一为 '0'/'1', 因此 0 代返回的也是归一化网格 (活字符→'1')。

运行:
    python3 life.py < input.txt
    python3 -c "from games.life import solve; print(solve('3 3 1\\n010\\n010\\n010'))"
    python3 life.py --selftest        # 打印 PASS/FAIL, 退出码 0=通过
"""
import sys

ALIVE = frozenset("1#*xX+")
DEAD_OUT = "0"
ALIVE_OUT = "1"


def _parse(text):
    """-> (rows, cols, generations, grid) ; grid 为 list[str] 每行恰好 cols 字符。"""
    lines = [ln.rstrip("\r\n") for ln in text.split("\n")]
    while lines and lines[-1].strip() == "":
        lines.pop()
    if not lines:
        return 0, 0, 1, []

    head = lines[0].split()
    if len(head) >= 2:
        try:
            r = int(head[0])
            c = int(head[1])
        except ValueError:
            r = c = None
        if r is not None and r >= 0 and c is not None and c >= 0:
            gens = int(head[2]) if len(head) >= 3 else 1
            body = lines[1:1 + r]
            grid = [_fit(ln, c) for ln in body]
            while len(grid) < r:
                grid.append(DEAD_OUT * c)
            return r, c, gens, grid

    grid = ["".join(ln.split()) for ln in lines]
    rows = len(grid)
    cols = max((len(g) for g in grid), default=0)
    grid = [g.ljust(cols, DEAD_OUT) for g in grid]
    return rows, cols, 1, grid


def _fit(line, cols):
    """把一行规则化为恰好 cols 个 '0'/'1' 字符。"""
    cells = line.split()
    if len(cells) > 1:
        chars = ["".join(cells)]           # 空格分隔的 token 串
    else:
        chars = [line]                     # 紧凑串
    s = chars[0]
    return "".join(ALIVE_OUT if ch in ALIVE else DEAD_OUT for ch in s[:cols]) \
        .ljust(cols, DEAD_OUT)


def _step(rows, cols, grid):
    out = []
    for i in range(rows):
        gi_prev = grid[i - 1] if i - 1 >= 0 else None
        gi_cur = grid[i]
        gi_next = grid[i + 1] if i + 1 < rows else None
        row_chars = []
        for j in range(cols):
            n = 0
            for gi in (gi_prev, gi_cur, gi_next):
                if gi is None:
                    continue
                for nj in (j - 1, j, j + 1):
                    if nj < 0 or nj >= cols:
                        continue
                    if gi is gi_cur and nj == j:
                        continue           # 跳过中心格自身
                    if gi[nj] in ALIVE:
                        n += 1
            if gi_cur[j] in ALIVE:
                row_chars.append(ALIVE_OUT if (n == 2 or n == 3) else DEAD_OUT)
            else:
                row_chars.append(ALIVE_OUT if n == 3 else DEAD_OUT)
        out.append("".join(row_chars))
    return out


def _render(rows, cols, gens, grid):
    for _ in range(max(0, gens)):
        grid = _step(rows, cols, grid)
    return "\n".join(grid)


def solve(text):
    """演化康威生命游戏, 返回结果字符串 (不含尾部换行)。"""
    rows, cols, gens, grid = _parse(text)
    return _render(rows, cols, gens, grid)


def _selftest():
    ok = True

    def check(name, got, want):
        nonlocal ok
        good = got == want
        print(("PASS " if good else "FAIL ") + name +
              ("" if good else " | got=%r want=%r" % (got, want)))
        if not good:
            ok = False

    # 1) 闪烁器 1 代: 竖 -> 横
    check("blinker-1gen", solve("3 3 1\n010\n010\n010"), "000\n111\n000")
    # 2) 闪烁器 2 代回到原状
    check("blinker-2gen", solve("3 3 2\n010\n010\n010"), "010\n010\n010")
    # 3) 方块 5 代稳定不变
    check("block-stable", solve("4 4 5\n0000\n0110\n0110\n0000"),
          "0000\n0110\n0110\n0000")
    # 4) 0 代: 归一化输出 (活字符 '#' -> '1')
    check("generation-0", solve("3 3 0\n1#0\n000\n000"), "110\n000\n000")
    # 5) 回退路径 (无首行尺寸) + 尾部换行容忍
    check("fallback-parser", solve("010\n010\n010\n"), "000\n111\n000")
    # 6) 边界外视为死: 孤立单细胞 1 代后死亡
    check("boundary-dead", solve("1 1 1\n1"), "0")
    # 7) 空格分隔网格 + 活字符归一化
    check("spaced-alive", solve("3 3 1\n0 # 0\n0 # 0\n0 # 0"), "000\n111\n000")
    # 8) 行数不足时补死行; 毒细胞(非活字符)不计活
    check("short-rows", solve("3 3 1\n0y0\n0y0"), "000\n111\n000")

    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        sys.exit(_selftest())
    data = sys.stdin.read()
    out = solve(data)
    sys.stdout.write(out)
    if out:
        sys.stdout.write("\n")
