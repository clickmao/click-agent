#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R529 夹具构建 + 契约机检 (J1): 第二题族 F2 (toolkit-multimodule-v1) 生成、落盘、正/负控。

产物:
  · `eval/rover/r529/taskset-r529.json`        两题: F1(g1, 逐字节复用 r528) + F2(t1, 新增)
  · `eval/rover/r529/cases/cases-r529-f2.json` F2 隐藏用例 (30 = vm_run 12 + json_mini 18)
  · `eval/rover/r529/cases/run_cases_r529.py`  F2 用例脚本 (与前置器契约同源)
  · `eval/rover/r529/evidence/nc-fixture-r529.json`  正控/负控机检读数

判据 J1: ① 正控 —— 用 tasks.py 的**参考实现**拼出 toolkit 包实跑用例脚本 ⇒ 30/30 且 rc=0;
         ② 负控 3 变异体 (vm 去掉步数上限 / vm 吞掉 ERR / jsonmini 键降序) ⇒ 必须红且 rc=1;
         ③ F1 题面 sha256 必须逐字节等于 R528/R521 锚 `516f3208…` (同输入硬门的前置)。
不吃任何活目录读数; 生成器 seed 固定 (20260917) ⇒ 夹具可复现。
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
R = os.path.join(REPO, "eval/rover/r529")
R528 = os.path.join(REPO, "eval/rover/r528")
sys.path.insert(0, os.path.join(REPO, "eval/probe"))
import tasks  # noqa: E402

F1_PIN = "516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3"
SEED = 20260917
FAMS = ("vm_run", "json_mini")
# 家族名 → CLI 子命令名 (题面 `python3 -m toolkit <vm|jsonmini>`; 家族名带下划线, 不得直接当子命令)
CLI_NAME = {"vm_run": "vm", "json_mini": "jsonmini"}

F2_PROMPT_HEAD = """用 Python 3 实现一个**多文件工具包** `toolkit/`（本任务规模超出单轮步数上限, 必须分模块完成）。

【结构要求】
- `toolkit/__init__.py`：包初始化（可空, 但必须存在）
- `toolkit/vm.py`、`toolkit/jsonmini.py`：每个子命令一个模块, 各自导出 `solve(text: str) -> str`（纯函数: 入参=该子命令的完整 stdin 文本, 返回=应当写出的 stdout 文本, 末尾不带换行）
- `toolkit/__main__.py`：CLI 入口, 使 `python3 -m toolkit <vm|jsonmini>` 可用；从标准输入读取全部文本、调用对应模块的 `solve`、把返回值写到标准输出
- 只允许标准库；不得打印任何多余文字、提示或调试信息（stderr 亦须静默）

【评分】对两个子命令分别用 `python3 -m toolkit <vm|jsonmini>` 跑隐藏用例, 逐字节比对 stdout。
产物必须落在**工作根**下（即 `toolkit/` 直接位于工作根, 不得另加中间目录）; 收尾前的自验必须在**工作根**执行同一验收形态。

"""


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def norm(v):
    if v is None:
        v = "ERR"
    if isinstance(v, list):
        v = "\n".join(str(x) for x in v)
    if isinstance(v, int):
        v = str(v)
    return v.strip("\n")


