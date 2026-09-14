#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""随机能力自检判定器 (R398 长期任务)

判定铁律
--------
1. **只认隐藏用例**: 公开用例从不参与判定 ⇒ "硬编码公开样例"的解法必然暴露。
2. **失败必须分类**: 只报"通过率"是空心指标; 必须给出失败模式分布 (no_code / syntax /
   runtime / timeout / wrong / partial), 否则无法归因、无法沉淀经验。
3. **判定器自身必须过负控**: 判定器若被注入"跳过比对"这类缺陷, 必须变红
   (见 `--selftest` 末三条反向负控)。判据不能自证。
4. **语言无关判据**: 判据 = (stdin, stdout) 二元关系; 沙箱只负责执行。

用法
----
    python3 eval/probe/grade.py --selftest
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable or "python3"
FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)
FINAL = re.compile(r"FINAL\s*:\s*(\S+)")

SANDBOX_ENV = {
    "PYTHONIOENCODING": "utf-8",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    "LC_ALL": "C.UTF-8",
}


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARTIFACT = re.compile(r"(?:\./)?data/artifacts/(py_[0-9a-f]+\.py)")
REPLY_MARK = "── 回复"


def _compiles(src: str) -> bool:
    try:
        compile(src, "<probe>", "exec")
        return True
    except SyntaxError:
        return False


def _prefixes(text: str):
    """由长到短逐行截断 (取最长可编译前缀): CLI 回复区尾部会混入状态行。"""
    lines = (text or "").rstrip().split("\n")
    for k in range(len(lines), 0, -1):
        yield "\n".join(lines[:k])


def _artifact_paths(paths):
    """R433: 显式产物路径 → 可读源码文本 (外部真值通道)。

    真机实测缺陷 (R433 冻结题集同 sha 复跑): 渲染后的对话转录里围栏/`__x__` 会被 TUI 吃掉,
    而产品侧已把**围栏源码**落盘为 `data/artifacts/py_*.py` 且遥测 `script_artifact` 记
    `compile_valid=true` ⇒ 判分必须优先取落盘产物, 否则取到带 TUI 装饰的转录片段被判
    `syntax_error` (假红)。本函数只做读取, 新鲜度/归属由调用方的窗口过滤保证。
    """
    out = []
    for p in (paths or []):
        if isinstance(p, dict):                      # 容错: 允许 {"path": ...} 记录
            p = p.get("path")
        if not p:
            continue
        full = p if os.path.isabs(p) else os.path.join(ROOT, str(p).lstrip("./"))
        try:
            if not os.path.exists(full):
                continue
            with open(full, encoding="utf-8", errors="replace") as fh:
                src = fh.read().strip("\n")
        except OSError:
            continue
        if src:
            out.append(src)
    return out


def candidates(reply: str, since: float = None, artifacts=None) -> list:
    """候选程序, 按产品真实交付形态多路收集 (真机教训 R398):
       ① 显式围栏代码块  ② CLI 回复区裸代码  ③ 回复中给出的落盘产物路径 (可加新鲜度门槛)
       ④ **显式产物路径** (R433: 遥测 `script_artifact` 落盘的源码 = 最硬的外部真值通道)
    """
    text = reply or ""
    out = _artifact_paths(artifacts)
    out += [b.strip("\n") for b in FENCE.findall(text)]
    idx = text.find(REPLY_MARK)
    if idx >= 0:
        seg = text[idx:].split("\n", 1)
        if len(seg) > 1 and seg[1].strip():
            out.append(seg[1].strip("\n"))
    for m in ARTIFACT.finditer(text):
        path = os.path.join(ROOT, m.group(0).lstrip("./"))
        if not os.path.exists(path):
            continue
        if since is not None and os.path.getmtime(path) + 1.0 < since:
            continue
        with open(path, encoding="utf-8") as fh:
            out.append(fh.read().strip("\n"))
    return out


MIN_PREFIX_CHARS = 64


