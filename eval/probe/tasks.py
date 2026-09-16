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


def _p_pair_closest(nums):
    best, bkey = None, None
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            s = nums[i] + nums[j]
            key = (abs(s), s)
            if bkey is None or key < bkey:
                best, bkey = s, key
    return best


def _p_pair_closest_alt(nums):
    import itertools
    sums = [a + b for a, b in itertools.combinations(nums, 2)]
    return min(sums, key=lambda s: (abs(s), s))


def _in_pair_closest(rnd):
    n = rnd.randint(2, 7)
    if rnd.random() < 0.35:
        pool = rnd.sample(range(-9, 10), rnd.randint(2, 4))
        vals = [rnd.choice(pool) for _ in range(n)]
    else:
        vals = [rnd.randint(-12, 12) for _ in range(n)]
    return "%d\n%s\n" % (n, " ".join(map(str, vals)))


# ---------------------------------------------------------------- 反饱和族 v2 (R417)
# json_mini: 严格 JSON 规范化器。规格密度高 (转义 / uXXXX 解码 / 键码点序 / 重复键覆盖 / 严格错误)。
# 公开样例推不出隐藏判据 ⇒ 只有真正实现完整规格才可能整题全对。

BS = chr(92)
TAB = chr(9)
NL = chr(10)
_ERR = object()