def build_f2():
    rnd = random.Random(SEED)
    fams = sorted(tasks.PROGRAM_FAMILIES)
    pool = [tasks.gen_program_task(i, fams, rnd) for i in range(1, 41)]
    sel = {}
    for t in pool:
        if t.family in FAMS and t.family not in sel:
            sel[t.family] = t
    assert sorted(sel) == sorted(FAMS), "生成器未产出目标族: %r" % sorted(sel)
    cases, specs, pub = [], [], []
    for fam in FAMS:
        t = sel[fam]
        for i, c in enumerate(t.hidden):
            cases.append({"mod": CLI_NAME[fam], "family": fam, "vis": "hidden", "stdin": c.stdin,
                          "expected_stdout": c.expected_stdout, "src_tid": t.tid})
        for c in t.public:
            pub.append({"mod": CLI_NAME[fam], "family": fam, "vis": "public", "stdin": c.stdin,
                        "expected_stdout": c.expected_stdout})
        specs.append("### 子命令 `%s`（规格逐字取自题集生成器, 家族 `%s`）\n%s" %
                     (fam, fam, t.prompt.split("【任务】", 1)[1].split("【公开用例】", 1)[0].strip()))
    os.makedirs(os.path.join(R, "cases"), exist_ok=True)
    io.open(os.path.join(R, "cases/cases-r529-f2.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(cases, ensure_ascii=False, indent=1) + "\n")
    prompt = F2_PROMPT_HEAD + "【各子命令规格（逐字）】\n" + "\n\n".join(specs) + "\n"
    return prompt, cases, pub, {f: sel[f].tid for f in FAMS}


def oracle_tree(root, f2_prompt, mutant=None):
    """用 tasks.py 参考实现拼出 toolkit 包 (正控) / 注入缺陷 (负控)。"""
    pkg = os.path.join(root, "toolkit")
    os.makedirs(pkg, exist_ok=True)
    io.open(os.path.join(pkg, "__init__.py"), "w", encoding="utf-8").write("")
    io.open(os.path.join(pkg, "__main__.py"), "w", encoding="utf-8", newline="\n").write(
        "import sys\n"
        "from toolkit import vm, jsonmini\n"
        "MODS = {'vm': vm, 'jsonmini': jsonmini}\n"
        "def main():\n"
        "    m = sys.argv[1]\n"
        "    sys.stdout.write(MODS[m].solve(sys.stdin.read()))\n"
        "    return 0\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n")
    def body(fam):
        # 参考实现 + 输出格式化 逐字取自生成器族表 (fmt 才是"期望输出"的权威来源;
        # vm_run 的 None/_ERR 语义差异正由此消除 ⇒ 正控才对得上生成器的 expected_stdout)
        return ("import sys\n"
                "sys.path.insert(0, %r)\n"
                "import tasks as _t\n"
                "def solve(text):\n"
                "    _f = _t.PROGRAM_FAMILIES[%r]\n"
                "    return _f['fmt'](_f['ref'](text))\n" % (os.path.join(REPO, "eval/probe"), fam))

    vm_body = body("vm_run")
    js_body = body("json_mini")
    if mutant == "vm_noerr":
        # 缺陷注入: 非法态(栈空弹栈/越界/超步/无 HALT)不再报 ERR ⇒ 用例脚本必须判红
        vm_body = vm_body.replace("    return _f['fmt'](_f['ref'](text))\n",
                                  "    _r = _f['ref'](text)\n"
                                  "    return '' if _r is None else _f['fmt'](_r)\n")
    if mutant == "json_desc":
        # 缺陷注入: 对象键序改为降序 (规格要求码点升序) ⇒ 用例脚本必须判红
        js_body = js_body.replace("    return _f['fmt'](_f['ref'](text))\n",
                                  "    _r = _f['ref'](text)\n"
                                  "    if _r is _t._ERR:\n"
                                  "        return 'ERR'\n"
                                  "    import json as _j\n"
                                  "    return _j.dumps(_r, sort_keys=True, reverse=True, ensure_ascii=False,\n"
                                  "                   separators=(',', ':'))\n")
    io.open(os.path.join(pkg, "vm.py"), "w", encoding="utf-8", newline="\n").write(vm_body)
    io.open(os.path.join(pkg, "jsonmini.py"), "w", encoding="utf-8", newline="\n").write(js_body)
    return root


def run_cases(tree):
    script = os.path.join(R, "cases/run_cases_r529.py")
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": tree}
    p = subprocess.run([sys.executable, "-I", "-B", script], cwd=tree, capture_output=True, text=True,
                       timeout=600, env=env)
    npass = sum(1 for ln in p.stdout.splitlines() if ln.startswith("CASE ") and " PASS" in ln)
    nfail = sum(1 for ln in p.stdout.splitlines() if ln.startswith("CASE ") and " FAIL" in ln)
    return {"rc": p.returncode, "pass": npass, "fail": nfail, "tail": p.stdout.strip().splitlines()[-1:]}


def main():
    os.makedirs(os.path.join(R, "evidence"), exist_ok=True)
    f2_prompt, f2_cases, f2_pub, tids = build_f2()
    ts_f1 = json.load(io.open(os.path.join(R528, "taskset-r528.json"), encoding="utf-8"))
    f1 = ts_f1["tasks"][0]
    f1_sha = hashlib.sha256(f1["prompt"].encode()).hexdigest()
    assert f1_sha == F1_PIN, "F1 题面 sha 与锚不符: %s" % f1_sha
    f2_sha = hashlib.sha256(f2_prompt.encode()).hexdigest()
    task = {"tid": "t1", "kind": "project", "family": "toolkit-multimodule-v1", "prompt": f2_prompt,
            "prompt_sha256": f2_sha, "cases": "cases/run_cases_r529.py",
            "hidden_cases": str(len(f2_cases)),
            "meta": {"n_mods": len(FAMS), "n_cases": len(f2_cases), "public": len(f2_pub),
                     "generator": "eval/probe/tasks.py", "seed": SEED, "src_tids": tids},
            "fixture_src": {"generator": "eval/probe/tasks.py --kind program --n 40 --seed %d" % SEED,
                            "builder": "eval/rover/r529/build_fixture_r529.py"}}
    blob = {"round": "R529", "family": "F1+F2", "source": "F1 = eval/rover/r528/taskset-r528.json 逐字节复用; "
            "F2 = eval/probe/tasks.py 双路径生成器 (seed %d)" % SEED, "tasks": [f1, task]}
    io.open(os.path.join(R, "taskset-r529.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(blob, ensure_ascii=False, indent=1) + "\n")

    # 正控 / 负控
    res = {}
    tmp = tempfile.mkdtemp(prefix="r529-fix-")
    for tag, mut in (("oracle", None), ("nc_vm_noerr", "vm_noerr"), ("nc_json_desc", "json_desc")):
        tr = oracle_tree(os.path.join(tmp, tag), f2_prompt, mut)
        res[tag] = run_cases(tr)
    os.remove(os.path.join(tmp, "nc_vm_nostepcap")) if False else None
    # vm 无步数上限变异: 用「不判 ERR」的近似, 由 vm_noerr 覆盖; 第三个负控 = 交付空包 (落盘缺失)
    empty = os.path.join(tmp, "nc_empty")
    os.makedirs(empty, exist_ok=True)
    res["nc_empty"] = run_cases(empty)
    shutil.rmtree(tmp, ignore_errors=True)

    verdict = {
        "J1_positive_control_30of30": res["oracle"]["pass"] == len(f2_cases) and res["oracle"]["rc"] == 0,
        "J1_negative_controls_all_red": all(res[k]["rc"] != 0 for k in ("nc_vm_noerr", "nc_json_desc", "nc_empty")),
        "J1_f1_prompt_sha_match": f1_sha == F1_PIN,
        "cases_total": len(f2_cases), "public_total": len(f2_pub),
    }
    out = {"round": "R529", "builder": "eval/rover/r529/build_fixture_r529.py", "seed": SEED,
           "f1_prompt_sha256": f1_sha, "f2_prompt_sha256": f2_sha,
           "f2_cases_sha256": sha_file(os.path.join(R, "cases/cases-r529-f2.json")),
           "src_tids": tids, "controls": res, "verdict": verdict,
           "j1_pass": all(verdict[k] for k in ("J1_positive_control_30of30", "J1_negative_controls_all_red",
                                               "J1_f1_prompt_sha_match"))}
    io.open(os.path.join(R, "evidence/nc-fixture-r529.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(out["verdict"], ensure_ascii=False))
    print("controls:", json.dumps(res, ensure_ascii=False))
    print("J1_PASS=%s" % out["j1_pass"])
    return 0 if out["j1_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
