#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R514 · 题面-判据一致性机检器 (候选②, 主线: 外部真值对照的夹具自检).

动机 (R512 实证): p4 题面第 2 条只写「全局选项 `--now <epoch 秒>` 注入当前时间」, **未写缺省语义**;
隐藏用例 12 条里 8 条不带 `--now` 调用 ⇒ 判据依赖题面没写明的约定 ⇒ 三个臂 (含外部真值 codex) 同败、
失败集合逐字相同 ⇒ 判据丧失区分力。该缺陷当时**靠人工定位**, 本器具把它机械化。

--- 读契约 (instrument read contract; 任何一条不满足 ⇒ rc=2 fail-closed, 禁计入被测读数) ---
输入 taskset (utf-8-sig): {"tasks":[{"tid","prompt","cases","ref","hidden_cases"}...]}
  · `prompt` = 题面全文 (唯一权威语料: 判据只许断言此处写明的契约)
  · `cases`  = 相对 taskset 所在目录的用例文件路径
用例文件 (静态 AST 解析, **不执行**):
  · 调用点 = 实参里含字面选项 token (以 `--` 开头的字符串常量) 的任何调用;
    列表/元组实参被展平; 非字面实参记 `<expr>` 占位 (保留元数, 不猜取值); 关键字实参 `args=` 同样展开。
  · 用例清单 (两种形态, 均可机取):
       (a) 变换形态: 顶层 `def` 名经文件中 `X.__name__[k:]` 的常量 k **派生** (禁硬编码 "test_");
       (b) 表形态  : 模块级 `CASES = [(<名>, <函数名>), ...]` 显式声明表。
  · 零退出码断言: 用例函数体内出现 `== 0` 比较, 或调用其体内的模块级助手 (传递闭包) 出现之。
  · 输出面键: 由「体内含 json.load(s) 的函数」(解码助手) 赋值的变量, 及其经下标派生的变量上的字面键。
语料边界: 本器具只做**静态**一致性检查 (题面字面 vs 用例调用与断言), 不判产品正确性; 不联网、不执行被测。

--- 判据 (逐条机检) ---
D1 `case_uses_option_not_in_statement` : 用例调用里的选项 token 未在题面出现 ⇒ 缺陷。
D2 `reliance_on_unstated_default`      : 题面把取值型选项 O 写成「非可选 ∧ 无缺省说明」, 而某调用点**省略** O
                                          ⇒ 该调用依赖题面未写明的缺省语义 ⇒ 缺陷 (R512 形态)。
   子分类 `binding` / `masked` / `spawn_site`: 该用例是否断言过零退出码 ⇒ 缺陷会真翻红(binding);
   只断言错误码 ⇒ 被错误路径掩盖(masked); 调用点在夹具非用例作用域 ⇒ spawn_site。
D3 `undeclared_error_token`            : 用例断言了某 error 取值, 题面未出现该字面 ⇒ 缺陷。
D4 `undeclared_json_key`               : 用例断言了某输出键, 题面未出现该字面 ⇒ 缺陷。
I1 `statement_option_unexercised`      : 题面出现的选项从未被任何调用点使用 ⇒ 信息项 (不判缺陷)。
I2 `statement_error_token_unexercised` : 题面写明的 error 取值从未被断言 ⇒ 信息项 (覆盖缺口)。

退出码: 0 = 无缺陷 / 1 = 检出夹具缺陷 / 2 = 器具缺陷(输入缺失或字段不可解析, fail-closed) / 3 = 缺侧。
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys

