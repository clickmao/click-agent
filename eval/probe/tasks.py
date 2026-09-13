#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""随机能力自检题集生成器 (R398 长期任务: 随机程序 + 随机数学题)

设计铁律
--------
1. **独立双路径**: 每道题的期望答案必须由**两条互相独立的路径**算出 (参考解 + 校验解);
   两条不一致 ⇒ **拒绝发题** (生成期硬失败, 绝不发"未验算的题")。
2. **公开/隐藏用例分离**: 交付给被测方的只有 `public`; 判定只用 `hidden`
   ⇒ "把公开用例硬编码" 的解法必然在隐藏用例上暴露 (作弊判据可机检)。
3. **可复现**: 全部随机性由 `--seed` 决定 (stdlib random, 零第三方依赖, 零网络)。
4. **判据语言无关**: 判据 = "输入 → 输出", 与解法语言无关 (题面会提语言要求, 那是任务面)。

用法
----
    python3 eval/probe/tasks.py --kind program --n 4 --seed 7
    python3 eval/probe/tasks.py --kind math    --n 4 --seed 7
    python3 eval/probe/tasks.py --selftest     # 生成器负控 (双路径必须能发现假答案)
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import sys
from dataclasses import dataclass, field, asdict
from fractions import Fraction
from itertools import groupby


# ---------------------------------------------------------------- 数据形态

@dataclass
class Case:
    stdin: str
    expected_stdout: str


@dataclass
class Task:
    tid: str
    kind: str            # program | math
    family: str          # 题族 (归因用: 失败模式要能按族聚合)
    prompt: str
    public: list = field(default_factory=list)
    hidden: list = field(default_factory=list)
    answer: str = ""     # math: 期望最终答案 (严格可解析)
    meta: dict = field(default_factory=dict)

    def to_json(self) -> str:
        d = asdict(self)
        d["public"] = [{"stdin": c.stdin, "expected_stdout": c.expected_stdout} for c in self.public]
        d["hidden"] = [{"stdin": c.stdin, "expected_stdout": c.expected_stdout} for c in self.hidden]
        return json.dumps(d, ensure_ascii=False)


class RefuseToEmit(Exception):
    """两条独立路径不一致 ⇒ 拒绝发题 (宁缺毋滥)。"""


def _dual(f_ref, f_chk, payload):
    a, b = f_ref(payload), f_chk(payload)
    if a != b:
        raise RefuseToEmit("双路径不一致: ref=%r check=%r" % (a, b))
    return a


# ================================================================ 程序题: 参考/校验实现