def extract_code(reply: str, since: float = None, artifacts=None) -> str:
    """抽候选程序: ① 全候选里取**第一个可整体编译**者 (按长度降序);
    ② 都不行才退化为「最长可编译前缀」, 且前缀必须 >= MIN_PREFIX_CHARS;
    ③ 仍不行返回最长候选 (此时 syntax_error 才是真失败)。

    R417 实测缺陷: 首版是「逐候选取首个可编译前缀」⇒ 长回复下会把 10 KB 程序误判成
    46 字符的注释残片 (p001 记录 0/18, 真值 12/18)。故前缀回退必须**分两轮**且设长度下限。
    R433: `artifacts` = 遥测落盘产物路径 (外部真值) ⇒ 并入候选, 且在长度降序里天然优先。
    """
    cands = [c for c in candidates(reply, since, artifacts) if c and c.strip()]
    if not cands:
        return ""
    ordered = sorted(cands, key=len, reverse=True)
    for c in ordered:                      # 第一轮: 只看整体可编译
        if _compiles(c):
            return c
    best = ""                              # 第二轮: 允许前缀, 但要有实体长度
    for c in ordered:
        for pre in _prefixes(c):
            if len(pre) >= MIN_PREFIX_CHARS and _compiles(pre):
                if len(pre) > len(best):
                    best = pre
                break
    if best:
        return best
    return max(cands, key=len)


def extract_final(reply: str) -> str:
    hits = FINAL.findall(reply or "")
    return hits[-1].strip().strip("`.,;") if hits else ""


