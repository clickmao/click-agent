#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R531 夹具构建 + 契约机检 (J1): 第三题族 F3 (mathkit-multimodule-v1) 生成、落盘、正/负控。

产物:
  · `eval/rover/r531/taskset-r531.json`          三题: F1(g1)/F2(t1) 逐字节复用 r529 + F3(m1, 新增)
  · `eval/rover/r531/cases/cases-r531-f3.json`   F3 隐藏用例 (30 = 5 op × 6)
  · `eval/rover/r531/evidence/nc-fixture-r531.json`  正控/负控机检读数

判据 J1:
  ① 正控 —— 用 tasks.py 的**参考实现** (ref + fmt) 拼出 mathkit 包实跑用例脚本 ⇒ 30/30 且 rc=0;
  ② 负控 4 变异体 (qr_count 差一 / choose 不取模 / 输出带前缀 / 交付空包) ⇒ 必须红且 rc=1;
  ③ F1/F2 题面 sha256 必须逐字节等于 R529 锚 (同输入硬门的前置)。
不吃任何活目录读数; 生成器 seed 固定 (531) ⇒ 夹具可复现。
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r531")
R529 = os.path.join(REPO, "eval/rover/r529")
sys.path.insert(0, R)
sys.path.insert(0, os.path.join(REPO, "eval/probe"))
import tasks  # noqa: E402
import op_contract_r531 as C  # noqa: E402

SEED = 531
OPS = ["qr_count", "choose", "det", "shortest", "expect"]   # 固定顺序 ⇒ 可复现
N_HIDDEN_PER_OP = 6
N_PUBLIC_PER_OP = 1