def _jnorm(v):
    """规范化输出 (无空白)。"""
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return "%d" % v
    if isinstance(v, str):
        out = ['"']
        for ch in v:
            if ch == '"':
                out.append(BS + '"')
            elif ch == BS:
                out.append(BS + BS)
            elif ch == NL:
                out.append(BS + "n")
            elif ch == TAB:
                out.append(BS + "t")
            else:
                out.append(ch)
        out.append('"')
        return "".join(out)
    if isinstance(v, list):
        return "[" + ",".join(_jnorm(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ",".join(_jnorm(k) + ":" + _jnorm(v[k]) for k in sorted(v)) + "}"
    return "!"


def _p_json_mini_ref(s):
    """递归下降 (字符级) 解析 + 规范化; 非法输入 ⇒ _ERR。"""
    i = [0]
    n = len(s)
    digits = "0123456789"
    hexd = "0123456789abcdefABCDEF"

    def ws():
        while i[0] < n and s[i[0]] in " \t\r\n":
            i[0] += 1

    def fail():
        raise ValueError("bad")

    def pstr():
        i[0] += 1
        buf = []
        while True:
            if i[0] >= n:
                fail()
            c = s[i[0]]
            if c == '"':
                i[0] += 1
                return "".join(buf)
            if c == BS:
                i[0] += 1
                if i[0] >= n:
                    fail()
                e = s[i[0]]
                if e == "u":
                    h = s[i[0] + 1:i[0] + 5]
                    if len(h) != 4 or any(x not in hexd for x in h):
                        fail()
                    cp = int(h, 16)
                    if cp < 0x20:
                        fail()
                    buf.append(chr(cp))
                    i[0] += 4
                elif e == '"':
                    buf.append('"')
                elif e == BS:
                    buf.append(BS)
                elif e == "/":
                    buf.append("/")
                elif e == "n":
                    buf.append(NL)
                elif e == "t":
                    buf.append(TAB)
                else:
                    fail()
                i[0] += 1
            elif ord(c) < 0x20:
                fail()
            else:
                buf.append(c)
                i[0] += 1

    def pnum():
        st = i[0]
        j = st
        if j < n and s[j] == "-":
            j += 1
        if j >= n or s[j] not in digits:
            fail()
        if s[j] == "0":
            j += 1
        else:
            while j < n and s[j] in digits:
                j += 1
        i[0] = j
        return int(s[st:j])

    def pval():
        ws()
        if i[0] >= n:
            fail()
        c = s[i[0]]
        if c == "{":
            return pobj()
        if c == "[":
            return parr()
        if c == '"':
            return pstr()
        for lit, val in (("null", None), ("true", True), ("false", False)):
            if s.startswith(lit, i[0]):
                i[0] += len(lit)
                return val
        return pnum()

    def parr():
        i[0] += 1
        out = []
        ws()
        if i[0] < n and s[i[0]] == "]":
            i[0] += 1
            return out
        while True:
            out.append(pval())
            ws()
            if i[0] >= n:
                fail()
            c = s[i[0]]
            i[0] += 1
            if c == "]":
                return out
            if c != ",":
                fail()

    def pobj():
        i[0] += 1
        d = {}
        ws()
        if i[0] < n and s[i[0]] == "}":
            i[0] += 1
            return d
        while True:
            ws()
            if i[0] >= n or s[i[0]] != '"':
                fail()
            k = pstr()
            ws()
            if i[0] >= n or s[i[0]] != ":":
                fail()
            i[0] += 1
            d[k] = pval()
            ws()
            if i[0] >= n:
                fail()
            c = s[i[0]]
            i[0] += 1
            if c == "}":
                return d
            if c != ",":
                fail()

    try:
        v = pval()
        ws()
        if i[0] != n:
            return _ERR
        return v
    except (ValueError, IndexError):
        return _ERR


def _p_json_mini_check(s):
    """独立路径: 先手工词法切分, 再在 token 流上递归下降 (与字符级实现不同)。"""
    toks = []
    i = 0
    n = len(s)
    digits = "0123456789"
    hexd = "0123456789abcdefABCDEF"
    while i < n:
        c = s[i]
        if c in " \t\r\n":
            i += 1
        elif c == '"':
            i += 1
            buf = []
            closed = False
            while i < n:
                ch = s[i]
                if ch == '"':
                    i += 1
                    closed = True
                    break
                if ch == BS:
                    i += 1
                    if i >= n:
                        break
                    e = s[i]
                    if e == "u":
                        h = s[i + 1:i + 5]
                        if len(h) != 4 or any(x not in hexd for x in h):
                            return _ERR
                        cp = int(h, 16)
                        if cp < 0x20:
                            return _ERR
                        buf.append(chr(cp))
                        i += 5
                        continue
                    mp = {'"': '"', BS: BS, "/": "/", "n": NL, "t": TAB}
                    if e not in mp:
                        return _ERR
                    buf.append(mp[e])
                    i += 1
                    continue
                if ord(ch) < 0x20:
                    return _ERR
                buf.append(ch)
                i += 1
            if not closed:
                return _ERR
            toks.append(("str", "".join(buf)))
        elif c == "-" or c in digits:
            st = i
            if c == "-":
                i += 1
            if i >= n or s[i] not in digits:
                return _ERR
            if s[i] == "0":
                i += 1
            else:
                while i < n and s[i] in digits:
                    i += 1
            toks.append(("num", int(s[st:i])))
        elif s.startswith("true", i):
            toks.append(("bool", True))
            i += 4
        elif s.startswith("false", i):
            toks.append(("bool", False))
            i += 5
        elif s.startswith("null", i):
            toks.append(("nul", None))
            i += 4
        elif c in "{}[],:":
            toks.append(("punc", c))
            i += 1
        else:
            return _ERR

    ti = [0]

    def peek():
        return toks[ti[0]] if ti[0] < len(toks) else None

    def take(kind=None):
        t = peek()
        if t is None or (kind is not None and t[0] != kind):
            raise ValueError("take")
        ti[0] += 1
        return t

    def val():
        t = peek()
        if t is None:
            raise ValueError("eof")
        if t[0] in ("str", "num", "bool", "nul"):
            ti[0] += 1
            return t[1]
        if t[1] == "[":
            return arr()
        if t[1] == "{":
            return obj()
        raise ValueError("val")

    def arr():
        take("punc")
        out = []
        if peek() == ("punc", "]"):
            ti[0] += 1
            return out
        while True:
            out.append(val())
            t = take("punc")
            if t[1] == "]":
                return out
            if t[1] != ",":
                raise ValueError("arr")

    def obj():
        take("punc")
        d = {}
        if peek() == ("punc", "}"):
            ti[0] += 1
            return d
        while True:
            k = take("str")
            c = take("punc")
            if c[1] != ":":
                raise ValueError("colon")
            d[k[1]] = val()
            t = take("punc")
            if t[1] == "}":
                return d
            if t[1] != ",":
                raise ValueError("obj")

    try:
        v = val()
        if ti[0] != len(toks):
            return _ERR
        return v
    except (ValueError, IndexError):
        return _ERR


_JCHARS = "abzXY019 _-/:中é"
_JTRICK = ['"', BS, "/", NL, TAB]


def _jrand_str(rnd):
    out = []
    for _ in range(rnd.randint(0, 4)):
        out.append(rnd.choice(_JTRICK) if rnd.random() < 0.4 else rnd.choice(_JCHARS))
    return "".join(out)


def _jrand_val(rnd, depth):
    if depth > 0 and rnd.random() < 0.55:
        if rnd.random() < 0.5:
            return [_jrand_val(rnd, depth - 1) for _ in range(rnd.randint(1, 3))]
        pairs = []
        for _ in range(rnd.randint(1, 3)):
            pairs.append((_jrand_str(rnd), _jrand_val(rnd, depth - 1)))
        if rnd.random() < 0.35:
            pairs.append((pairs[0][0], _jrand_val(rnd, depth - 1)))
        return ("obj", pairs)
    k = rnd.choice(["nul", "bool", "int", "int", "str", "str"])
    if k == "nul":
        return None
    if k == "bool":
        return rnd.random() < 0.5
    if k == "int":
        return rnd.randint(-99, 99)
    return _jrand_str(rnd)


def _jws(rnd):
    return rnd.choice(["", "", " ", NL, "  ", NL + " "])


def _jser_str(s, rnd):
    out = ['"']
    for ch in s:
        if ch == '"':
            out.append(BS + '"')
        elif ch == BS:
            out.append(BS + BS)
        elif ch == NL:
            out.append(BS + "n")
        elif ch == TAB:
            out.append(BS + "t")
        elif ch == "/":
            out.append(rnd.choice(["/", BS + "/"]))
        elif rnd.random() < 0.25:
            out.append(BS + "u%04x" % ord(ch))
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _jser(v, rnd):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return "%d" % v
    if isinstance(v, str):
        return _jser_str(v, rnd)
    if isinstance(v, list):
        return "[" + _jws(rnd) + (("," + _jws(rnd)).join(_jser(x, rnd) for x in v)) + _jws(rnd) + "]"
    pairs = v[1]
    items = [_jser_str(k, rnd) + _jws(rnd) + ":" + _jws(rnd) + _jser(x, rnd) for k, x in pairs]
    return "{" + _jws(rnd) + (("," + _jws(rnd)).join(items)) + _jws(rnd) + "}"


def _jcorrupt(t, rnd):
    k = rnd.randrange(6)
    if k == 0:
        return t[:-1]
    if k == 1:
        return t + " x"
    if k == 2:
        return t.replace(",", " ,, ", 1)
    if k == 3:
        return "[" + t
    if k == 4:
        return t.replace('"', BS + "x", 1)
    return "01" + t


def _jtight(rnd):
    """规格紧用例: 合法 JSON 但**违反本规格** ⇒ 期望 ERR。用于确定性区分"通用 JSON 库套用"式解法。"""
    k = rnd.randrange(4)
    if k == 0:
        return '["' + BS + "u000" + rnd.choice("0123456789abcdef") + 'x"]'
    if k == 1:
        return "[" + rnd.choice(["1.5", "-0.25", "1e3"]) + "]"
    if k == 2:
        return "[" + rnd.choice(["NaN", "Infinity", "-Infinity"]) + "]"
    return '["a' + TAB + 'b"]'


def _in_json_mini(rnd):
    r = rnd.random()
    if r < 0.3:
        t = _jser(_jrand_val(rnd, 3), rnd)
    elif r < 0.75:
        t = _jcorrupt(_jser(_jrand_val(rnd, 3), rnd), rnd)
    else:
        t = _jtight(rnd)
    return t + NL


# ---------------------------------------------------------------- 反饱和族 (R417)
# 背景: 原 7 族对当前链已饱和 (agent 与 oracle 同为 rate=1.0 = 天花板效应) ⇒ 无法度量质量。
# 这两族的公开样例**推不出**隐藏判据 (字典序最小 / 栈机错误语义), 必须真正实现规格才能整题全对。
# 注意: 本族输入一律用 _nl() 拼行, 不用转义字面量 (写入工具会污染特定字符序列)。

def _nl(lines):
    return NL.join(lines) + NL


def _p_topo_min_ref(s):
    """Kahn + 最小堆 = 字典序最小拓扑序; 有环/自环 ⇒ None。"""
    import heapq
    d = s.split()
    n, m = int(d[0]), int(d[1])
    adj = [[] for _ in range(n)]
    deg = [0] * n
    i = 2
    for _ in range(m):
        u, v = int(d[i]), int(d[i + 1])
        i += 2
        adj[u].append(v)
        deg[v] += 1
    h = [x for x in range(n) if deg[x] == 0]
    heapq.heapify(h)
    out = []
    while h:
        u = heapq.heappop(h)
        out.append(u)
        for v in adj[u]:
            deg[v] -= 1
            if deg[v] == 0:
                heapq.heappush(h, v)
    return out if len(out) == n else None


def _p_topo_min_check(s):
    """独立路径: 每步线性扫描剩余节点中最小入度 0 者 (O(n^2), 与堆/邻接表独立)。"""
    d = s.split()
    n, m = int(d[0]), int(d[1])
    edges = []
    i = 2
    for _ in range(m):
        edges.append((int(d[i]), int(d[i + 1])))
        i += 2
    left = set(range(n))
    out = []
    while left:
        pick = None
        for u in sorted(left):
            blocked = False
            for (v, w) in edges:
                if w == u and v in left:
                    blocked = True
                    break
            if not blocked:
                pick = u
                break
        if pick is None:
            return None
        out.append(pick)
        left.discard(pick)
    return out


def _in_topo_min(rnd):
    n = rnd.randint(2, 7)
    style = rnd.random()
    if style < 0.3:                     # 汇点收口: 存在多个合法序, 字典序最小非平凡
        edges = [(i, n - 1) for i in range(n - 1)]
    elif style < 0.45:                  # 制造环 (含自环可能)
        edges = [(rnd.randrange(n), rnd.randrange(n)) for _ in range(rnd.randint(1, 3))]
        edges.append((n - 1, 0))
    else:
        edges = [(rnd.randrange(n), rnd.randrange(n)) for _ in range(rnd.randint(0, n + 2))]
    return _nl(["%d %d" % (n, len(edges))] + ["%d %d" % e for e in edges])


def _vm_valid_body(rnd):
    """构造**确定合法**的栈机程序 (整题全对要求: 错解不能靠"一律 ERR"过关)。"""
    a, b = rnd.randint(-5, 5), rnd.randint(-5, 5)
    kind = rnd.randrange(7)
    if kind == 0:
        body = ["PUSH %d" % a, "PUSH %d" % b, "ADD", "PRINT", "HALT"]
    elif kind == 1:
        body = ["PUSH %d" % a, "PUSH %d" % b, "MUL", "PRINT", "HALT"]
    elif kind == 2:
        body = ["PUSH %d" % a, "PUSH %d" % b, "SUB", "PRINT", "HALT"]
    elif kind == 3:
        body = ["PUSH %d" % a, "DUP", "ADD", "PRINT", "HALT"]
    elif kind == 4:
        body = ["PUSH %d" % a, "PUSH %d" % b, "SWAP", "SUB", "PRINT", "HALT"]
    elif kind == 5:
        body = ["PUSH %d" % a, "PRINT", "PUSH %d" % b, "PRINT", "HALT"]
    else:
        n = rnd.randint(1, 4)           # 倒计数循环: 打印 n, n-1, ..., 1
        body = ["PUSH %d" % n, "DUP", "PRINT", "PUSH 1", "SUB", "DUP", "JNZ 1", "POP", "HALT"]
    if kind < 6:                        # 无跳转模板可插无害 PUSH/POP 对 (打散"照抄公开样例"式解法)
        for _ in range(rnd.randint(0, 2)):
            pos = rnd.randint(0, len(body) - 2)
            body = body[:pos] + ["PUSH %d" % rnd.randint(-3, 3), "POP"] + body[pos:]
    return body


def _vm_err_body(rnd):
    """构造必须判 ERR 的程序: 栈下溢 / 操作数不足 / 跳转越界 / 无 HALT / 步数上限。"""
    kind = rnd.randrange(6)
    if kind == 0:
        return ["POP", "HALT"]
    if kind == 1:
        return ["PUSH %d" % rnd.randint(-3, 3), "ADD", "HALT"]
    if kind == 2:
        return ["PUSH 1", "JNZ 99", "HALT"]
    if kind == 3:
        return ["PUSH %d" % rnd.randint(-3, 3)]
    if kind == 4:
        return ["PUSH 1", "PUSH 2", "SWAP", "SWAP", "POP", "POP", "POP", "HALT"]
    return ["PUSH %d" % rnd.randint(1, 3), "JNZ 0", "HALT"]


def _in_vm_run(rnd):
    body = _vm_err_body(rnd) if rnd.random() < 0.3 else _vm_valid_body(rnd)
    return _nl(["%d" % len(body)] + body)


def _p_vm_run_ref(s):
    """参考路径: 列表当栈 + 显式逐指令分支; 任何非法态 ⇒ None (答案格式化为 ERR)。"""
    L = s.strip().splitlines()
    k = int(L[0].split()[0])
    prog = [ln.split() for ln in L[1:1 + k]]
    st = []
    pc = 0
    out = []
    steps = 0
    while True:
        if pc < 0 or pc >= k:
            return None
        steps += 1
        if steps > 10000:
            return None
        op, arg = prog[pc][0], prog[pc][1:]
        pc += 1
        if op == "PUSH":
            st.append(int(arg[0]))
        elif op == "POP":
            if not st:
                return None
            st.pop()
        elif op in ("ADD", "SUB", "MUL"):
            if len(st) < 2:
                return None
            a2 = st.pop()
            b2 = st.pop()
            st.append(b2 + a2 if op == "ADD" else (b2 - a2 if op == "SUB" else b2 * a2))
        elif op == "DUP":
            if not st:
                return None
            st.append(st[-1])
        elif op == "SWAP":
            if len(st) < 2:
                return None
            st[-1], st[-2] = st[-2], st[-1]
        elif op == "PRINT":
            if not st:
                return None
            out.append(st.pop())
        elif op == "JNZ":
            if not st:
                return None
            v = st.pop()
            t = int(arg[0])
            if t < 0 or t >= k:
                return None
            if v != 0:
                pc = t
        elif op == "HALT":
            return out
        else:
            return None


def _p_vm_run_check(s):
    """独立路径: 预分配栈数组 + 指针 (无 append/pop) + 倒计数步数上限。"""
    it = iter(s.strip().splitlines())
    try:
        k = int(next(it).split()[0])
    except (StopIteration, ValueError):
        return None
    prog = []
    for _ in range(k):
        try:
            prog.append(next(it).split())
        except StopIteration:
            return None
    st = [0] * 10050
    sp = 0
    out = []
    pc = 0
    budget = 10000
    while budget > 0:
        budget -= 1
        if not (0 <= pc < k):
            return None
        op = prog[pc][0]
        arg = prog[pc][1:]
        nxt = pc + 1
        if op == "PUSH":
            if sp >= len(st):
                return None
            st[sp] = int(arg[0])
            sp += 1
        elif op == "POP":
            if sp < 1:
                return None
            sp -= 1
        elif op in ("ADD", "SUB", "MUL"):
            if sp < 2:
                return None
            a2 = st[sp - 1]
            b2 = st[sp - 2]
            sp -= 2
            st[sp] = b2 + a2 if op == "ADD" else (b2 - a2 if op == "SUB" else b2 * a2)
            sp += 1
        elif op == "DUP":
            if sp < 1 or sp >= len(st):
                return None
            st[sp] = st[sp - 1]
            sp += 1
        elif op == "SWAP":
            if sp < 2:
                return None
            st[sp - 1], st[sp - 2] = st[sp - 2], st[sp - 1]
        elif op == "PRINT":
            if sp < 1:
                return None
            sp -= 1
            out.append(st[sp])
        elif op == "JNZ":
            if sp < 1:
                return None
            sp -= 1
            t = int(arg[0])
            if t < 0 or t >= k:
                return None
            if st[sp] != 0:
                nxt = t
        elif op == "HALT":
            return out
        else:
            return None
        pc = nxt
    return None


# life_k: 生命游戏 (Conway) 第 k 代 —— **游戏族** (主线「随机游戏」面)。
# 高密度规格: 8 邻域 / 同时更新 / 网格外一律视为死 (与 life_wrap 变异互为判别面)。
def _life_parse(s):
    lines = [ln for ln in s.strip(chr(10)).splitlines() if ln != ""]
    h, w, k = map(int, lines[0].split())
    grid = [list(ln) for ln in lines[1:1 + h]]
    assert len(grid) == h and all(len(r) == w for r in grid), "题面解析失败: %r" % s
    return grid, k


def _life_nbr(grid, i, j):
    h, w = len(grid), len(grid[0])
    n = 0
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == 0 and dj == 0:
                continue
            x, y = i + di, j + dj
            if 0 <= x < h and 0 <= y < w and grid[x][y] == "#":
                n += 1
    return n


def _p_life_k_ref(s):
    grid, k = _life_parse(s)
    for _ in range(k):
        grid = [["#" if (_life_nbr(grid, i, j) == 3 or (grid[i][j] == "#" and _life_nbr(grid, i, j) == 2)) else "."
                 for j in range(len(grid[0]))] for i in range(len(grid))]
    return NL.join("".join(r) for r in grid)


def _p_life_k_check(s):
    """独立实现 (显式 padding 边界 + 单次邻域计数) ⇒ 与 ref 双路径互证。"""
    grid, k = _life_parse(s)
    for _ in range(k):
        h, w = len(grid), len(grid[0])
        pad = [list("." * (w + 2))]
        for r in grid:
            pad.append(["."] + list(r) + ["."])
        pad.append(list("." * (w + 2)))
        nxt = []
        for i in range(h):
            row = []
            for j in range(w):
                c = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if (di != 0 or dj != 0) and pad[i + 1 + di][j + 1 + dj] == "#":
                            c += 1
                alive = pad[i + 1][j + 1] == "#"
                row.append("#" if (c == 3 or (alive and c == 2)) else ".")
            nxt.append(row)
        grid = nxt
    return NL.join("".join(r) for r in grid)


def _in_life_k(rnd):
    h = rnd.randint(1, 12)
    w = rnd.randint(1, 12)
    k = rnd.randint(0, 8)
    dens = rnd.choice([0.15, 0.3, 0.45, 0.6])
    rows = ["".join("#" if rnd.random() < dens else "." for _ in range(w)) for _ in range(h)]
    return _nl(["%d %d %d" % (h, w, k)] + rows)


# ---- sub_game (游戏族之二: 减法博弈; R503 扩面, 与 life_k 并列) ----
def _sub_game_parse(s):
    lines = s.strip().splitlines()
    n, k = (int(x) for x in lines[0].split())
    ss = [int(x) for x in lines[1].split()]
    assert k == len(ss) and len(set(ss)) == k and all(1 <= x <= 12 for x in ss), "题面解析失败: %r" % s
    assert 1 in ss and 1 <= n <= 80, "题面不合法(须含取 1): %r" % s
    return n, sorted(ss)


def _p_sub_game_ref(s):
    """正推 DP: win[i] = 存在允许的取 t 使得对手在 i-t 是败态。"""
    n, ss = _sub_game_parse(s)
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(not win[i - t] for t in ss if t <= i)
    if not win[n]:
        return None
    return min(t for t in ss if t <= n and not win[n - t])


def _p_sub_game_check(s):
    """独立实现: 记忆化递归极小极大 (自顶向下), 并对返回手做合法性与语义复核。"""
    n, ss = _sub_game_parse(s)
    memo = {}

    def f(i):
        if i == 0:
            return False          # 轮到走者无子可取 ⇒ 败 (含 1 的集合下不会发生, 保留为语义锚)
        if i not in memo:
            memo[i] = any(not f(i - t) for t in ss if t <= i)
        return memo[i]

    if not f(n):
        return None
    cand = [t for t in ss if t <= n and not f(n - t)]
    assert cand, "check: 必胜态必须存在必胜手"
    m = min(cand)
    assert m in ss and 1 <= m <= n, "check: 手非法"
    assert not f(n - m), "check: 该手未把对手置于败态"
    return m


def _in_sub_game(rnd):
    k = rnd.randint(1, 4)
    ss = sorted([1] + rnd.sample([x for x in range(2, 13)], k - 1)) if k > 1 else [1]
    return _nl(["%d %d" % (rnd.randint(1, 80), k), " ".join(str(x) for x in ss)])


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
    "pair_closest_abs_sum": {
        "spec": "读入: 第一行整数 n (n>=2); 第二行 n 个整数。输出: 在所有下标 i<j 的两数之和中, 绝对值最小的那个和; 若并列取数值最小者。",
        "ref": lambda s: _p_pair_closest([int(x) for x in s.split()[1:]]),
        "check": lambda s: _p_pair_closest_alt([int(x) for x in s.split()[1:]]),
        "gen_input": _in_pair_closest,
        "fmt": lambda r: "%d" % r,
    },
    "topo_min": {
        "spec": "读入: 第一行两个整数 n m (1<=n<=64); 随后 m 行, 每行两个整数 u v (0<=u,v<n), 表示有向边 u->v。输出: 若图中存在拓扑序, 输出**字典序最小**的拓扑序 (n 个节点编号, 空格分隔为一行); 若存在环(含自环), 输出 -1。",
        "ref": _p_topo_min_ref,
        "check": _p_topo_min_check,
        "gen_input": _in_topo_min,
        "fmt": lambda r: "-1" if r is None else " ".join("%d" % x for x in r),
    },
    "vm_run": {
        "spec": "读入: 第一行整数 k (1<=k<=64, 指令条数); 随后 k 行, 每行一条指令 (地址从 0 开始)。指令集: PUSH n(压入整数 n) / POP(弹出丢弃) / ADD / SUB / MUL(弹出 a=栈顶, b=次顶, 压入 b-a 等运算) / DUP(复制栈顶) / SWAP(交换栈顶两元素) / PRINT(弹出栈顶并输出一行) / JNZ a(弹出栈顶, 非 0 则跳转到地址 a, 否则继续) / HALT(结束)。输出: 按 PRINT 顺序逐行输出整数。若出现栈空弹栈、操作数不足、跳转地址越界、未在 10000 步内执行 HALT, 或执行流越过最后一条指令, 则只输出一行 ERR。",
        "ref": _p_vm_run_ref,
        "check": _p_vm_run_check,
        "gen_input": _in_vm_run,
        "fmt": lambda r: "ERR" if r is None else NL.join("%d" % x for x in r),
    },
    "json_mini": {
        "spec": ("读入: STDIN 整体为一个 JSON 值 (可含前后空白与换行)。支持 null / true / false / 十进制整数"
                 "(可选负号; 不允许前导零, 允许 -0 ⇒ 输出为 0) / 字符串 / 数组 / 对象(键为字符串)。"
                 "字符串内仅允许标准反斜杠转义 (引号 反斜杠 斜杠 n t uXXXX 六种); uXXXX 解码为对应字符, "
                 "且解码出的码点必须 >= 0x20。对象允许重复键, 重复时后者覆盖前者。"
                 "输出: 规范化文本, **不含任何空白**: 字符串输出时把 引号/反斜杠/换行/制表符 重新转义, 其余字符原样; "
                 "对象的键按 Unicode 码点升序; 例: {\"a\":1,\"b\":[2,3]}。"
                 "若输入非法 (语法错误 / 结尾有多余内容 / 非法转义 / 非法数字 / 空输入), 只输出一行 ERR。"),
        "ref": _p_json_mini_ref,
        "check": _p_json_mini_check,
        "gen_input": _in_json_mini,
        "tight_gen": _jtight,
        "fmt": lambda r: "ERR" if r is _ERR else _jnorm(r),
    },
    "life_k": {
        "spec": ("读入: 第一行三个整数 H W k (H,W 属于 1..20, k 属于 0..20); 随后 H 行, 每行 W 个字符, "
                 "只含 '.'(死) 与 '#'(活)。规则: 每代**同时**按 8 邻域更新, 网格外一律视为死格; "
                 "活细胞邻居数为 2 或 3 时存活, 否则死亡; 死细胞邻居数恰为 3 时复活。"
                 "输出: 第 k 代之后 (k=0 即初始) 的网格, H 行, 每行 W 个字符, 只含 '.' 与 '#'。"),
        "ref": _p_life_k_ref,
        "check": _p_life_k_check,
        "gen_input": _in_life_k,
        "fmt": lambda r: r,
    },
    "sub_game": {
        "spec": ("读入: 第一行两个整数 n k (1<=n<=80 为石子数, 1<=k<=12 为可选步数个数); "
                 "第二行 k 个互不相同的整数 s1..sk (1<=si<=12, 且保证其中含 1), 表示一步可取走的石子数。"
                 "玩法: 两人轮流取, 每次取走恰好某个允许的数目, 取走最后一颗者胜。"
                 "输出: 先手有必胜策略时输出一行 `WIN m` (m 为**数值最小**的必胜首取数); 先手必败时输出一行 `LOSE`。"),
        "ref": _p_sub_game_ref,
        "check": _p_sub_game_check,
        "gen_input": _in_sub_game,
        "fmt": lambda r: "LOSE" if r is None else "WIN %d" % r,
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




# ---------------------------------------------------------------- 对抗输入 (M6 加硬)
# 抗性来源: 这些输入**只进 hidden**, 公开用例里给不到 ⇒ 通过公开样例的"浅解"会在此翻车。
# 覆盖: 退化长度 / 全负 / 全同 / 极大值 / 全零 / 并列。
HARD_INPUTS = {
    "max_subarray": ["1\n-7\n", "3\n-5 -1 -3\n", "6\n0 0 0 0 0 0\n",
                     "5\n1000000000 1000000000 -1 1000000000 1000000000\n", "4\n-1 2 -1 2\n"],
    "longest_unique": ["a\n", "aaaaaa\n", "abcdefghijklmnopqrstuvwxyz\n", "abba\n", "abcdbe\n"],
    "bracket_fix": ["(\n", ")((()\n", "()))(((\n", ")(\n", "((((((\n"],
    "interval_sum": ["1 1\n5\n0 0\n", "3 2\n-1 -2 -3\n0 2\n1 1\n",
                     "4 3\n0 0 0 0\n0 3\n1 2\n2 2\n",
                     "3 1\n1000000000 1000000000 1000000000\n0 2\n", "2 2\n-5 5\n0 1\n1 1\n"],
    "matrix_spiral": ["1 1\n7\n", "1 5\n1 2 3 4 5\n", "5 1\n1\n2\n3\n4\n5\n",
                      "2 2\n-1 -2\n-3 -4\n", "3 3\n0 0 0\n0 0 0\n0 0 0\n"],
    "csv_agg": ["A,1\n", "Z,5\nA,5\n", "A,-3\nB,4\n", "A,0\n", "M,7\nM,-7\nN,2\n"],
    "pair_closest_abs_sum": ["2\n0 0\n", "2\n-5 5\n", "3\n1 1 1\n", "4\n-3 7 7 -3\n", "2\n-9 -9\n"],
    "topo_min": [_nl(["1 0"]), _nl(["2 2", "0 1", "1 0"]), _nl(["2 1", "1 1"]),
                 _nl(["5 0"]), _nl(["3 1", "2 0"]), _nl(["4 3", "3 0", "2 0", "1 0"]),
                 _nl(["6 5", "5 0", "4 0", "3 0", "2 0", "1 0"])],
    "vm_run": [_nl(["2", "POP", "HALT"]), _nl(["3", "PUSH 1", "JNZ 9", "HALT"]),
               _nl(["9", "PUSH 3", "DUP", "PRINT", "PUSH 1", "SUB", "DUP", "JNZ 1", "POP", "HALT"]),
               _nl(["5", "PUSH 2", "PUSH 3", "MUL", "PRINT", "HALT"]),
               _nl(["5", "PUSH 3", "PUSH 4", "SWAP", "SUB", "HALT"]),
               _nl(["3", "PUSH 5", "DUP", "ADD"])],
    "json_mini": [_nl(['{"a":1,"b":[true,null]}']),
                  _nl(['{"a": 1']),
                  "[" + '"a' + BS + 'xb"]' + NL,
                  "[" + '"' + BS + "u0041" + '"]' + NL,
                  _nl(['{"b":1,"a":2,"b":3}']),
                  _nl(["[01]"]),
                  _nl(["[] x"]),
                  _nl(["-0"]),
                  _nl(['{"z":{"b":1,"a":2},"a":[]}']),
                  "[" + '"' + BS + "u0007x" + '"]' + NL,
                  _nl(["[1.5]"]),
                  _nl(["NaN"])],
    "sub_game": [_nl(["1 1", "1"]),
                 _nl(["2 2", "1 3"]),
                 _nl(["3 2", "1 3"]),
                 _nl(["4 1", "1"]),
                 _nl(["7 3", "1 2 5"]),
                 _nl(["6 2", "1 5"])],
    "life_k": [_nl(["1 1 0", "."]),
               _nl(["3 3 1", "...", "###", "..."]),
               _nl(["1 3 1", "###"]),
               _nl(["4 4 4", "....", ".##.", ".##.", "...."]),
               _nl(["3 3 1", ".#.", "..#", "###"]),
               _nl(["2 2 3", "##", "##"])],
}


# ---------------------------------------------------------------- 见证型数学题 (M6 加硬)
# 与"唯一答案"族不同: 答案**不唯一**, 判定 = 独立验证解答者给出的见证 (判据绑定语义, 非比对标签)。

def _w_sqrt_mod_gen(rnd):
    p = rnd.choice([101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167])
    x0 = rnd.randint(0, p - 1)
    return {"kind": "sqrt_mod", "p": p, "a": (x0 * x0) % p}


def _w_sqrt_mod_ref(m):
    p, a = m["p"], m["a"]
    return [x for x in range(p) if (x * x) % p == a]


def _w_sqrt_mod_check(m):
    p, a = m["p"], m["a"]
    hits = []
    for x in range(p):
        r = (x * x) % p
        if r == a:
            hits.append(x)
    return hits


def _w_mod_inverse_gen(rnd):
    p = rnd.choice([101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167])
    return {"kind": "mod_inverse", "p": p, "a": rnd.randint(1, p - 1)}


def _w_mod_inverse_ref(m):
    """穷举扫描 (朴素)。"""
    p, a = m["p"], m["a"]
    return min(x for x in range(p) if (a * x) % p == 1)


def _w_mod_inverse_check(m):
    """独立实现: 内置模逆 (扩展欧几里得), 与穷举互证。"""
    p, a = m["p"], m["a"]
    v = pow(a, -1, p)
    assert 0 <= v < p and (a * v) % p == 1, "check: pow 逆元不合规"
    return v


def _claim_mersenne(n):
    v = (1 << n) - 1
    if v < 2:
        return False
    d = 2
    while d * d <= v:
        if v % d == 0:
            return False
        d += 1
    return True


def _claim_mersenne_alt(n):
    v = (1 << n) - 1
    if v < 2:
        return False
    if v % 2 == 0:
        return v == 2
    d = 3
    while d * d <= v:
        if v % d == 0:
            return False
        d += 2
    return True


def _claim_poly41(n):
    v = n * n - n + 41
    if v < 2:
        return False
    d = 2
    while d * d <= v:
        if v % d == 0:
            return False
        d += 1
    return True


def _claim_poly41_alt(n):
    v = n * n - n + 41
    for d in range(2, int(v ** 0.5) + 1):
        if v % d == 0:
            return False
    return True


CLAIMS = {
    "mersenne_prime": {"expr": "2^n - 1 是质数", "n_min": 2, "n_max": 12,
                       "ref": _claim_mersenne, "check": _claim_mersenne_alt},
    "poly41_prime": {"expr": "n^2 - n + 41 是质数", "n_min": 2, "n_max": 60,
                     "ref": _claim_poly41, "check": _claim_poly41_alt},
}


def _w_counterexample_gen(rnd):
    name = rnd.choice(sorted(CLAIMS))
    c = CLAIMS[name]
    n = c["n_min"]
    while n <= c["n_max"]:
        if not c["ref"](n):
            break
        n += 1
    else:
        raise RefuseToEmit("claim 无反例: %s" % name)
    return {"kind": "min_counterexample", "claim": name, "n": n}


WITNESS_FAMILIES = {
    # answer = 生成器已知的**一个**合法见证, 仅供 oracle 正控与可复现性使用;
    # 判定端(grade.py)不比对 answer, 而是独立验证见证语义 ⇒ 多解不算错, 错解必被拒。
    "witness_sqrt_mod": {
        "gen": _w_sqrt_mod_gen, "spec": lambda m: (
            "求整数 x (0 <= x < %d) 满足 x^2 ≡ %d (mod %d)。答案不唯一, 任何满足条件的 x 都算正确。"
            % (m["p"], m["a"], m["p"])),
        "answer": lambda m: str(min(_dual(_w_sqrt_mod_ref, _w_sqrt_mod_check, m))),
    },
    "witness_mod_inverse": {
        "gen": _w_mod_inverse_gen, "spec": lambda m: (
            "求整数 x (0 <= x < %d) 满足 (%d * x) mod %d == 1。答案唯一, 给出该 x 即可。"
            % (m["p"], m["a"], m["p"])),
        "answer": lambda m: str(_dual(_w_mod_inverse_ref, _w_mod_inverse_check, m)),
    },
    "witness_min_counterexample": {
        "gen": _w_counterexample_gen, "spec": lambda m: (
            "设命题 P(n) 为: %s (n 为整数)。求最小的 n >= %d 使 P(n) 为假。"
            % (CLAIMS[m["claim"]]["expr"], CLAIMS[m["claim"]]["n_min"])),
        "answer": lambda m: str(m["n"]),
    },
}


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
    if fam in WITNESS_FAMILIES:
        wf = WITNESS_FAMILIES[fam]
        m = wf["gen"](rnd)
        prompt = ("%s\n\n请给出最终答案, 最后一行必须是 `FINAL: <答案>` 格式。"
                  % wf["spec"](m))
        return Task(tid="m%03d" % idx, kind="math", family=fam, prompt=prompt,
                    answer=wf["answer"](m), meta={"witness": m})
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
        if len(cases) == n_public + n_hidden - 1 and f.get("tight_gen"):
            stdin_text = f["tight_gen"](rnd)
        else:
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
    hard = []
    for stdin_text in HARD_INPUTS.get(fam, []):
        if stdin_text in seen:
            continue
        seen.add(stdin_text)
        exp = _dual(lambda s: _fam_answer(fam, "ref", s),
                    lambda s: _fam_answer(fam, "check", s), stdin_text)
        hard.append(Case(stdin_text, f["fmt"](exp)))
    if len(hard) < 3:
        raise RefuseToEmit("对抗用例不足: %s (%d)" % (fam, len(hard)))
    return Task(tid="p%03d" % idx, kind="program", family=fam, prompt=prompt,
                public=cases[:n_public], hidden=cases[n_public:] + hard,
                meta={"hard": len(hard)})


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
        chk("双路径一致时可发题", len(t.hidden) == 2 + t.meta["hard"],
            "hid=%d hard=%d" % (len(t.hidden), t.meta["hard"]))
    except RefuseToEmit as e:
        chk("双路径一致时可发题", False, str(e))

    for fam in sorted(PROGRAM_FAMILIES):
        try:
            t = gen_program_task(2, [fam], random.Random(1000 + len(fam)), n_public=1, n_hidden=3)
            chk("program 族双路径一致:%s" % fam,
                len(t.hidden) == 3 + t.meta["hard"] and t.meta["hard"] >= 3,
                "hid=%d hard=%d" % (len(t.hidden), t.meta["hard"]))
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

    # ---- M6 加硬: 对抗用例覆盖 + 浅解必须翻车 + 见证型 ----
    chk("对抗输入覆盖全部 program 族",
        set(HARD_INPUTS) == set(PROGRAM_FAMILIES)
        and all(len(v) >= 3 for v in HARD_INPUTS.values()),
        "%d 族 / 最少 %d 条" % (len(HARD_INPUTS), min(len(v) for v in HARD_INPUTS.values())))

    hit = 0
    for fam in sorted(PROGRAM_FAMILIES):
        tt = gen_program_task(9, [fam], random.Random(2000 + len(fam)), n_public=2, n_hidden=2)
        pub_map = {c.stdin: c.expected_stdout for c in tt.public}
        passed = sum(1 for h in tt.hidden if pub_map.get(h.stdin) == h.expected_stdout)
        hit += passed
        chk("浅解(只硬编码公开样例)在 %s 上零通过" % fam, passed == 0, "passed=%d" % passed)
    chk("浅解跨族零通过", hit == 0)

    for fam in sorted(WITNESS_FAMILIES):
        tt = gen_math_task(10, [fam], random.Random(3000 + len(fam)))
        m = tt.meta.get("witness", {})
        av = int(tt.answer) if tt.answer.strip() else None
        kind = m.get("kind")
        if kind == "sqrt_mod":
            chk("见证型 answer 是合法见证(oracle 正控可用)",
                av is not None and 0 <= av < m["p"] and (av * av) % m["p"] == m["a"],
                "answer=%r p=%d a=%d" % (tt.answer, m["p"], m["a"]))
        elif kind == "mod_inverse":
            chk("见证型 answer 是合法见证(oracle 正控可用)",
                av is not None and 0 <= av < m["p"] and (av * m["a"]) % m["p"] == 1,
                "answer=%r p=%d a=%d" % (tt.answer, m["p"], m["a"]))
        else:
            chk("见证型 answer 是最小反例", av == m.get("n"), "answer=%r n=%r" % (tt.answer, m.get("n")))
        if m.get("kind") == "sqrt_mod":
            good = (m["a"] % m["p"]) == ((min(x for x in range(m["p"]) if (x * x) % m["p"] == m["a"]) ** 2) % m["p"])
            bad = [x for x in range(m["p"]) if (x * x) % m["p"] == m["a"]]
            chk("见证型 sqrt_mod 有解且非平凡", good and len(bad) >= 1 and m["p"] in (101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167),
                "p=%d a=%d 解数=%d" % (m["p"], m["a"], len(bad)))
            n0 = (m["a"] + 1) % m["p"]
            chk("见证型 sqrt_mod 错见证必须被拒", not ((m["a"] == 0) or ((n0 * n0) % m["p"] == m["a"])),
                "反例 x=%d" % n0)
        elif kind == "mod_inverse":
            sols = [x for x in range(m["p"]) if (m["a"] * x) % m["p"] == 1]
            chk("见证型 mod_inverse 逆元存在且唯一",
                len(sols) == 1 and sols[0] == av
                and m["p"] in (101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167)
                and 1 <= m["a"] < m["p"],
                "p=%d a=%d 解数=%d" % (m["p"], m["a"], len(sols)))
            w = (av + 1) % m["p"]
            chk("见证型 mod_inverse 错见证必须被拒", (m["a"] * w) % m["p"] != 1, "反例 x=%d" % w)
        else:
            C = CLAIMS[m["claim"]]
            n = m["n"]
            chk("见证型 最小反例正确且最小",
                (not C["ref"](n)) and all(C["ref"](k) for k in range(C["n_min"], n)),
                "%s n=%d" % (m["claim"], n))
            chk("见证型 最小反例双实现一致:%s" % m["claim"], C["check"](n) == C["ref"](n))
        chk("见证型 answer 就位且判定=验见证非比对标签:%s" % fam,
            tt.answer.strip() != "" and bool(m) and "FINAL:" in tt.prompt)

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
        fams = sorted(MATH_FAMILIES) + sorted(WITNESS_FAMILIES)
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