# ---- 声明式词表 (仪器读契约; 改词表 = 改仪器, 必须重跑负控阶梯) ---------------------------
DEFAULT_MARKERS = ("缺省", "默认", "未提供", "未指定", "未给出", "省略时", "回落到", "不得要求该选项必填")
OPTIONAL_MARKERS = ("可选", "可省")
SUBPROCESS_FNS = ("run", "Popen", "call", "check_output", "check_call")
OPTION_RE = re.compile(r"`(--[a-z][a-z0-9-]*)")
# 题面里的**裸**选项形态 (未加反引号, 如 `--status open|done` / `--port {int}`) 也必须被读到,
# 否则「题面写明了却被判未声明」= 器具假红 (R514 首跑实测: --status 假红 5 处)。
OPTION_BARE_RE = re.compile(r"(?<![\w`-])(--[a-z][a-z0-9-]*)")
VALUE_PLACEHOLDER_RE = re.compile(r"\s*=?\s*[<{]")
SPLIT_RE = re.compile(r"[\n。；;]")


class InstrumentError(Exception):
    pass


def _sentences(text):
    return [s for s in SPLIT_RE.split(text) if s.strip()]


def _bracketed(sentence, pos):
    """该位置是否位于一对方括号内 (最近的 '[' 在最近的 ']' 之后)。"""
    return sentence.rfind("[", 0, pos) > sentence.rfind("]", 0, pos)


def parse_statement(prompt):
    """从题面抽选项事实。反引号形态与裸形态都读 (禁把题面写明的东西判成未声明)。"""
    opts = {}
    for s in _sentences(prompt):
        occ = {}
        for m in OPTION_RE.finditer(s):
            occ[m.start(1)] = m.group(1)
        for m in OPTION_BARE_RE.finditer(s):
            occ.setdefault(m.start(1), m.group(1))
        for pos, opt in sorted(occ.items()):
            value_taking = bool(VALUE_PLACEHOLDER_RE.match(s[pos + len(opt):pos + len(opt) + 12]))
            rec = opts.setdefault(opt, {"opt": opt, "value_taking": False, "optional_marked": False,
                                        "default_marked": False, "occurrences": 0})
            rec["occurrences"] += 1
            rec["value_taking"] = rec["value_taking"] or value_taking
            if _bracketed(s, pos) or any(k in s for k in OPTIONAL_MARKERS):
                rec["optional_marked"] = True
            if any(k in s for k in DEFAULT_MARKERS):
                rec["default_marked"] = True
    return opts


def _argv_of(call):
    """调用实参 → (argv, literal)。列表/元组展平; args= 关键字展平。"""
    argv, literal = [], True
    for a in list(call.args):
        if isinstance(a, (ast.List, ast.Tuple)):
            for e in a.elts:
                if isinstance(e, ast.Constant) and isinstance(e.value, str):
                    argv.append(e.value)
                else:
                    argv.append("<expr>")
                    literal = False
        elif isinstance(a, ast.Constant) and isinstance(a.value, str):
            argv.append(a.value)
        else:
            argv.append("<expr>")
            literal = False
    for kw in call.keywords:
        if kw.arg == "args" and isinstance(kw.value, (ast.List, ast.Tuple)):
            for e in kw.value.elts:
                argv.append(e.value if isinstance(e, ast.Constant) and isinstance(e.value, str) else "<expr>")
    return argv, literal


