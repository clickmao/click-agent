#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DCR 判定题集生成器 (eval/dcr/dcr_cases.jsonl)。

铁律:
  * 标签**不由人手拍** —— 对每个 premise ∧ ¬goal 交独立 oracle z3 做**整数** SAT 检查:
        unsat  => entail  (Proceed/Proved)
        sat    => refute  (Violation/Refuted, 并记录 z3 model 作为期望反例)
        premises 本身 unsat => vacuous (Violation/Vacuous)
  * out_of_fragment / malformed / absent 三类**不可**由 z3 的 SAT 结果决定
    (它们考的是「片段归属 / 契约结构 / 缺失语义」, 不是数学真值), z3_label 记 "n/a"
    并在 label_note 里说明理由, label_source 记 "constructive"。
  * 生成后**逐条自验**: 用同一 oracle 从 contract 重算标签, 写回 self_check。

用法:
    /tmp/z3env/bin/python eval/dcr/gen_cases.py            # 写 eval/dcr/dcr_cases.jsonl
    /tmp/z3env/bin/python eval/dcr/gen_cases.py --check     # 只自验 (不写文件)
"""
import argparse
import json
import os
import sys

try:
    import z3
except ImportError as e:  # pragma: no cover
    sys.stderr.write("FATAL: z3 不可用: %s\n" % e)
    raise

# ---------------------------------------------------------------------------
# 1) 可判定片段的表达式 → z3 (与 src/agent.rover/formal/Formula.cs 的词法/语法同构)
# ---------------------------------------------------------------------------


def _lex(s):
    ts = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c.isdigit():
            j = i
            while j < n and s[j].isdigit():
                j += 1
            ts.append(("num", int(s[i:j])))
            i = j
            continue
        if c.isalpha() or c == "_":
            j = i
            while j < n and (s[j].isalnum() or s[j] in "_."):
                j += 1
            w = s[i:j]
            ts.append(({"and": "and", "or": "or", "not": "not"}.get(w, "ident"), w))
            i = j
            continue
        if i + 1 < n:
            m = {"<=": "le", ">=": "ge", "==": "eq", "!=": "ne", "&&": "and", "||": "or"}
            two = s[i:i + 2]
            if two in m:
                ts.append((m[two], two))
                i += 2
                continue
        k = {"+": "plus", "-": "minus", "*": "star", "<": "lt",
             ">": "gt", "(": "lp", ")": "rp", "!": "not"}.get(c)
        if k is None:
            raise ValueError("expr_bad_char: '%s' @%d" % (c, i))
        ts.append((k, c))
        i += 1
    ts.append(("end", "<eof>"))
    return ts


class _P:
    def __init__(self, toks):
        self.t = toks
        self.i = 0

    def k(self):
        return self.t[self.i][0]

    def s(self):
        return self.t[self.i][1]

    def eat(self, k):
        if self.k() != k:
            raise ValueError("expr_expected_%s: got %s '%s'" % (k, self.k(), self.s()))
        v = self.t[self.i]
        self.i += 1
        return v

    # linear term: {var: coeff} + const
    @staticmethod
    def _add(a, b, sign=1):
        coeffs = dict(a[0])
        for k, v in b[0].items():
            coeffs[k] = coeffs.get(k, 0) + sign * v
            if coeffs[k] == 0:
                del coeffs[k]
        return (coeffs, a[1] + sign * b[1])

    def or_(self):
        f = self.and_()
        if self.k() != "or":
            return f
        items = [f]
        while self.k() == "or":
            self.eat("or")
            items.append(self.and_())
        return z3.Or(*items)

    def and_(self):
        f = self.unary()
        if self.k() != "and":
            return f
        items = [f]
        while self.k() == "and":
            self.eat("and")
            items.append(self.unary())
        return z3.And(*items)

    def unary(self):
        if self.k() == "not":
            self.eat("not")
            return z3.Not(self.unary())
        if self.k() == "lp":
            self.eat("lp")
            inner = self.or_()
            if self.k() != "rp":
                raise ValueError("expr_missing_rparen")
            self.eat("rp")
            return inner
        return self.cmp()

    def cmp(self):
        l = self.lin()
        op = self.k()
        if op not in ("le", "lt", "ge", "gt", "eq", "ne"):
            raise ValueError("expr_expected_comparison: got %s '%s'" % (op, self.s()))
        self.eat(op)
        r = self.lin()
        d = self._add(l, r, sign=-1)  # l - r
        z = _lin_to_z3(d)
        return {"le": lambda: z <= 0, "lt": lambda: z < 0,
                "ge": lambda: z >= 0, "gt": lambda: z > 0,
                "eq": lambda: z == 0, "ne": lambda: z != 0}[op]()

    def lin(self):
        acc = self.term()
        while self.k() in ("plus", "minus"):
            sign = 1 if self.k() == "plus" else -1
            self.eat(self.k())
            acc = self._add(acc, self.term(), sign)
        return acc

    def term(self):
        acc = self.factor()
        while self.k() == "star":
            self.eat("star")
            rhs = self.factor()
            if acc[0] == {}:
                acc = ({k: v * acc[1] for k, v in rhs[0].items()}, rhs[1] * acc[1])
            elif rhs[0] == {}:
                acc = ({k: v * rhs[1] for k, v in acc[0].items()}, acc[1] * rhs[1])
            else:
                raise ValueError("expr_nonlinear: 变量*变量 不在可判定片段内")
        return acc

    def factor(self):
        if self.k() == "minus":
            self.eat("minus")
            f = self.factor()
            return ({k: -v for k, v in f[0].items()}, -f[1])
        if self.k() == "plus":
            self.eat("plus")
            return self.factor()
        if self.k() == "num":
            return ({}, self.eat("num")[1])
        if self.k() == "ident":
            return ({self.eat("ident")[1]: 1}, 0)
        raise ValueError("expr_expected_operand: got %s '%s'" % (self.k(), self.s()))


def _lin_to_z3(l):
    e = z3.IntVal(l[1])
    for v, c in l[0].items():
        e = e + c * z3.Int(v)
    return e


def parse_expr(s):
    """表达式文本 → z3 布尔式 (整数语义)。越界/非线性 → ValueError。"""
    p = _P(_lex(s))
    f = p.or_()
    if p.k() != "end":
        raise ValueError("expr_unexpected_token: %s '%s'" % (p.k(), p.s()))
    return f


def parse_contract(text):
    """契约文本 → (premises[list[str]], goal[str])。仅取 premise/goal 行。"""
    prem, goal = [], None
    for raw in (text or "").split("\n"):
        line = raw.strip()
        if not line or line[0] == "#":
            continue
        if line.startswith("premise "):
            prem.append(line[len("premise "):].strip())
        elif line.startswith("let "):
            prem.append(line[len("let "):].strip())
        elif line.startswith("goal "):
            goal = line[len("goal "):].strip()
    return prem, goal


# ---------------------------------------------------------------------------
# 2) oracle: z3 整数 SAT
# ---------------------------------------------------------------------------


def _z3_model_of(P, G):
    """premise ∧ ¬goal 的一个整数模型 (全部变量都取到具体值)。"""
    s2 = z3.Solver()
    s2.set("timeout", 20000)
    s2.add(P)
    s2.add(z3.Not(G))
    if s2.check() != z3.sat:
        return None
    m = s2.model()
    names = sorted({str(d) for d in m.decls()} | _vars_of(P) | _vars_of(G))
    return {n: m.eval(z3.Int(n), model_completion=True).as_long() for n in names}


def model_is_valid_counterexample(text, model):
    """语义校验: model 必须满足全部 premise 且违反 goal (整数)。"""
    if not isinstance(model, dict):
        return False
    prem, goal = parse_contract(text)
    P = z3.And(*[parse_expr(b) for b in prem])
    G = parse_expr(goal)
    s = z3.Solver()
    s.add(P, z3.Not(G))
    for n, v in model.items():
        s.add(z3.Int(n) == int(v))
    return s.check() == z3.sat


def z3_label_contract(text):
    """对 contract 做整数 SAT 检查, 返回 (status, details)。

    status ∈ {'entail','refute','vacuous'}; details 含 z3_label / z3_model / 变量表。
    """
    prem, goal = parse_contract(text)
    if not prem or goal is None:
        raise ValueError("contract_not_well_formed_for_z3_oracle")
    P = z3.And(*[parse_expr(b) for b in prem])
    G = parse_expr(goal)

    s = z3.Solver()
    s.set("timeout", 20000)
    s.add(P)
    if s.check() == z3.unsat:
        return "vacuous", {"z3_label": "premises_unsat", "z3_model": None}

    s2 = z3.Solver()
    s2.set("timeout", 20000)
    s2.add(P)
    s2.add(z3.Not(G))
    r = s2.check()
    if r == z3.unsat:
        return "entail", {"z3_label": "unsat", "z3_model": None}
    if r == z3.sat:
        return "refute", {"z3_label": "sat", "z3_model": _z3_model_of(P, G)}
    raise RuntimeError("z3 returned %s" % r)


def _vars_of(e):
    out = set()

    def walk(x):
        if z3.is_const(x) and x.decl().kind() == z3.Z3_OP_UNINTERPRETED:
            out.add(str(x))
        for c in getattr(x, "children", lambda: [])():
            walk(c)

    walk(e)
    return out


DISPO = {"entail": ("Proceed", "Proved"),
         "refute": ("Violation", "Refuted"),
         "vacuous": ("Violation", "Vacuous")}


# ---------------------------------------------------------------------------
# 3) 题集定义
# ---------------------------------------------------------------------------

ENTAIL = [
    # (a) 整数严格性边界: >4 ≡ >=5, <=10 ≡ <11
    "premise x > 4\ngoal x >= 5",
    "premise x >= 5\ngoal x > 4",
    "premise x <= 10\ngoal x < 11",
    "premise x < 11\ngoal x <= 10",
    "premise x > 0\ngoal x >= 1",
    "premise x < 0\ngoal x <= -1",
    "premise x >= -3\ngoal x > -4",
    "premise x > 4\ngoal x > 4",
    # 线性算术
    "premise x + y == 10\npremise x > 4\ngoal y < 6",
    "premise x + y == 10\npremise y < 6\ngoal x > 4",
    "premise 2 * x == 10\ngoal x == 5",
    "premise 3 * x <= 12\ngoal x <= 4",
    "premise x == y\npremise y == z\ngoal x == z",
    "premise x + y == 10\npremise x - y == 4\ngoal x == 7",
    "premise x >= 1\npremise y >= 2\ngoal x + y >= 3",
    "premise x - y == 0\npremise y >= 5\ngoal x >= 5",
    "premise 2 * x + 3 * y == 12\npremise x >= 0\npremise y >= 0\ngoal x <= 6",
    "premise x + y == 10\npremise z == x + y\ngoal z == 10",
    # (d) 系数 0 的退化约束
    "premise 0 * x + y >= 3\npremise x >= 0\ngoal y >= 3",
    "premise 0 * x == 0\npremise y > 2\ngoal y > 2",
    "premise x + 0 * y == 7\ngoal x + 0 * y == 7",
    "premise 0 * x + 0 * y + x == 5\ngoal x == 5",
    # (e) 多变量 (>=4) 线性系统
    "premise a + b + c + d == 20\npremise a >= 0\npremise b >= 0\npremise c >= 0\npremise d >= 0\ngoal a <= 20",
    "premise a + b + c + d == 20\npremise d >= 0\ngoal a + b + c <= 20",
    "premise a + b + c + d == 20\npremise a == 1\npremise b == 2\npremise c == 3\ngoal d == 14",
    "premise a + 2 * b + 3 * c + 4 * d == 30\npremise a >= 0\npremise b >= 0\npremise c >= 0\npremise d >= 0\ngoal a <= 30",
    # 命题逻辑 (&& / || / ==组合)
    "premise x > 1 && x < 4\ngoal x >= 2 && x <= 3",
    "premise x == 5 || x == 6\ngoal x >= 5 && x <= 6",
    "premise x != 1 && x != 2 && x != 3\ngoal x != 1",
    # (e) 多变量: 取值被等式钉死 ⇒ 内核可判 (对照上面只能弃权的自由多变量组)
    "premise x == 3\npremise y == 4\npremise z == 5\npremise w == 6\ngoal x + y + z + w == 18",
    "premise a == 1\npremise b == 2\npremise c == 3\npremise d == 4\ngoal a + b + c + d == 10",
    "premise 2 * a == 4\npremise 3 * b == 9\ngoal a + b == 5",
    "premise a + b + c + d == 20\npremise a == 5\npremise b == 5\npremise c == 5\ngoal d == 5",
]

REFUTE = [
    # (c) 表面像蕴含但实际不蕴含
    "premise x > 4\npremise x + y == 10\ngoal x <= 10",          # 题面示例本身即反例 x=11,y=-1
    "premise x + y == 10\ngoal x < 10",                          # x=11,y=-1
    "premise x + y == 10\ngoal x <= 5",                          # x=11,y=-1
    "premise x - y == 5\ngoal x > y + 5",                        # 边界: x=y+5 不大于 y+5
    "premise x >= 0\ngoal x >= 1",
    "premise x <= 10\ngoal x <= 9",
    # (a) 严格性边界的不等价对
    "premise x > 4\ngoal x >= 6",                                # x=5
    "premise x >= 5\ngoal x >= 6",                               # x=5
    "premise x < 11\ngoal x < 10",                               # x=10
    "premise x > 4\ngoal x != 5",                                # x=5
    # (b) 隐藏反例的大区间
    "premise 0 <= x\npremise x <= 1000000\ngoal x < 500000",      # x=500000
    "premise 0 <= x\npremise x <= 1000000\ngoal x <= 999999",     # x=1000000
    "premise 1 <= x && x <= 1000\ngoal x <= 999",                 # x=1000
    "premise x + y == 10\npremise 0 <= x\npremise x <= 1000\ngoal y >= 5",  # x=5,y=5? goal y>=5 true; 反例需 y<5 → x=6..1000 早于? sat
    # (d) 系数 0 退化
    "premise x + 0 * y == 7\ngoal x == 8",
    "premise 0 * x + y == 3\ngoal y >= 4",
    "premise 0 * x + 0 * y + x == 5\ngoal x >= 6",
    "premise x * 0 + y > 2\ngoal y != 3",
    # (e) 多变量
    "premise a + b + c + d == 20\npremise a >= 0\ngoal a <= 4",
    "premise a + b + c + d == 20\npremise b >= 0\ngoal b <= 3",
    "premise x + y + z == 30\npremise z >= 0\ngoal x <= 9",
    "premise a + 2 * b + 3 * c + 4 * d == 30\npremise d >= 0\ngoal d >= 1",
    # 命题逻辑
    "premise x > 1 && x < 4\ngoal x == 2",
    "premise x == 5 || x == 6\ngoal x == 5",
    "premise x != 3\ngoal x != 4",
    # (b') 大区间但反例域被夹紧 ⇒ 内核可判 (对照上面只能弃权的宽反例域)
    "premise 0 <= x\npremise x <= 1000\ngoal x <= 999",
    "premise 0 <= x\npremise x <= 1000000\ngoal x < 999999",
    # (e') 多变量: 取值被等式钉死 ⇒ 内核可判
    "premise a == 5\npremise b == 6\npremise c == 7\npremise d == 8\ngoal a + b + c + d == 25",
    "premise 2 * x == 4\npremise y == 3\ngoal x + y == 6",
    "premise x == 7\npremise y == 8\npremise z == 9\npremise w == 10\ngoal x < 7",
]

VACUOUS = [
    "premise 2 * x == 7\ngoal x == 3",                                # 奇数, 无整数解
    "premise 6 * x == 9\ngoal x == 1",                                # 3 的奇数倍 = 偶数倍? 6x=9 无整数解
    "premise 3 * x - 3 * y == 1\ngoal x == y",
    "premise x > 5\npremise x < 5\ngoal x == 5",
    "premise x >= 10\npremise x <= 9\ngoal x == 9",
    "premise x >= 1\npremise x <= 0\ngoal x == 0",
    "premise x + y == 4\npremise x + y == 5\ngoal x == 0",
    "premise x + y == 10\npremise x + y == 11\ngoal x == 5",
    "premise x == 1\npremise x == 2\ngoal x == 1",
    "premise 0 * x + 0 * y == 1\npremise y > 2\ngoal y > 2",
    "premise 2 * a + 2 * b + 2 * c == 5\ngoal a + b + c == 2",
    "premise 4 * x + 6 * y == 3\npremise x >= 0\npremise y >= 0\ngoal x == 0",
    "premise x - x == 1\ngoal x == 0",
    "premise 2 * x + 4 * y == 3\ngoal x == 0",
    "premise x >= 5\npremise x < 5\npremise y == 3\ngoal y == 3",
    "premise 2 * x == 2 * y + 1\ngoal x == y",
    "premise 10 * x == 5\ngoal x == 0",
    "premise 2 * x + 2 * y == 3\ngoal x + y == 1",
    # (e') 多变量: 等式把取值钉死后自相矛盾 ⇒ 内核可判
    "premise a == 1\npremise b == 1\npremise c == 1\npremise d == 1\npremise a + b + c + d == 5\ngoal a == 0",
    "premise x == 3\npremise y == 3\npremise z == 3\npremise w == 3\npremise x + y + z + w == 11\ngoal x == 3",
]

OUT_OF_FRAGMENT = [
    "premise x * x == 4\ngoal x == 2",
    "premise x * y == 6\ngoal x == 2",
    "premise x * x <= 9\ngoal x <= 3",
    "premise x * x - 1 == 0\ngoal x == 1",
    "premise x * x + y * y == 25\ngoal x <= 5",
    "premise 2 * x * x == 8\ngoal x == 2",
    "premise x * y * z == 8\ngoal x <= 8",
    "premise x * x == y\ngoal y >= 0",
    "premise x * x * x == 27\ngoal x == 3",
    "premise x * y + x == 4\ngoal x <= 4",
    "premise x * x + y == 10\ngoal y <= 10",
    "premise x * x == 4 && y == 1\ngoal x <= 2",
    "premise y == 1\ngoal x * x == 4",
    "premise x > 0\ngoal x * x > 0",
    "premise a * b == 1\ngoal a == 1",
    "premise x * x - y == 0\ngoal x >= 0",
    "premise x * x + x == 0\ngoal x == 0 || x == -1",
    "premise x * y + 3 * x == 12\ngoal x <= 12",
    # 超规模: 变量数 > 内核 MaxVars(12)
    "premise a1 + a2 + a3 + a4 + a5 + a6 + a7 + a8 + a9 + a10 + a11 + a12 + a13 == 13\ngoal a1 <= 13",
]

MALFORMED = [
    # —— 契约层: 残缺 ——
    "premise",
    "premise ",
    "goal",
    "goal ",
    "premise x > 4",
    "goal x < 10",
    "premise x > 4\ngoal",
    "premise x > 4\ngoal ",
    # —— 契约层: 自相矛盾 ——
    "no_formal: 纯 IO 节点\npremise x > 0\ngoal x > 0",
    "premise x > 0\nno_formal: 其实不可判定\ngoal x > 0",
    # —— 关键字被当作英文词 ——
    "goal is to summarize the document",
    "premise of the plan is to read config",
    # —— 内核层: 真语法错 (契约齐备) ——
    "premise x >\ngoal x > 0",
    "premise x +\ngoal x > 0",
    "premise x $ 1\ngoal x > 0",
    "premise (x > 1\ngoal x > 0",
    "premise x 1\ngoal x > 0",
    "premise 1\ngoal x > 0",
    "premise x > 1 && \ngoal x > 0",
    "premise @\ngoal x > 0",
    "premise x\ngoal x > 0",
    "premise x == \ngoal x > 0",
    # —— 语言限制: 括号**不支持**线性项 (ParseFactor 不认 '(') ⇒ 真语法错, 非片段限制 ——
    "premise (x + 1) * (x - 1) == 0\ngoal x == 1",
    "premise 2 * (x + 1) == 4\ngoal x == 1",
    "premise x * (y + 1) == 4\ngoal x <= 4",
]

ABSENT = [
    None,
    "",
    "   ",
    "\n",
    "\n\n\t  \n",
    "# 只有一行注释",
    "// 只有一行注释",
    "read the config file and return the parsed value",
    "本节点无需形式化断言,直接读取环境变量",
    "the sum is computed by the caller",
    "either the cache hit or the disk read decides the branch",
    "TODO: implement later",
    "no-op",
    "x + y == 10",
    "1 + 1 == 2",
    "x * x == 4",
    "premises are not needed here",
    "goal:",
]

CATS = [("entail", ENTAIL), ("refute", REFUTE), ("vacuous", VACUOUS),
        ("out_of_fragment", OUT_OF_FRAGMENT), ("malformed", MALFORMED),
        ("absent", ABSENT)]


def build():
    rows = []
    seq = 0
    for cat, cases in CATS:
        for ct in cases:
            seq += 1
            cid = "c%03d" % seq
            row = {"id": cid, "category": cat, "contract": ct}
            if cat in ("entail", "refute", "vacuous"):
                status, det = z3_label_contract(ct)
                if status != cat:
                    raise SystemExit(
                        "ORACLE MISMATCH: %s declared=%s z3=%s contract=%r"
                        % (cid, cat, status, ct))
                d, v = DISPO[status]
                row.update({
                    "expected_disposition": d,
                    "expected_verdict": v,
                    "label_source": "z3",
                    "z3_label": det["z3_label"],
                    "z3_model": det["z3_model"],
                })
                if status == "refute":
                    row["z3_label_why"] = (
                        "z3: premise ∧ ¬goal 可满足 (整数), model 即期望反例")
                elif status == "entail":
                    row["z3_label_why"] = (
                        "z3: premise ∧ ¬goal 在整数上 unsat ⇒ 真蕴含")
                else:
                    row["z3_label_why"] = (
                        "z3: premise 本身 unsat (整数) ⇒ 空真, 非证据")
            elif cat == "absent":
                row.update({
                    "expected_disposition": "Proceed",
                    "expected_verdict": "NoFormal",
                    "label_source": "constructive",
                    "z3_label": "n/a",
                    "z3_model": None,
                    "z3_label_why": (
                        "契约层 NoFormal: 缺失/空/纯自然语言 (无 premise∧goal), "
                        "不进入内核, 无数学真值可判 ⇒ z3 不适用"),
                })
            elif cat == "out_of_fragment":
                row.update({
                    "expected_disposition": "Abstained",
                    "expected_verdict": "Unknown",
                    "label_source": "constructive",
                    "z3_label": "n/a",
                    "z3_model": None,
                    "z3_label_why": (
                        "考的是「片段归属」而非数学真值: 内核必须诚实弃权(Unknown), "
                        "即使 z3 能判其真假也不改变期望 ⇒ z3 不适用"),
                })
            else:  # malformed
                row.update({
                    "expected_disposition": "Malformed",
                    "expected_verdict": "Malformed",
                    "label_source": "constructive",
                    "z3_label": "n/a",
                    "z3_model": None,
                    "z3_label_why": (
                        "考的是「契约结构」: 残缺/矛盾/裸关键字/真语法错, "
                        "无可判定命题 ⇒ z3 不适用"),
                })
            rows.append(row)
    return rows


def self_check(rows):
    """逐条重算标签 (独立于生成时的期望), 写回 self_check。"""
    for r in rows:
        cat = r["category"]
        if cat in ("entail", "refute", "vacuous"):
            status, det = z3_label_contract(r["contract"])
            d, v = DISPO[status]
            ok = (status == cat
                  and d == r["expected_disposition"]
                  and v == r["expected_verdict"]
                  and det["z3_label"] == r["z3_label"])
            # 反例模型是见证而非规范形: 校验**存储的那一个**语义为真, 而非逐字节相等
            if ok and cat == "refute":
                ok = model_is_valid_counterexample(r["contract"], r["z3_model"])
                why = "" if ok else "存储的 z3_model 不是合法反例"
            r["self_check"] = "ok" if ok else (
                "MISMATCH: recomputed=%s/%s/%s model=%s" % (status, d, v, det["z3_model"]))
        else:
            # 结构自验: 类别的构造性约束必须成立
            ct = r["contract"]
            if cat == "absent":
                ok = ct is None or ct.strip() == "" or _has_no_kw(ct)
                why = "" if ok else "absent 契约意外含 premise/goal 关键字"
            elif cat == "out_of_fragment":
                ok, why = _is_of_fragment(ct)
            else:
                ok, why = _is_structurally_malformed(ct)
            r["self_check"] = "ok" if ok else ("MISMATCH: " + why)
        if r["self_check"] != "ok":
            raise SystemExit("SELF-CHECK FAILED %s: %s" % (r["id"], r["self_check"]))
    return rows


def _has_no_kw(ct):
    for raw in ct.split("\n"):
        line = raw.strip()
        if line.startswith("premise ") or line.startswith("goal "):
            return False
        if line == "premise" or line == "goal":
            return False
    return True


def _is_of_fragment(ct):
    prem, goal = parse_contract(ct)
    try:
        for b in prem:
            parse_expr(b)
        parse_expr(goal or "")
    except ValueError as e:
        if "expr_nonlinear" in str(e) or "不在可判定片段内" in str(e):
            return True, ""
        return False, "expected nonlinear, got: %s" % e
    # 无非线性 ⇒ 必须是超规模 (变量 > 12)
    varn = len(_all_vars(ct))
    if varn > 12:
        return True, ""
    return False, "既非线性也未超规模(变量=%d)" % varn


def _all_vars(ct):
    prem, goal = parse_contract(ct)
    out = set()
    for b in prem + [goal or ""]:
        try:
            out |= _vars_of(parse_expr(b))
        except ValueError:
            pass
    return out


def _is_structurally_malformed(ct):
    """与 FormalAssertionContract.Parse 的判定口径同构 (独立实现, 用于结构自验)。"""
    prem, goals, broken, decl = [], [], False, None
    for raw in ct.split("\n"):
        line = raw.strip()
        if not line or line[0] == "#":
            continue
        low = line.lower()
        if low.startswith("no_formal"):
            rest = line[len("no_formal"):]
            if rest and rest[0] == ":":
                decl = rest[1:].strip()
                continue
            if rest and not rest[0].isspace():
                continue
            decl = rest.strip()
            continue
        def kw(word):
            if not line.startswith(word):
                return None
            rest = line[len(word):]
            if rest and not rest[0].isspace():
                return None
            return rest.strip()
        b = kw("premise")
        if b is not None:
            if b == "":
                broken = True
            else:
                prem.append(b)
            continue
        g = kw("goal")
        if g is not None:
            if g == "":
                broken = True
            else:
                goals.append(g)
    has_intent = bool(prem) or bool(goals) or broken
    if decl is not None and has_intent:
        return True, ""
    if has_intent and (broken or not prem or not goals):
        return True, ""
    if has_intent:
        # 契约层放行 ⇒ 必须被内核判 Malformed (真语法错, 且非非线性)
        try:
            for b in prem:
                parse_expr(b)
            parse_expr(goals[0])
        except ValueError as e:
            if "expr_nonlinear" in str(e) or "不在可判定片段内" in str(e):
                return False, "契约放行但为非线性(应属 out_of_fragment)"
            return True, ""
        return False, "契约齐备且内核算术合法 ⇒ 应属 entail/refute/vacuous"
    return False, "无断言意图 ⇒ 应属 absent"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只自验, 不写文件")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "dcr_cases.jsonl"))
    a = ap.parse_args()

    rows = self_check(build())

    from collections import Counter
    cnt = Counter(r["category"] for r in rows)
    print("z3: %s" % z3.get_version_string())
    print("total=%d" % len(rows))
    for cat, _ in CATS:
        print("  %-16s %d" % (cat, cnt[cat]))
    bad = [r["id"] for r in rows if r["self_check"] != "ok"]
    print("self_check: %d ok / %d bad" % (len(rows) - len(bad), len(bad)))
    for cat, _ in CATS:
        if cnt[cat] < 12:
            raise SystemExit("FATAL: category %s < 12" % cat)

    if not a.check:
        with open(a.out, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        print("wrote %s (%d lines)" % (a.out, len(rows)))


if __name__ == "__main__":
    main()