def _p_max_subarray(nums):
    best = cur = nums[0]
    for x in nums[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best


def _p_max_subarray_bf(nums):
    n = len(nums)
    return max(sum(nums[i:j + 1]) for i in range(n) for j in range(i, n))


def _p_longest_unique(s):
    last, start, best = {}, 0, 0
    for i, ch in enumerate(s):
        if ch in last and last[ch] >= start:
            start = last[ch] + 1
        last[ch] = i
        best = max(best, i - start + 1)
    return best


def _p_longest_unique_bf(s):
    best = 0
    for i in range(len(s)):
        seen = set()
        for j in range(i, len(s)):
            if s[j] in seen:
                break
            seen.add(s[j])
            best = max(best, j - i + 1)
    return best


def _p_bracket_fix(s):
    need_open = need_close = 0
    for ch in s:
        if ch == "(":
            need_open += 1
        elif need_open:
            need_open -= 1
        else:
            need_close += 1
    return need_open + need_close


def _p_bracket_fix_alt(s):
    """独立路径: 栈式 (未匹配的右括号 + 栈内剩余左括号)。"""
    stack, bad = [], 0
    for ch in s:
        if ch == "(":
            stack.append(ch)
        elif stack:
            stack.pop()
        else:
            bad += 1
    return bad + len(stack)


def _p_interval_sum(payload):
    nums, queries = payload
    pref = [0]
    for x in nums:
        pref.append(pref[-1] + x)
    return [pref[r + 1] - pref[l] for l, r in queries]


def _p_interval_sum_bf(payload):
    nums, queries = payload
    return [sum(nums[l:r + 1]) for l, r in queries]


def _p_spiral(mat):
    out, top, bottom, left, right = [], 0, len(mat) - 1, 0, len(mat[0]) - 1
    while top <= bottom and left <= right:
        for c in range(left, right + 1):
            out.append(mat[top][c])
        top += 1
        for r in range(top, bottom + 1):
            out.append(mat[r][right])
        right -= 1
        if top <= bottom:
            for c in range(right, left - 1, -1):
                out.append(mat[bottom][c])
            bottom -= 1
        if left <= right:
            for r in range(bottom, top - 1, -1):
                out.append(mat[r][left])
            left += 1
    return out


def _p_spiral_alt(mat):
    """独立路径: 剥洋葱 (顶行 / 右列 / 底行倒序 / 左列倒序), 与方向步进法独立。"""
    m = [row[:] for row in mat]
    out = []
    while m:
        out.extend(m.pop(0))
        if m and m[0]:
            for row in m:
                out.append(row.pop())
        if m:
            out.extend(reversed(m.pop()))
        if m and m[0]:
            for row in reversed(m):
                out.append(row.pop(0))
    return out


def _p_csv_agg(text):
    agg = {}
    for line in text.strip().splitlines():
        name, val = line.split(",")
        agg[name] = agg.get(name, 0) + int(val)
    return ";".join("%s=%d" % (k, agg[k]) for k in sorted(agg))


def _p_csv_agg_alt(text):
    """独立路径: 先分组成对, 再用 groupby 求和。"""
    pairs = sorted((ln.split(",")[0], int(ln.split(",")[1])) for ln in text.strip().splitlines())
    return ";".join("%s=%d" % (k, sum(v for _, v in grp)) for k, grp in groupby(pairs, key=lambda t: t[0]))


# ---------------------------------------------------------------- 程序题: 输入生成器

def _in_max_subarray(rnd):
    n = rnd.randint(1, 9)
    return "%d\n%s\n" % (n, " ".join(str(rnd.randint(-20, 20)) for _ in range(n)))


def _in_longest_unique(rnd):
    return "".join(rnd.choice("abcde") for _ in range(rnd.randint(1, 14))) + "\n"


def _in_bracket_fix(rnd):
    return "".join(rnd.choice("()") for _ in range(rnd.randint(1, 16))) + "\n"


def _in_interval_sum(rnd):
    n, q = rnd.randint(1, 8), rnd.randint(1, 5)
    nums = [rnd.randint(-50, 50) for _ in range(n)]
    qs = []
    for _ in range(q):
        a, b = rnd.randrange(n), rnd.randrange(n)
        qs.append((min(a, b), max(a, b)))
    return "%d %d\n%s\n%s" % (n, q, " ".join(map(str, nums)),
                              "".join("%d %d\n" % (l, r) for l, r in qs))


def _in_matrix_spiral(rnd):
    R, C = rnd.randint(1, 4), rnd.randint(1, 4)
    rows = [" ".join(str(rnd.randint(0, 99)) for _ in range(C)) for _ in range(R)]
    return "%d %d\n%s\n" % (R, C, "\n".join(rows))


def _in_csv_agg(rnd):
    return "".join("%s,%d\n" % (rnd.choice("ABC"), rnd.randint(1, 9))
                   for _ in range(rnd.randint(1, 8)))


PROGRAM_FAMILIES = {
    "max_subarray": {
        "spec": "读入: 第一行整数 n; 第二行 n 个整数(空格分隔)。输出: 连续子数组的最大和(至少取一个元素)。",
        "ref": lambda s: _p_max_subarray([int(x) for x in s.split()[1:]]),
        "check": lambda s: _p_max_subarray_bf([int(x) for x in s.split()[1:]]),
        "gen_input": _in_max_subarray,
        "fmt": lambda r: "%d" % r,
    },
    "longest_unique": {
        "spec": "读入: 一行不含空格的小写字母串。输出: 最长不含重复字符的子串长度。",
        "ref": _p_longest_unique,
        "check": _p_longest_unique_bf,
        "gen_input": _in_longest_unique,
        "fmt": lambda r: "%d" % r,
    },
    "bracket_fix": {
        "spec": "读入: 一行仅由 '(' 和 ')' 组成的串。输出: 使其平衡所需插入的最少括号数。",
        "ref": _p_bracket_fix,
        "check": _p_bracket_fix_alt,
        "gen_input": _in_bracket_fix,
        "fmt": lambda r: "%d" % r,
    },
    "interval_sum": {
        "spec": "读入: 第一行 n q; 第二行 n 个整数; 随后 q 行每行 l r (0 起闭区间)。输出: 每行一个区间元素和。",
        "ref": _p_interval_sum,
        "check": _p_interval_sum_bf,
        "gen_input": _in_interval_sum,
        "fmt": lambda r: "\n".join(map(str, r)),
        "payload": True,
    },
    "matrix_spiral": {
        "spec": "读入: 第一行 R C; 随后 R 行每行 C 个整数。输出: 螺旋顺序读出的全部元素, 空格分隔为一行。",
        "ref": _p_spiral,
        "check": _p_spiral_alt,
        "gen_input": _in_matrix_spiral,
        "fmt": lambda r: " ".join(map(str, r)),
        "payload": True,
    },
    "csv_agg": {
        "spec": "读入: 多行, 每行形如 组名,数值 (数值为整数, 组名 1 个大写字母)。输出: 一行, 形如 A=3;B=7 (按组名升序, 分号分隔, 无多余空格)。",
        "ref": _p_csv_agg,
        "check": _p_csv_agg_alt,
        "gen_input": _in_csv_agg,
        "fmt": lambda r: r,
    },
}


def _payload_of(fam, stdin_text):
    lines = stdin_text.strip("\n").splitlines()
    if fam == "interval_sum":
        n, q = map(int, lines[0].split())
        nums = [int(x) for x in lines[1].split()]
        queries = [tuple(int(x) for x in ln.split()) for ln in lines[2:2 + q]]
        assert len(nums) == n and len(queries) == q, "题面解析失败: %r" % stdin_text
        return nums, queries
    if fam == "matrix_spiral":
        R, C = map(int, lines[0].split())
        mat = [[int(x) for x in lines[i + 1].split()] for i in range(R)]
        assert all(len(row) == C for row in mat), "题面解析失败: %r" % stdin_text
        return mat
    raise AssertionError("该族不需要 payload: %s" % fam)


def _fam_answer(fam, which, stdin_text):
    f = PROGRAM_FAMILIES[fam]
    if f.get("payload"):
        return f[which](_payload_of(fam, stdin_text))
    return f[which](stdin_text.strip())


# ================================================================ 数学题族

def _m_quad_residue_count(p):
    a, m = p
    return sum(1 for x in range(m) if (x * x - a) % m == 0)


def _m_quad_residue_count_alt(p):
    """独立路径: 用集合 {x² mod m} 的频次表直接查 (与逐点判同余独立)。"""
    a, m = p
    freq = {}
    for x in range(m):
        r = (x * x) % m
        freq[r] = freq.get(r, 0) + 1
    return freq.get(a % m, 0)


def _m_comb_mod(p):
    n, k, mod = p
    return math.comb(n, k) % mod


def _m_comb_mod_alt(p):
    """独立路径: Pascal 递推取模 (与 math.comb 独立)。"""
    n, k, mod = p
    row = [1]
    for _ in range(n):
        row = [1] + [(row[i] + row[i + 1]) % mod for i in range(len(row) - 1)] + [1]
    return row[k]


def _m_det_mod(p):
    mat, mod = p
    n = len(mat)
    a = [[Fraction(x) for x in row] for row in mat]
    det = Fraction(1)
    for i in range(n):
        piv = next((r for r in range(i, n) if a[r][i] != 0), None)
        if piv is None:
            return 0
        if piv != i:
            a[i], a[piv] = a[piv], a[i]
            det = -det
        det *= a[i][i]
        inv = Fraction(1) / a[i][i]
        a[i] = [x * inv for x in a[i]]
        for r in range(i + 1, n):
            f = a[r][i]
            if f != 0:
                a[r] = [a[r][c] - f * a[i][c] for c in range(n)]
    return int(det) % mod


def _m_det_mod_alt(p):
    """独立路径: 按定义对排列展开 (Leibniz), 与高斯消元独立。"""
    mat, mod = p
    n = len(mat)
    total = 0
    for perm in itertools.permutations(range(n)):
        inv = sum(1 for i in range(n) for j in range(i + 1, n) if perm[i] > perm[j])
        term = 1
        for i in range(n):
            term *= mat[i][perm[i]]
        total += -term if inv % 2 else term
    return total % mod


def _m_shortest_path(p):
    w, s, t, n = p
    dist, done = [math.inf] * n, [False] * n
    dist[s] = 0
    for _ in range(n):
        cands = [i for i in range(n) if not done[i]]
        u = min(cands, key=lambda i: dist[i]) if cands else None
        if u is None or dist[u] == math.inf:
            break
        done[u] = True
        for v in range(n):
            if w[u][v] > 0 and dist[u] + w[u][v] < dist[v]:
                dist[v] = dist[u] + w[u][v]
    return dist[t]


def _m_shortest_path_alt(p):
    """独立路径: Bellman-Ford 松弛 (与 Dijkstra 不同算法族)。"""
    w, s, t, n = p
    dist = [math.inf] * n
    dist[s] = 0
    for _ in range(n - 1):
        for u in range(n):
            for v in range(n):
                if w[u][v] > 0 and dist[u] + w[u][v] < dist[v]:
                    dist[v] = dist[u] + w[u][v]
    return dist[t]


def _m_expectation(p):
    r, b, d = p
    return Fraction(d * r, r + b)


def _m_expectation_alt(p):
    """独立路径: 指示变量之和的逐项精确期望 (与线性期望公式独立)。"""
    r, b, d = p
    total = r + b
    return sum(Fraction(1, total) for _ in range(r)) * d


def _fill_matrix(rnd, n):
    return [[rnd.randint(-6, 6) for _ in range(n)] for _ in range(n)]


def _fill_graph(rnd, n):
    w = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if rnd.random() < 0.55:
                x = rnd.randint(1, 9)
                w[i][j] = w[j][i] = x
    return w


MATH_FAMILIES = {
    "quadratic_residue_count": {
        "gen": lambda rnd: (rnd.randrange(0, 13), rnd.choice([8, 9, 10, 12, 15, 16])),
        "ref": _m_quad_residue_count, "check": _m_quad_residue_count_alt,
        "spec": lambda p: "求同余方程 x^2 ≡ %d (mod %d) 在 0 <= x < %d 内的整数解个数。" % (p[0], p[1], p[1]),
        "fmt": lambda p, r: "%d" % r,
    },
    "comb_mod": {
        "gen": lambda rnd: (lambda n: (n, rnd.randint(0, n), rnd.choice([97, 101, 1000003])))(rnd.randint(0, 40)),
        "ref": _m_comb_mod, "check": _m_comb_mod_alt,
        "spec": lambda p: "求组合数 C(%d, %d) mod %d 的值。" % (p[0], p[1], p[2]),
        "fmt": lambda p, r: "%d" % r,
    },
    "det_mod": {
        "gen": lambda rnd: (lambda n: (_fill_matrix(rnd, n), rnd.choice([97, 101])))(rnd.randint(2, 4)),
        "ref": _m_det_mod, "check": _m_det_mod_alt,
        "spec": lambda p: "给定下面的 %dx%d 整数矩阵, 求其行列式 mod %d 的非负余数 (0..%d)。" % (
            len(p[0]), len(p[0]), p[1], p[1] - 1),
        "fmt": lambda p, r: "%d" % r,
        "attach_matrix": True,
    },
    "shortest_path": {
        "gen": lambda rnd: (lambda n: (_fill_graph(rnd, n), 0, n - 1, n))(rnd.randint(4, 7)),
        "ref": _m_shortest_path, "check": _m_shortest_path_alt,
        "spec": lambda p: "给定 %d 个结点的带权无向图邻接矩阵 (0 = 无边, 对称), 求结点 %d 到结点 %d 的最短路径长度; 若不可达请回答 -1。" % (
            p[3], p[1], p[2]),
        "fmt": lambda p, r: "-1" if r == math.inf else "%d" % r,
        "attach_matrix": True,
    },
    "expectation_urn": {
        "gen": lambda rnd: (lambda r, b: (r, b, rnd.randint(1, r + b)))(rnd.randint(1, 6), rnd.randint(1, 6)),
        "ref": _m_expectation, "check": _m_expectation_alt,
        "spec": lambda p: "袋中有 %d 个红球与 %d 个蓝球, 不放回地抽出 %d 个。求抽出红球个数的数学期望, 以最简分数 p/q 形式给出 (例如 3/2)。" % p,
        "fmt": lambda p, r: "%d/%d" % (r.numerator, r.denominator),
    },
}


def _render_math(fam, params):
    f = MATH_FAMILIES[fam]
    spec = f["spec"](params)
    if f.get("attach_matrix"):
        if fam == "det_mod":
            body = "\n".join(" ".join(str(x) for x in row) for row in params[0])
            head = "矩阵数据:"
        else:
            body = "\n".join(" ".join(str(x) for x in row) for row in params[0])
            head = "邻接矩阵 (第 i 行第 j 列 = i 到 j 的边权):"
        return "%s\n\n%s\n%s\n\n请直接给出最终答案, 最后一行必须是 `FINAL: <答案>` 格式。" % (spec, head, body)
    return "%s\n\n请直接给出最终答案, 最后一行必须是 `FINAL: <答案>` 格式。" % spec


def gen_math_task(idx, families, rnd):
    fam = rnd.choice(families)
    f = MATH_FAMILIES[fam]
    params = f["gen"](rnd)
    expected = _dual(f["ref"], f["check"], params)
    return Task(tid="m%03d" % idx, kind="math", family=fam, prompt=_render_math(fam, params),
                answer=f["fmt"](params, expected), meta={"params_len": len(str(params))})


def gen_program_task(idx, families, rnd, n_public=2, n_hidden=6):
    fam = rnd.choice(families)
    f = PROGRAM_FAMILIES[fam]
    cases, seen = [], set()
    for _ in range((n_public + n_hidden) * 4):
        if len(cases) >= n_public + n_hidden:
            break
        stdin_text = f["gen_input"](rnd)
        if stdin_text in seen:
            continue
        seen.add(stdin_text)
        expected = _dual(lambda s: _fam_answer(fam, "ref", s), lambda s: _fam_answer(fam, "check", s), stdin_text)
        cases.append(Case(stdin_text, f["fmt"](expected)))
    if len(cases) < n_public + n_hidden:
        raise RefuseToEmit("用例去重后不足: %s (%d)" % (fam, len(cases)))
    prompt = (
        "用 Python 3 写一个单文件程序解决下面的任务。程序从标准输入读数据, 把结果写到标准输出; "
        "不要打印任何多余文字、提示或调试信息。\n\n"
        "【任务】\n%s\n\n"
        "【公开用例】(仅供参考; 判定使用另一批隐藏用例)\n%s\n\n"
        "请把完整程序放在一个 ```python 围栏代码块内。"
        % (f["spec"], "\n\n".join("输入:\n%s期望输出:\n%s" % (c.stdin, c.expected_stdout)
                                  for c in cases[:n_public]))
    )
    return Task(tid="p%03d" % idx, kind="program", family=fam, prompt=prompt,
                public=cases[:n_public], hidden=cases[n_public:])


# ---------------------------------------------------------------- 自检负控

def selftest() -> int:
    ok, fails = 0, []

    def chk(name, cond, detail=""):
        nonlocal ok
        if cond:
            ok += 1
            print("  [PASS] %s %s" % (name, detail))
        else:
            fails.append(name)
            print("  [FAIL] %s %s" % (name, detail))

    print("selftest: 生成器负控")
    rnd = random.Random(20260913)

    try:
        t = gen_program_task(1, ["max_subarray"], rnd, n_public=1, n_hidden=2)
        chk("双路径一致时可发题", len(t.hidden) == 2)
    except RefuseToEmit as e:
        chk("双路径一致时可发题", False, str(e))

    for fam in sorted(PROGRAM_FAMILIES):
        try:
            t = gen_program_task(2, [fam], random.Random(1000 + len(fam)), n_public=1, n_hidden=3)
            chk("program 族双路径一致:%s" % fam, len(t.hidden) == 3)
        except RefuseToEmit as e:
            chk("program 族双路径一致:%s" % fam, False, str(e))

    orig = PROGRAM_FAMILIES["max_subarray"]["ref"]
    PROGRAM_FAMILIES["max_subarray"]["ref"] = lambda s: _p_max_subarray([int(x) for x in s.split()[1:]]) + 1
    try:
        gen_program_task(3, ["max_subarray"], random.Random(1), n_public=1, n_hidden=2)
        chk("program 假答案拒绝发题", False, "竟然发题了")
    except RefuseToEmit:
        chk("program 假答案拒绝发题", True)
    finally:
        PROGRAM_FAMILIES["max_subarray"]["ref"] = orig

    for fam, f in sorted(MATH_FAMILIES.items()):
        try:
            t = gen_math_task(4, [fam], random.Random(abs(hash(fam)) % 9973))
            chk("math 族双路径一致:%s" % fam, t.answer != "")
        except RefuseToEmit as e:
            chk("math 族双路径一致:%s" % fam, False, str(e))

    f = MATH_FAMILIES["comb_mod"]
    orig_c = f["check"]
    f["check"] = lambda p: _m_comb_mod_alt(p) + 1
    try:
        gen_math_task(5, ["comb_mod"], random.Random(5))
        chk("math 假答案拒绝发题", False, "竟然发题了")
    except RefuseToEmit:
        chk("math 假答案拒绝发题", True)
    finally:
        f["check"] = orig_c

    t = gen_program_task(6, ["interval_sum"], random.Random(9), n_public=2, n_hidden=4)
    chk("公开/隐藏用例不重叠", not ({c.stdin for c in t.public} & {c.stdin for c in t.hidden}),
        "pub=%d hid=%d" % (len(t.public), len(t.hidden)))

    for fam in sorted(MATH_FAMILIES):
        ans = gen_math_task(7, [fam], random.Random(11)).answer
        okfmt = ("/" in ans and all(x.lstrip("-").isdigit() for x in ans.split("/"))) or ans.lstrip("-").isdigit()
        chk("math 答案可解析:%s" % fam, okfmt, repr(ans))

    chk("同种子同题",
        gen_program_task(8, ["csv_agg"], random.Random(42), 1, 2).to_json()
        == gen_program_task(8, ["csv_agg"], random.Random(42), 1, 2).to_json())

    print("selftest %d/%d" % (ok, ok + len(fails)))
    return 0 if not fails else 1


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["program", "math"], default="program")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    rnd = random.Random(a.seed)
    tasks = []
    if a.kind == "program":
        fams = sorted(PROGRAM_FAMILIES)
        for i in range(1, a.n + 1):
            tasks.append(gen_program_task(i, fams, rnd))
    else:
        fams = sorted(MATH_FAMILIES)
        for i in range(1, a.n + 1):
            tasks.append(gen_math_task(i, fams, rnd))

    blob = "[\n" + ",\n".join(t.to_json() for t in tasks) + "\n]\n"
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(blob)
        print("wrote %s (%d 题)" % (a.out, len(tasks)))
    else:
        sys.stdout.write(blob)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