def run_code(code: str, stdin_text: str, timeout: float = 5.0) -> dict:
    """在隔离临时目录里跑候选程序。返回 {stdout, exit, timed_out, err, bad_encoding}。

    R419 修正: stdout/stderr **不得**按严格 UTF-8 解码 —— 被测程序可能打印坏字节
    (实测 0xe9 截断多字节 ⇒ UnicodeDecodeError 把整个臂打崩, EXIT=3)。
    判定器对坏字节只有两种合法反应: ① 如实记为该用例不过 (替换字符后比对必然不等);
    ② 显式标 `bad_encoding` 供分类。**不允许抛异常**。
    """
    work = tempfile.mkdtemp(prefix="probe_")
    try:
        src = os.path.join(work, "sol.py")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(code)
        try:
            p = subprocess.run([PY, "-I", "-B", src], input=(stdin_text or "").encode("utf-8"),
                               capture_output=True, timeout=timeout,
                               cwd=work, env=SANDBOX_ENV)
        except subprocess.TimeoutExpired:
            return {"stdout": "", "exit": -9, "timed_out": True, "err": "timeout",
                    "bad_encoding": False}
        except OSError as e:  # 解释器缺失等环境性问题: 显式出声, 不静默算失败
            return {"stdout": "", "exit": -1, "timed_out": False, "err": "oserror: %s" % e,
                    "bad_encoding": False}
        raw_out, raw_err = (p.stdout or b""), (p.stderr or b"")
        bad = False
        for raw in (raw_out, raw_err):
            try:
                raw.decode("utf-8")
            except UnicodeDecodeError:
                bad = True
        return {"stdout": raw_out.decode("utf-8", errors="replace"),
                "exit": p.returncode, "timed_out": False,
                "err": raw_err.decode("utf-8", errors="replace")[-400:],
                "bad_encoding": bad}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def norm(text: str) -> str:
    """输出比对归一: 去行尾空白 + 去末尾空行 (只容忍空白差异, 不容忍内容差异)。"""
    lines = [ln.rstrip() for ln in (text or "").replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _syntax_ok(code: str) -> bool:
    try:
        compile(code, "<sol>", "exec")
        return True
    except SyntaxError:
        return False


def grade_program(task: dict, reply: str, timeout: float = 5.0, since: float = None,
                  artifacts=None) -> dict:
    """返回 {mode, passed, total, detail[], taxonomy, code_source}。mode ∈ 上面铁律 2 的集合。

    since: 求解开始墙钟秒; 只接受**该时刻之后**落盘的产物 (防拿旧产物冒充本次结果)。
    artifacts: R433 显式落盘产物路径 (遥测 `script_artifact` 外部真值) ⇒ 优先取码, 防
    「渲染转录吃掉围栏/下划线 ⇒ 假 syntax_error」。
    code_source: 实际取码通道 (artifact | transcript) —— **通道必须可见**, 否则假红不可归因。
    """
    art = [c for c in _artifact_paths(artifacts) if c and c.strip()]
    code = extract_code(reply, since=since, artifacts=artifacts)
    cs = "artifact" if (code or "").strip() and (code or "").strip() in art else "transcript"
    if not code or not code.strip():
        return {"mode": "no_code", "passed": 0, "total": len(task["hidden"]),
                "detail": [], "taxonomy": {"no_code": 1}, "code_source": cs}
    if not _syntax_ok(code):
        return {"mode": "syntax_error", "passed": 0, "total": len(task["hidden"]),
                "detail": [], "taxonomy": {"syntax_error": 1}, "code_source": cs}

    tax, detail = {}, []
    nonzero_ok = 0
    n_bad_enc = 0
    for i, case in enumerate(task["hidden"]):
        r = run_code(code, case["stdin"], timeout)
        if r.get("bad_encoding"):
            n_bad_enc += 1
        out_ok = norm(r["stdout"]) == norm(case["expected_stdout"])
        if r["timed_out"]:
            v = "timeout"
        elif out_ok and (r["exit"] == 0 or norm(case["expected_stdout"]) != ""):
            # R417: 输出正确但退出码非 0 (惯性 sys.exit(1)) 不该判失败; 期望空输出时崩溃仍算失败
            v = "ok"
            if r["exit"] != 0:
                nonzero_ok += 1
        elif r["exit"] != 0:
            v = "runtime_error"
        else:
            v = "wrong_output"
        tax[v] = tax.get(v, 0) + 1
        detail.append({"case": i, "verdict": v, "exit": r["exit"],
                       "bad_encoding": 1 if r.get("bad_encoding") else 0,
                       "got": norm(r["stdout"])[:120], "want": norm(case["expected_stdout"])[:120]})
    passed = tax.get("ok", 0)
    total = len(task["hidden"])
    mode = "ok" if passed == total else ("timeout" if "timeout" in tax else
                                        "runtime_error" if "runtime_error" in tax else
                                        "partial" if passed else "wrong_output")
    return {"mode": mode, "passed": passed, "total": total, "detail": detail,
            "taxonomy": tax, "exit_nonzero_ok": nonzero_ok, "bad_encoding": n_bad_enc,
            "code_source": cs}


# ---------------------------------------------------------------- 见证型数学题: 独立验证
# 判据绑定语义: 不比对单一标签, 而是**验证解答者给出的见证**。
# 本实现的素数判定走 6k±1 轮, 与生成器 (tasks.py 的双实现) 不同路 ⇒ 构成跨实现对账。

_CLAIM_MIN = {"mersenne_prime": 2, "poly41_prime": 2}


def _grade_pred(name: str):
    if name == "mersenne_prime":
        def f(n: int) -> bool:
            v = (1 << n) - 1
            if v < 2:
                return False
            if v % 2 == 0:
                return v == 2
            if v % 3 == 0:
                return v == 3
            d = 5
            while d * d <= v:
                if v % d == 0 or v % (d + 2) == 0:
                    return False
                d += 6
            return True
        return f

    def g(n: int) -> bool:
        v = n * n - n + 41
        if v < 2:
            return False
        d = 2
        while d * d <= v:
            if v % d == 0:
                return False
            d += 1
        return True
    return g


def verify_witness(meta: dict, got: str):
    """独立验证见证 ⇒ (ok, reason)。"""
    m = (meta or {}).get("witness") or {}
    kind = m.get("kind")
    try:
        x = int(got)
    except (TypeError, ValueError):
        return False, "not_int"
    if kind == "sqrt_mod":
        p, a = int(m["p"]), int(m["a"])
        if not (0 <= x < p):
            return False, "out_of_range"
        return ((x * x) % p == a), "x^2 mod p != a"
    if kind == "min_counterexample":
        name = str(m["claim"])
        pred = _grade_pred(name)
        if pred(x):
            return False, "claim_true_at_n"
        for k in range(_CLAIM_MIN[name], x):
            if not pred(k):
                return False, "not_minimal:%d" % k
        return True, ""
    return False, "unknown_witness_kind"


def grade_math(task: dict, reply: str) -> dict:
    got = extract_final(reply)
    if not got:
        return {"mode": "no_final", "passed": 0, "total": 1, "detail": [], "taxonomy": {"no_final": 1}}
    if (task.get("meta") or {}).get("witness"):
        ok, why = verify_witness(task["meta"], got)
        mode = "ok" if ok else "wrong_witness"
        return {"mode": mode, "passed": 1 if ok else 0, "total": 1,
                "detail": [{"case": 0, "verdict": mode, "got": got,
                            "want": "<见证独立验证>", "why": why}],
                "taxonomy": {mode: 1}}
    want = task["answer"]
    if not got:
        return {"mode": "no_final", "passed": 0, "total": 1, "detail": [], "taxonomy": {"no_final": 1}}
    ok = got == want or (got.lstrip("+") == want)
    return {"mode": "ok" if ok else "wrong_final", "passed": 1 if ok else 0, "total": 1,
            "detail": [{"case": 0, "verdict": "ok" if ok else "wrong_final", "got": got, "want": want}],
            "taxonomy": {"ok" if ok else "wrong_final": 1}}


def grade(task: dict, reply: str, timeout: float = 5.0, artifacts=None) -> dict:
    return (grade_program(task, reply, timeout, artifacts=artifacts) if task["kind"] == "program"
            else grade_math(task, reply))


# ---------------------------------------------------------------- 负控

_GOOD_MAXSUB = """
import sys
d=sys.stdin.read().split()
n=int(d[0]); a=[int(x) for x in d[1:1+n]]
best=cur=a[0]
for x in a[1:]:
    cur=max(x,cur+x); best=max(best,cur)
print(best)
"""

_BAD_OFFBYONE = _GOOD_MAXSUB.replace("print(best)", "print(best-1)")   # 真差一: 输出必错
assert _BAD_OFFBYONE != _GOOD_MAXSUB
_BAD_LOOP = "while True:\n    pass\n"
_BAD_SYNTAX = "def f(:\n    pass\n"


def _mk_program_task():
    return {"kind": "program", "family": "max_subarray",
            "hidden": [{"stdin": "3\n1 -2 3\n", "expected_stdout": "3"},
                       {"stdin": "4\n-1 -2 -3 -4\n", "expected_stdout": "-1"}]}


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

    t = _mk_program_task()
    print("selftest: 判定器正控 / 负控")

    r = grade_program(t, "```python\n%s\n```" % _GOOD_MAXSUB)
    chk("正控: 正确解判满分", r["mode"] == "ok" and r["passed"] == 2, str(r["taxonomy"]))

    r = grade_program(t, "")
    chk("负控: 无代码块判 no_code", r["mode"] == "no_code")

    r = grade_program(t, "先分析一下…\n```python\n%s\n```\n完成" % _BAD_SYNTAX)
    chk("负控: 语法错判 syntax_error", r["mode"] == "syntax_error")

    r = grade_program(t, "```python\n%s\n```" % _BAD_LOOP, timeout=1.0)
    chk("负控: 死循环判 timeout", r["mode"] == "timeout")

    r = grade_program(t, "```python\n%s\n```" % _BAD_OFFBYONE)
    chk("负控: 差一错误判 wrong_output", r["mode"] == "wrong_output",
        "passed=%d/%d" % (r["passed"], r["total"]))

    # 只过公开用例的作弊解: 硬编码公开样例 ⇒ 隐藏用例必挂
    cheat = "print(3)" if t["hidden"][0]["expected_stdout"] == "3" else "print(0)"
    r = grade_program(t, "```python\n%s\n```" % cheat)
    chk("负控: 单值硬编码判部分/错", r["passed"] < 2, "passed=%d/2" % r["passed"])

    r = grade_program({"kind": "program", "hidden": t["hidden"]}, "```python\n%s\n```" % _GOOD_MAXSUB)
    chk("正控: 与公开用例无关(判定只用隐藏)", r["passed"] == 2)

    # ---- 提取/分类口径负控 (R417 真机抓到: 长回复下程序被误判成残片 + 正确输出被退出码顶掉)
    nl = chr(10)
    stub = "#!/usr/bin/env python3" + nl + "# -*- coding: utf-8 -*-" + nl + "def f(:" + nl
    good = "import sys" + nl + "print(len(sys.stdin.read().split()))" + nl
    pad = ("# " + "x" * 40 + nl) * 6
    fence = "```python" + nl
    reply = fence + stub + pad + "```" + nl + fence + good + "```" + nl
    got = extract_code(reply)
    chk("负控: 长残片候选不得顶掉整体可编译者", got.strip() == good.strip(), "len=%d" % len(got))

    t_exit = {"kind": "program", "hidden": [{"stdin": "x", "expected_stdout": "ERR"}]}
    r = grade_program(t_exit, fence + "import sys" + nl + "print('ERR')" + nl + "sys.exit(1)" + nl + "```")
    chk("正控: stdout 正确但退出码非 0 仍判过", r["mode"] == "ok" and r.get("exit_nonzero_ok") == 1,
        str(r["taxonomy"]))
    r = grade_program(t_exit, fence + "import sys" + nl + "raise SystemExit(1)" + nl + "```")
    chk("负控: 无输出 + 非 0 退出判 runtime_error", r["mode"] == "runtime_error", str(r["taxonomy"]))
    t_empty = {"kind": "program", "hidden": [{"stdin": "x", "expected_stdout": ""}]}
    r = grade_program(t_empty, fence + "import sys" + nl + "raise SystemExit(1)" + nl + "```")
    chk("负控: 期望空输出时崩溃不得判过", r["mode"] == "runtime_error", str(r["taxonomy"]))

    # ---- R419 坏字节负控: 判定器不得因被测程序输出坏字节而抛异常 (整臂崩 = 测量失败) ----
    t_bytes = {"kind": "program", "hidden": [{"stdin": "x", "expected_stdout": "ERR"}]}
    bad_src = (fence + "import sys" + nl
               + "sys.stdout.buffer.write(b'\\xe9')" + nl
               + "sys.stdout.flush()" + nl + "```" + nl)
    try:
        rb = grade_program(t_bytes, bad_src)
        chk("★负控: 坏字节输出判不过且被分类 (不得抛异常打崩整臂)",
            rb["mode"] == "wrong_output" and rb["bad_encoding"] == 1, str(rb["taxonomy"]))
    except Exception as e:  # noqa: BLE001 —— 这里有异常就是缺陷本身
        chk("★负控: 坏字节输出判不过且被分类 (不得抛异常打崩整臂)", False, "raised %r" % e)
    r = grade_program(t_bytes, fence + "print('ERR')" + nl + "```")
    chk("正控: 坏字节修正后正常程序仍判过 (改动不误伤)", r["mode"] == "ok" and r["bad_encoding"] == 0,
        str(r["taxonomy"]))

    # ---- 见证型判定负控 ----
    ws = {"kind": "math", "family": "witness_sqrt_mod", "answer": "", "meta": {"witness": {"kind": "sqrt_mod", "p": 101, "a": 4}}}
    chk("正控: sqrt_mod 正确见证通过", grade_math(ws, "FINAL: 2")["mode"] == "ok")
    chk("负控: sqrt_mod 错见证被拒", grade_math(ws, "FINAL: 3")["mode"] == "wrong_witness")
    chk("负控: sqrt_mod 越界被拒", grade_math(ws, "FINAL: 101")["mode"] == "wrong_witness")
    chk("负控: 见证非整数被拒", grade_math(ws, "FINAL: abc")["mode"] == "wrong_witness")

    wc = {"kind": "math", "family": "witness_min_counterexample", "answer": "",
          "meta": {"witness": {"kind": "min_counterexample", "claim": "mersenne_prime", "n": 4}}}
    chk("正控: 最小反例 4 通过", grade_math(wc, "FINAL: 4")["mode"] == "ok")
    chk("负控: 非最小反例被拒(5)", grade_math(wc, "FINAL: 5")["mode"] == "wrong_witness")
    chk("负控: 命题为真的 n 被拒(3)", grade_math(wc, "FINAL: 3")["mode"] == "wrong_witness")
    chk("负控: 缺 FINAL 判 no_final", grade_math(wc, "最小反例是 4")["mode"] == "no_final")

    _save_pred = _grade_pred
    globals()["_grade_pred"] = lambda name: (lambda n: True)   # 打坏判据
    try:
        bad = grade_math(wc, "FINAL: 4")["mode"]
    finally:
        globals()["_grade_pred"] = _save_pred                  # 还原
    chk("反向负控: 谓词恒真时 4 必须被判命题为真", bad == "wrong_witness", "mode=%s" % bad)
    chk("还原后判据仍严", grade_math(wc, "FINAL: 5")["mode"] == "wrong_witness")

    tm = {"kind": "math", "family": "comb_mod", "answer": "5"}
    chk("正控: math FINAL 解析", grade_math(tm, "推导…\nFINAL: 5")["mode"] == "ok")
    chk("负控: math 无 FINAL 判 no_final", grade_math(tm, "答案是 5")["mode"] == "no_final")
    chk("负控: math 错答判 wrong_final", grade_math(tm, "FINAL: 6")["mode"] == "wrong_final")

    # ---- 真机形态负控 (R398 首轮真跑抓到的两个判定器缺陷, 固化为永久负控)
    cli_like = "── 执行中 (turn 1) ──\n  [05] PY 落盘\n── 回复 ──\n%s\n  [06] 收尾状态行" % _GOOD_MAXSUB
    r = grade_program(t, cli_like)
    chk("负控: 无围栏 CLI 回复+尾部状态行 ⇒ 仍能抽到可编译前缀",
        r["mode"] == "ok" and r["passed"] == 2, str(r["taxonomy"]))

    import tempfile as _tf
    global ROOT
    real_root = ROOT
    td = _tf.mkdtemp(prefix="probe_art_")
    art = os.path.join(td, "data/artifacts")
    os.makedirs(art, exist_ok=True)
    name = "py_deadbeef00.py"
    with open(os.path.join(art, name), "w", encoding="utf-8") as fh:
        fh.write(_GOOD_MAXSUB)
    try:
        ROOT = td
        r = grade_program(t, "已写入 ./data/artifacts/%s (2026B) ✓ py_compile" % name)
        chk("正控: 回复只给产物路径 ⇒ 读产物判分", r["passed"] == 2, str(r["taxonomy"]))
        r = grade_program(t, "", since=10 ** 12)
        chk("负控: 空回复判 no_code", r["mode"] == "no_code")
    finally:
        ROOT = real_root

    # ---- R433 真机假红 (冻结题集同 sha 复跑): 渲染转录吃掉围栏/下划线, 而产品已落盘 artifact
    p_art = os.path.join(art, name)
    mangled = ("── 回复 ──\n  ｜ code_generation intent=cg\n  if name == \"main\":\n"
               "      main()\n(20363ms, intent=code_generation)\n")
    r = grade_program(t, mangled, artifacts=[p_art])
    chk("正控 R433: 转录不可编译 + 落盘产物 ⇒ 取产物判满分",
        r["mode"] == "ok" and r["passed"] == 2 and r["code_source"] == "artifact",
        "%s src=%s" % (r["taxonomy"], r["code_source"]))
    r = grade_program(t, mangled)
    chk("负控 R433: 同转录但缺产物通道 ⇒ 必须仍失败 (证明通道真起作用)",
        r["mode"] != "ok" and r["code_source"] == "transcript",
        "mode=%s src=%s" % (r["mode"], r["code_source"]))
    r = grade_program(t, "```python\n%s\n```" % _GOOD_MAXSUB, artifacts=["/nonexistent/py_x.py"])
    chk("负控 R433: 产物路径不存在 ⇒ 静默回退转录, 不许崩",
        r["mode"] == "ok" and r["passed"] == 2, "src=%s" % r["code_source"])

    # ---- 判定器自身反向负控: 把比对函数换成恒真, 正向负控必须转红
    global norm
    real_norm = norm
    norm = lambda text: ""  # noqa: E731  恒等: 任何输出都算相等 ⇒ 差一错误解将"变成"正确
    try:
        r = grade_program(t, "```python\n%s\n```" % _BAD_OFFBYONE)
        chk("反向负控: 比对恒真时差一解被误判为通过 (证明判据非空心)",
            r["mode"] == "ok", "mode=%s" % r["mode"])
    finally:
        norm = real_norm

    r = grade_program(t, "```python\n%s\n```" % _BAD_OFFBYONE)
    chk("反向负控: 比对恢复后差一解再次被抓", r["mode"] == "wrong_output")

    print("selftest %d/%d" % (ok, ok + len(fails)))
    return 0 if not fails else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