F3_PROMPT_HEAD = """用 Python 3 实现一个**多文件数学工具包** `mathkit/`（本任务规模超出单轮步数上限, 必须分模块完成）。

【结构要求】
- `mathkit/__init__.py`：包初始化（可空, 但必须存在）
- `mathkit/modular.py`、`mathkit/linear.py`、`mathkit/graphs.py`、`mathkit/prob.py`：每个模块导出一组**纯函数**, 每个 op 一个函数, 签名 `op(args: dict) -> str`（返回应当写出的 stdout 文本, 末尾不带换行）; 各模块归属见下【各 op 规格】
- `mathkit/__main__.py`：CLI 入口, 使 `python3 -m mathkit <op>` 可用；**从标准输入读取一个 JSON 对象**作为参数、调用对应模块的对应函数、把返回值写到标准输出
- 只允许标准库；不得打印任何多余文字、提示或调试信息（stderr 亦须静默）
- 输出**恰好一行**, 只含答案本身（整数 / `-1` / 最简分数 `p/q`），无前缀、无空格、无单位

【评分】对每个 op 分别用 `python3 -m mathkit <op>` 跑隐藏用例（参数以 JSON 从 stdin 传入），逐字节比对 stdout。
产物必须落在**工作根**下（即 `mathkit/` 直接位于工作根, 不得另加中间目录）; 收尾前的自验必须在**工作根**执行同一验收形态。

【各 op 规格（逐字取自本夹具契约表）】
"""


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def build_f3():
    """按 op 生成 30 隐藏 + 5 公开用例; 期望值 = ref 路径, 并当场用 check 路径核对 (双路径机检)。"""
    rnd = random.Random(SEED)
    cases, pub, specs, dual_ok, dual_tot = [], [], [], 0, 0
    for op in OPS:
        meta = C.OP_TABLE[op]
        fam = meta["family"]
        f = tasks.MATH_FAMILIES[fam]
        seen, made = set(), []
        budget = (N_HIDDEN_PER_OP + N_PUBLIC_PER_OP) * 6
        while len(made) < N_HIDDEN_PER_OP + N_PUBLIC_PER_OP and budget > 0:
            budget -= 1
            params = f["gen"](rnd)
            args = _params_to_args(op, params)
            key = json.dumps(args, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            exp_ref = f["fmt"](params, f["ref"](params))
            exp_chk = f["fmt"](params, f["check"](params))
            dual_tot += 1
            if exp_ref != exp_chk:                     # fail-closed: 双路径不一致 ⇒ 直接不产出
                raise SystemExit("ORACLE_DRIFT %s: ref=%r check=%r" % (op, exp_ref, exp_chk))
            dual_ok += 1
            made.append({"mod": meta["mod"], "op": op, "family": fam, "args": args, "exp": exp_ref})
        if len(made) < N_HIDDEN_PER_OP + N_PUBLIC_PER_OP:
            raise SystemExit("用例生成不足: %s (%d)" % (op, len(made)))
        pub.append(dict(made[0], vis="public"))
        for j, c in enumerate(made[1:]):
            cases.append({"mod": c["mod"], "op": op, "family": fam, "vis": "hidden",
                          "args": c["args"], "expected_stdout": c["exp"]})
        specs.append("### op `%s`（模块 `%s`, 家族 `%s`）\n%s\n入参字段: %s\n公开用例:\n  输入(JSON): %s\n  期望输出: `%s`"
                     % (op, meta["mod"], fam, meta["spec"], meta["fields"],
                        json.dumps(pub[-1]["args"], ensure_ascii=False), pub[-1]["exp"]))
    os.makedirs(os.path.join(R, "cases"), exist_ok=True)
    io.open(os.path.join(R, "cases/cases-r531-f3.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(cases, ensure_ascii=False, indent=1) + "\n")
    prompt = (F3_PROMPT_HEAD + "\n\n".join(specs) +
              "\n\n【模块归属一览】\n" +
              "\n".join("- `mathkit/%s.py`：%s" % (m, ", ".join("`%s`" % o for o in ops))
                        for m, ops in C.MODULES.items()) + "\n")
    return prompt, cases, pub, {"dual_pairs_ok": dual_ok, "dual_pairs_total": dual_tot}


def _params_to_args(op, params):
    """params 元组 → JSON 入参 (契约表 `params` 的逆映射; 逆映射只在夹具侧, 不入契约)。"""
    if op == "qr_count":
        return {"a": params[0], "m": params[1]}
    if op == "choose":
        return {"n": params[0], "k": params[1], "mod": params[2]}
    if op == "det":
        return {"matrix": params[0], "mod": params[1]}
    if op == "shortest":
        return {"matrix": params[0], "src": params[1], "dst": params[2]}
    if op == "expect":
        return {"red": params[0], "blue": params[1], "draw": params[2]}
    raise SystemExit("未知 op: %s" % op)


def oracle_tree(root, mutant=None):
    """用 tasks.py 参考实现拼出 mathkit 包 (正控) / 注入缺陷 (负控)。"""
    pkg = os.path.join(root, "mathkit")
    os.makedirs(pkg, exist_ok=True)
    io.open(os.path.join(pkg, "__init__.py"), "w", encoding="utf-8").write("")
    main_src = (
        "import json, sys\n"
        "from mathkit import modular, linear, graphs, prob\n"
        "MOD = {'modular': modular, 'linear': linear, 'graphs': graphs, 'prob': prob}\n"
        "OP2MOD = {'qr_count': 'modular', 'choose': 'modular', 'det': 'linear',\n"
        "          'shortest': 'graphs', 'expect': 'prob'}\n"
        "def main():\n"
        "    op = sys.argv[1]\n"
        "    args = json.loads(sys.stdin.read())\n"
        "    out = getattr(MOD[OP2MOD[op]], op)(args)\n"
        "    sys.stdout.write(out if out.endswith('\\n') else out + '\\n')\n"
        "    return 0\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n")
    if mutant == "extra_text":
        main_src = main_src.replace("    sys.stdout.write(out if out.endswith('\\n') else out + '\\n')\n",
                                    "    sys.stdout.write('ans=' + out)\n")
    io.open(os.path.join(pkg, "__main__.py"), "w", encoding="utf-8", newline="\n").write(main_src)

    def body(mod, ops):
        lines = ["import sys",
                 "sys.path.insert(0, %r)" % os.path.join(REPO, "eval/probe"),
                 "sys.path.insert(0, %r)" % R,
                 "import tasks as _t",
                 "import op_contract_r531 as _C",
                 "",
                 "def _ans(op, args):",
                 "    f = _t.MATH_FAMILIES[_C.OP_TABLE[op]['family']]",
                 "    p = _C.to_params(op, args)",
                 "    return f['fmt'](p, f['ref'](p))",
                 ""]
        for op in ops:
            lines += ["def %s(args):" % op, "    return _ans(%r, args)" % op, ""]
        return "\n".join(lines)

    mods = {m: body(m, ops) for m, ops in C.MODULES.items()}
    if mutant == "qr_offby1":
        mods["modular"] = mods["modular"].replace(
            "def qr_count(args):\n    return _ans('qr_count', args)",
            "def qr_count(args):\n    return str(int(_ans('qr_count', args)) + 1)")
    if mutant == "choose_nomod":
        mods["modular"] = mods["modular"].replace(
            "def choose(args):\n    return _ans('choose', args)",
            "def choose(args):\n    import math as _m\n    return str(_m.comb(int(args['n']), int(args['k'])))")
    for m, src in mods.items():
        io.open(os.path.join(pkg, "%s.py" % m), "w", encoding="utf-8", newline="\n").write(src)
    return root


def run_cases(tree):
    script = os.path.join(R, "cases/run_cases_r531_math.py")
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": tree}
    p = subprocess.run([sys.executable, "-I", "-B", script], cwd=tree, capture_output=True, text=True,
                       timeout=600, env=env)
    npass = sum(1 for ln in p.stdout.splitlines() if ln.startswith("CASE ") and " PASS" in ln)
    nfail = sum(1 for ln in p.stdout.splitlines() if ln.startswith("CASE ") and " FAIL" in ln)
    pairs = [ln for ln in p.stdout.splitlines() if ln.startswith("R531_ORACLE_PAIRS ")]
    return {"rc": p.returncode, "pass": npass, "fail": nfail, "pairs": pairs[-1:] or [],
            "tail": p.stdout.strip().splitlines()[-1:]}


def main():
    os.makedirs(os.path.join(R, "evidence"), exist_ok=True)
    f3_prompt, f3_cases, f3_pub, dual = build_f3()
    ts529 = json.load(io.open(os.path.join(R529, "taskset-r529.json"), encoding="utf-8"))
    f1, f2 = ts529["tasks"][0], ts529["tasks"][1]
    f1_sha = hashlib.sha256(f1["prompt"].encode()).hexdigest()
    f2_sha = hashlib.sha256(f2["prompt"].encode()).hexdigest()
    assert f1_sha == f1["prompt_sha256"], "F1 题面在 r529 内不自洽: %s" % f1_sha
    assert f2_sha == f2["prompt_sha256"], "F2 题面在 r529 内不自洽: %s" % f2_sha
    f3_sha = hashlib.sha256(f3_prompt.encode()).hexdigest()
    f3_task = {"tid": "m1", "kind": "project", "family": "mathkit-multimodule-v1", "prompt": f3_prompt,
               "prompt_sha256": f3_sha, "cases": "cases/run_cases_r531_math.py",
               "hidden_cases": str(len(f3_cases)),
               "meta": {"n_mods": len(C.MODULES), "n_ops": len(OPS), "n_cases": len(f3_cases),
                        "public": len(f3_pub), "generator": "eval/probe/tasks.py", "seed": SEED,
                        "oracle": "MATH_FAMILIES[*].ref (落盘) ⊕ [*].check (判分时刻重算)",
                        "dual_pairs": dual["dual_pairs_ok"]},
               "fixture_src": {"generator": "eval/probe/tasks.py MATH_FAMILIES (seed %d)" % SEED,
                               "builder": "eval/rover/r531/build_fixture_r531.py",
                               "contract": "eval/rover/r531/op_contract_r531.py"}}
    blob = {"round": "R531", "family": "F1+F2+F3",
            "source": "F1/F2 = eval/rover/r529/taskset-r529.json 逐字节复用 (同输入硬门); "
                      "F3 = eval/probe/tasks.py MATH_FAMILIES 双路径 (seed %d)" % SEED,
            "tasks": [f1, f2, f3_task]}
    io.open(os.path.join(R, "taskset-r531.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(blob, ensure_ascii=False, indent=1) + "\n")

    res = {}
    tmp = tempfile.mkdtemp(prefix="r531-fix-")
    for tag, mut in (("oracle", None), ("nc_qr_offby1", "qr_offby1"),
                     ("nc_choose_nomod", "choose_nomod"), ("nc_extra_text", "extra_text")):
        res[tag] = run_cases(oracle_tree(os.path.join(tmp, tag), mut))
    empty = os.path.join(tmp, "nc_empty")
    os.makedirs(empty, exist_ok=True)
    res["nc_empty"] = run_cases(empty)
    shutil.rmtree(tmp, ignore_errors=True)

    nc_keys = ("nc_qr_offby1", "nc_choose_nomod", "nc_extra_text", "nc_empty")
    verdict = {
        "J1_positive_control_30of30": res["oracle"]["pass"] == len(f3_cases) and res["oracle"]["rc"] == 0,
        "J1_negative_controls_all_red": all(res[k]["rc"] != 0 for k in nc_keys),
        "J1_reused_prompts_byte_identical": f1_sha == f1["prompt_sha256"] and f2_sha == f2["prompt_sha256"],
        "J1_dual_path_oracle_consistent": dual["dual_pairs_ok"] == dual["dual_pairs_total"] > 0,
        "cases_total": len(f3_cases), "public_total": len(f3_pub),
    }
    out = {"round": "R531", "builder": "eval/rover/r531/build_fixture_r531.py", "seed": SEED,
           "f1_prompt_sha256": f1_sha, "f2_prompt_sha256": f2_sha, "f3_prompt_sha256": f3_sha,
           "f3_cases_sha256": sha_file(os.path.join(R, "cases/cases-r531-f3.json")),
           "dual_path": dual, "controls": res, "verdict": verdict,
           "j1_pass": all(verdict[k] for k in ("J1_positive_control_30of30", "J1_negative_controls_all_red",
                                               "J1_reused_prompts_byte_identical",
                                               "J1_dual_path_oracle_consistent"))}
    io.open(os.path.join(R, "evidence/nc-fixture-r531.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(verdict, ensure_ascii=False))
    print("controls:", json.dumps(res, ensure_ascii=False))
    print("J1_PASS=%s" % out["j1_pass"])
    return 0 if out["j1_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