def parse_cases(path):
    src = open(path, encoding="utf-8", errors="replace").read()
    tree = ast.parse(src)
    # --- 子进程触达自检 (读契约的前提: 这个文件确实在驱动被测进程) ---
    if not [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr in SUBPROCESS_FNS]:
        raise InstrumentError("用例文件里找不到子进程调用 ⇒ 解析契约不成立")
    # --- 用例清单: ①模块级注册表 (被 for 迭代的函数名列表) ②表形态 ③变换形态 ---
    k = None
    for n in ast.walk(tree):
        if (isinstance(n, ast.Subscript) and isinstance(n.value, ast.Attribute)
                and n.value.attr == "__name__" and isinstance(n.slice, ast.Slice)
                and isinstance(n.slice.lower, ast.Constant) and isinstance(n.slice.lower.value, int)
                and n.slice.upper is None):
            k = n.slice.lower.value
    registry = None
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                and isinstance(n.value, (ast.List, ast.Tuple)) and n.value.elts \
                and all(isinstance(e, ast.Name) for e in n.value.elts):
            tgt = n.targets[0].id
            if any(isinstance(x, ast.For) and isinstance(x.iter, ast.Name) and x.iter.id == tgt
                   for x in tree.body):
                registry = [e.id for e in n.value.elts]
    table = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                and isinstance(n.value, (ast.List, ast.Tuple)):
            pairs = []
            for e in n.value.elts:
                if (isinstance(e, ast.Tuple) and len(e.elts) == 2
                        and isinstance(e.elts[0], ast.Constant) and isinstance(e.elts[0].value, str)
                        and isinstance(e.elts[1], ast.Name)):
                    pairs.append((e.elts[0].value, e.elts[1].id))
            if pairs:
                table = {nm: fn for nm, fn in pairs}
    if table:
        case_names, form = table, "table"
    elif registry is not None and k is not None:
        case_names, form = {fname[k:]: fname for fname in registry}, "transform+registry"
    elif k is not None:
        raise InstrumentError("用例文件有变换常量但无注册表/声明表 ⇒ 无法确定用例全集 ⇒ fail-closed")
    else:
        raise InstrumentError("用例文件里既无 X.__name__[k:] 变换也无 CASES 声明表 ⇒ 解析契约不成立")
    # --- 作用域表 ---
    scope_of = {}
    for f in ast.walk(tree):
        if isinstance(f, ast.FunctionDef):
            for n in ast.walk(f):
                scope_of.setdefault(id(n), f.name)
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        for m in [x for x in cls.body if isinstance(x, ast.FunctionDef)]:
            for n in ast.walk(m):
                scope_of[id(n)] = "%s.%s" % (cls.name, m.name)
    # --- 调用点 = 含字面选项 token 的调用 ---
    all_calls = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            argv, literal = _argv_of(n)
            if any(t.startswith("--") for t in argv):
                all_calls.append({"node": n, "argv": argv, "literal": literal,
                                  "scope": scope_of.get(id(n), "?"), "callee": ast.unparse(n.func)[:60]})
    if not all_calls:
        raise InstrumentError("用例文件里找不到含选项 token 的调用点 ⇒ 解析契约不成立")
    # --- 用例函数名集合 ---
    fn_names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    if table:
        case_names = table
    else:
        case_names = {f[3:]: f for f in fn_names if f.startswith("test_")} if all(
            f.startswith("test_") for f in fn_names) else {}
        if not case_names:  # 变换形态但无统一前缀 ⇒ 以变换常量派生全部顶层 def (排除跑器)
            case_names = {f[k:]: f for f in fn_names if f != "case"}
    # --- 零退出码断言 (传递闭包) ---
    fn_by_name = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}

    def has_zero_rc(fn_name, seen=None):
        seen = seen or set()
        if fn_name in seen or fn_name not in fn_by_name:
            return False
        seen.add(fn_name)
        for n in ast.walk(fn_by_name[fn_name]):
            if isinstance(n, ast.Compare) and any(isinstance(c, ast.Constant) and c.value == 0
                                                  for c in n.comparators):
                return True
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and has_zero_rc(n.func.id, seen):
                return True
        return False

    # --- 输出面键: 解码助手赋值的变量及其下标派生 ---
    decode_fns = {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and any(
        isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and x.func.attr in ("loads", "load")
        for x in ast.walk(n))}

    def rooted(node, names):
        while True:
            if isinstance(node, ast.Name):
                return node.id in names
            if isinstance(node, (ast.Subscript, ast.Attribute)):
                node = node.value
                continue
            return False

    def decoded_names(fn):
        names, changed = set(), True
        while changed:
            changed = False
            for n in ast.walk(fn):
                if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                    v = n.value
                    hit = isinstance(v, ast.Call) and (
                        (isinstance(v.func, ast.Name) and v.func.id in decode_fns)
                        or (isinstance(v.func, ast.Attribute) and v.func.attr in ("loads", "load")))
                    if not hit and isinstance(v, ast.Subscript):
                        hit = rooted(v.value, names)
                    if hit and n.targets[0].id not in names:
                        names.add(n.targets[0].id)
                        changed = True
        return names

    cases = []
    for name, fname in case_names.items():
        fn = fn_by_name.get(fname)
        if fn is None:
            raise InstrumentError("用例表声明的函数 %r 在文件里找不到 ⇒ 解析契约不成立" % fname)
        dec = decoded_names(fn)
        keys = sorted({x.slice.value for x in ast.walk(fn)
                       if isinstance(x, ast.Subscript) and isinstance(x.slice, ast.Constant)
                       and isinstance(x.slice.value, str) and rooted(x.value, dec)})
        cases.append({"func": fname, "name": name, "zero_rc": has_zero_rc(fname), "output_keys": keys,
                      "call_ids": [id(c["node"]) for c in all_calls
                                   if scope_of.get(id(c["node"])) == fname]})
    case_fn_names = {c["func"] for c in cases}
    spawn_sites = [{"scope": c["scope"], "argv": c["argv"]} for c in all_calls
                   if c["scope"] not in case_fn_names]
    err_tokens = set()
    for n in ast.walk(tree):
        if not isinstance(n, ast.Compare):
            continue
        left = n.left
        is_error_read = ((isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute)
                          and left.func.attr == "get" and left.args
                          and isinstance(left.args[0], ast.Constant) and left.args[0].value == "error")
                         or (isinstance(left, ast.Subscript) and isinstance(left.slice, ast.Constant)
                             and left.slice.value == "error"))
        if is_error_read:
            for c in n.comparators:
                if isinstance(c, ast.Constant) and isinstance(c.value, str):
                    err_tokens.add(c.value)
    by_id = {id(c["node"]): c for c in all_calls}
    for c in cases:
        c["calls"] = [by_id[i] for i in c["call_ids"]]
    return {"cases": cases, "spawn_sites": spawn_sites, "case_name_k": k, "form": form,
            "error_tokens": sorted(err_tokens), "json_keys": sorted({k2 for c in cases for k2 in c["output_keys"]}),
            "case_file": path,
            "case_sha256": hashlib.sha256(src.encode("utf-8", "replace")).hexdigest()}


def check_task(task, base_dir):
    prompt = task.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise InstrumentError("task %r 缺 prompt 字段 ⇒ 器具缺陷" % task.get("tid"))
    cases_rel = task.get("cases")
    if not isinstance(cases_rel, str) or not cases_rel:
        raise InstrumentError("task %r 缺 cases 字段 ⇒ 器具缺陷" % task.get("tid"))
    cases_path = os.path.join(base_dir, cases_rel)
    if not os.path.isfile(cases_path):
        raise FileNotFoundError(cases_path)
    info = parse_cases(cases_path)
    opts = parse_statement(prompt)
    used_options, defects, infos = set(), [], []

    def scan(scope, argv, subclass=None):
        present = [t for t in argv if t.startswith("--")]
        for o in present:
            used_options.add(o)
            if o not in opts:
                defects.append({"kind": "case_uses_option_not_in_statement", "case": scope,
                                "option": o, "argv": argv})
        for o, rec in opts.items():
            if o in present:
                continue
            if not (rec["value_taking"] and not rec["optional_marked"] and not rec["default_marked"]):
                continue
            defects.append({"kind": "reliance_on_unstated_default", "case": scope, "option": o,
                            "argv": argv, "subclass": subclass})

    for c in info["cases"]:
        if not c["calls"]:
            infos.append({"kind": "case_without_direct_call", "case": c["name"]})
        for call in c["calls"]:
            scan(c["name"], call["argv"], "binding" if c["zero_rc"] else "masked")
    for sp in info["spawn_sites"]:
        scan(sp["scope"], sp["argv"], "spawn_site")
    for t in info["error_tokens"]:
        if t not in prompt:
            defects.append({"kind": "undeclared_error_token", "token": t})
    for key in info["json_keys"]:
        if key not in prompt:
            defects.append({"kind": "undeclared_json_key", "key": key})
    for o in sorted(opts):
        if o not in used_options:
            infos.append({"kind": "statement_option_unexercised", "option": o})
    for t in re.findall(r'"error"\s*:\s*"([a-z_]+)"', prompt):
        if t not in info["error_tokens"]:
            infos.append({"kind": "statement_error_token_unexercised", "token": t})
    d2 = [d for d in defects if d["kind"] == "reliance_on_unstated_default"]
    return {"tid": task.get("tid"),
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "cases_sha256": info["case_sha256"], "case_name_form": info["form"],
            "spawn_sites": info["spawn_sites"],
            "statement_options": {kk: {a: b for a, b in v.items() if a != "opt"} for kk, v in opts.items()},
            "cases_total": len(info["cases"]), "cases_with_calls": sum(1 for c in info["cases"] if c["calls"]),
            "defects": defects, "info": infos,
            "predicted_binding_failures": sorted({d["case"] for d in d2 if d["subclass"] == "binding"}),
            "defect_masked_by_error_path": sorted({d["case"] for d in d2 if d["subclass"] == "masked"}),
            "defect_spawn_scope": sorted({d["case"] for d in d2 if d["subclass"] == "spawn_site"}),
            "defect_kinds": sorted({d["kind"] for d in defects}),
            "verdict": "FIXTURE_DEFECT" if defects else "OK"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--taskset", required=True)
    ap.add_argument("--json")
    ap.add_argument("--tid", action="append")
    a = ap.parse_args()
    out = {"taskset": os.path.abspath(a.taskset), "tasks": [], "verdict": "OK"}
    try:
        ts = json.load(open(a.taskset, encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        print("[器具缺陷 rc=2] taskset 不可解析: %s" % exc)
        return 2
    if not isinstance(ts.get("tasks"), list) or not ts["tasks"]:
        print("[器具缺陷 rc=2] taskset 缺 tasks 数组 ⇒ fail-closed")
        return 2
    base = os.path.dirname(os.path.abspath(a.taskset))
    for t in ts["tasks"]:
        if a.tid and t.get("tid") not in a.tid:
            continue
        try:
            out["tasks"].append(check_task(t, base))
        except FileNotFoundError as exc:
            print("[缺侧 rc=3] task %s 的用例文件不存在: %s" % (t.get("tid"), exc))
            return 3
        except (InstrumentError, SyntaxError) as exc:
            print("[器具缺陷 rc=2] task %s: %s" % (t.get("tid"), exc))
            return 2
    if any(t["verdict"] != "OK" for t in out["tasks"]):
        out["verdict"] = "FIXTURE_DEFECT"
    for t in out["tasks"]:
        print("task %-4s form=%-9s cases=%d/%d violations=%d binding=%d masked=%d spawn=%d info=%d kinds=%s"
              % (t["tid"], t["case_name_form"], t["cases_with_calls"], t["cases_total"], len(t["defects"]),
                 len(t["predicted_binding_failures"]), len(t["defect_masked_by_error_path"]),
                 len(t["defect_spawn_scope"]), len(t["info"]), ",".join(t["defect_kinds"]) or "-"))
        for d in t["defects"]:
            print("   DEFECT %-34s %s" % (d["kind"], json.dumps({k2: v for k2, v in d.items() if k2 != "kind"},
                                                                 ensure_ascii=False)[:220]))
        for i in t["info"]:
            print("   info   %-34s %s" % (i["kind"], json.dumps({k2: v for k2, v in i.items() if k2 != "kind"},
                                                                ensure_ascii=False)[:160]))
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(out, ensure_ascii=False, indent=1))
    return 1 if out["verdict"] != "OK" else 0


if __name__ == "__main__":
    raise SystemExit(main())
