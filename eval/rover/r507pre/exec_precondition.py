#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比数据**可验收前置**：两侧产出物必须 ① 可实际执行 ② 正确（用户 2026-09-17 令）。

规则（本轮落为宪法级前置）: 与 codex 的对照读数，只有**两侧产出物都真的能跑、且跑出来是对的**，
才构成「可验收对比数据」；否则该轮读数一律记 NOT_VERIFIABLE，不得当作验收依据。

与 `judge_contrast_r5xx.py` 的分工: 判据器吃**已落盘摘要**（判分器内部跑过一遍）；本器具走
**独立执行路径** —— 把产出物**物化到磁盘**（artifact 文件原样复制 / transcript 代码落盘），
再用 `python3 -I -B <file>` + 逐条 hidden 用例 stdin 实跑，比对规范化 stdout。

用法:
  python3 eval/rover/r507pre/exec_precondition.py \
      --taskset eval/rover/r504/taskset-r504.json \
      --codex data/probe/probe-cmd:....json --agent data/probe/probe-agent-...json \
      --out eval/rover/r507pre/precondition-r504.json
退出码: 0 = 可验收（两侧全跑通且全对）; 1 = 不可验收（点名）; 3 = 输入缺失 fail-closed

**验收面（R509 新增）**: 预注册 —— 题集同目录 `prereg-<名>.json` 内 `evidence_scope`
  `{"require":["<win>/<arm>",...], "nonrequired":[{"pattern":..., "reason":...}]}`。**先写再跑**才生效;
  臂未声明 ⇒ `UNDECLARED` fail-closed（不变相放水）; 事后 `--scope` 只出信息性读数, rc 恒 1。

**两种布局（R509 扩面）**:
  · `stdin/stdout` 布局（R502–R504 类）: 单文件程序, `python3 -I -B <file>` + stdin 逐条 hidden 用例。
  · `project` 布局（R508 类）: 多文件/起服务/多步, 任务自带**隐藏用例脚本**（`task["cases"]`,
    输出 `CASE <name> PASS|FAIL`）。本器**独立物化**仓内不可变快照
    （`eval/rover/<r>/snapshots/<window>/<arm>/<tid>/**`）到全新临时目录后 `python3 -I -B` 实跑用例脚本,
    逐条机械判对; **不吃** `report.json` 的自报 `all_pass`, 只把它记下来做**自报一致性**对照
    （不一致 ⇒ 点名 `self_report_mismatch`）。用例条数须等于 `task["hidden_cases"]`, 不等 ⇒ fail-closed。
    自动发现: `<r>/evidence/windows/*/report.json` + `<r>/snapshots/` 同时在位即走本布局。
"""
import argparse
import fnmatch
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
CASE_RE = re.compile(r"^CASE (\S+) (PASS|FAIL)(?: (.*))?$")
MIN_ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8"}
sys.path.insert(0, os.path.join(REPO, "eval/probe"))
import grade  # noqa: E402

PY = sys.executable


def rel(p):
    """落盘一律用仓内相对路径（可移植，禁绝对路径入证据件）。"""
    try:
        r = os.path.relpath(p, REPO)
        return r if not r.startswith("..") else p
    except Exception:
        return p


def load(p):
    return json.load(io.open(p, encoding="utf-8-sig"))


def reply_text(paths):
    for p in paths or []:
        ap = p if os.path.isabs(p) else os.path.join(REPO, p)
        if os.path.isfile(ap):
            return io.open(ap, encoding="utf-8", errors="replace").read()
    return ""


def materialize(code, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(code)
    return path


def run_file(path, stdin_text, timeout=10.0):
    try:
        p = subprocess.run([PY, "-I", "-B", path], input=(stdin_text or "").encode("utf-8"),
                           capture_output=True, timeout=timeout, cwd=os.path.dirname(path))
        return {"rc": p.returncode, "stdout": p.stdout.decode("utf-8", "replace"),
                "stderr_tail": p.stderr.decode("utf-8", "replace")[-200:]}
    except subprocess.TimeoutExpired:
        return {"rc": 124, "stdout": "", "stderr_tail": "TIMEOUT"}
    except Exception as e:  # pragma: no cover
        return {"rc": 125, "stdout": "", "stderr_tail": str(e)[:200]}


def check_side(side, summary, tasks, work, timeout=10.0):
    rows = []
    for t in summary.get("per_task") or []:
        tid = t.get("tid")
        task = tasks.get(tid)
        if task is None:
            rows.append({"tid": tid, "status": "task_not_in_taskset"})
            continue
        kind = task.get("kind")
        art = [a for a in (t.get("artifacts") or []) if a]
        rep = reply_text(t.get("reply_paths"))
        code = grade.extract_code(rep, None, art)
        rec = {"tid": tid, "kind": kind, "family": task.get("family"),
               "graded_mode": t.get("mode"), "code_source": t.get("code_source"),
               "artifact_on_disk": bool(art and os.path.isfile(art[0])),
               "code_chars": len(code or "")}
        if kind != "program":
            # 无「可执行」面: 只记判定器的正确性结论（不冒充执行读数）
            rec.update({"exec": "not-applicable", "correct": t.get("mode") == "ok",
                        "note": "非程序题(kind=%s): 无执行面, 只核正确性" % kind})
            rows.append(rec)
            continue
        if not code or not code.strip():
            rec.update({"exec": "no_code", "correct": False})
            rows.append(rec)
            continue
        fp = materialize(code, os.path.join(work, "%s-%s.py" % (side, tid)))
        pub = (task.get("public") or [{}])[0]
        e = run_file(fp, pub.get("stdin"), timeout)
        rec["exec_rc_public"] = e["rc"]
        rec["exec"] = "ok" if e["rc"] == 0 else "rc=%s" % e["rc"]
        cases = []
        for i, c in enumerate(task.get("hidden") or []):
            r = run_file(fp, c.get("stdin"), timeout)
            ok = (r["rc"] == 0) and (grade.norm(r["stdout"]) == grade.norm(c.get("expected_stdout")))
            cases.append(ok)
        rec.update({"cases_n": len(cases), "cases_pass": sum(1 for x in cases if x),
                    "correct": bool(cases) and all(cases), "path": fp})
        rows.append(rec)
    return rows


def _discover(round_id):
    """按轮号自动发现题集与两侧落盘摘要（机检，不猜）。"""
    import glob as _g
    rid = round_id.lower()
    rid = rid if rid.startswith("r") else "r" + rid
    ts = sorted(_g.glob(os.path.join(REPO, "eval/rover", rid, "taskset-%s.json" % rid)))
    if not ts:
        return None, None, None
    cand = [p for p in sorted(_g.glob(os.path.join(REPO, "data/probe", "probe-*%s.json" % rid)), key=os.path.getmtime)
            if "-seed0-" in os.path.basename(p) and "vmrun" not in os.path.basename(p)]
    cx = [p for p in cand if "codex" in os.path.basename(p)]
    ag = [p for p in cand if "agent" in os.path.basename(p) and "codex" not in os.path.basename(p)]
    return ts[-1], (cx[-1] if cx else None), (ag[-1] if ag else None)


# --- project 布局（R508 类: 多文件/起服务/多步，任务自带隐藏用例脚本） -------

def _discover_project(round_id):
    """project 布局自动发现: 题集 + windows(含 artifacts.json 的窗口) + 仓内快照根。不适用 ⇒ None。"""
    rid = round_id.lower()
    rid = rid if rid.startswith("r") else "r" + rid
    ts = sorted(glob.glob(os.path.join(REPO, "eval/rover", rid, "taskset-%s.json" % rid)))
    win_root = os.path.join(REPO, "eval/rover", rid, "evidence/windows")
    snap_root = os.path.join(REPO, "eval/rover", rid, "snapshots")
    if not ts or not os.path.isdir(win_root) or not os.path.isdir(snap_root):
        return None
    wins = sorted(d for d in os.listdir(win_root)
                  if os.path.isfile(os.path.join(win_root, d, "artifacts.json")))
    if not wins:
        return None
    return ts[-1], win_root, snap_root, wins


def _claimed_rows(win_dir):
    """自报读数（仅作对照，**不吃**）: report.json rows ∪ `grade-<tag>-<tid>.json`。
    返回 {(arm_tag, tid): {"all_pass":bool, "side":str|None, "src":path}}。"""
    out = {}
    rp = os.path.join(win_dir, "report.json")
    if os.path.isfile(rp):
        rep = load(rp)
        for row in (rep.get("rows") or []):
            if row.get("arm") and row.get("tid"):
                out[(row["arm"], row["tid"])] = {"all_pass": bool(row.get("all_pass")),
                                                 "side": row.get("side"), "src": rel(rp)}
    for gp in sorted(glob.glob(os.path.join(win_dir, "grade-*.json"))):
        m = re.match(r"^grade-(.+)-([a-z0-9]+)\.json$", os.path.basename(gp))
        if not m:
            continue
        key = (m.group(1), m.group(2))
        d = load(gp)
        out.setdefault(key, {"all_pass": bool(d.get("all_pass")), "side": None, "src": rel(gp)})
    return out


def _dir_to_tag(d, codex_tags):
    """快照目录名 → 自报臂标签: `agentB`→`B` / `codex`→唯一 codex 标签。无对应 ⇒ None。"""
    if d.startswith("agent"):
        return d[len("agent"):]
    if d == "codex":
        return codex_tags[0] if len(codex_tags) == 1 else None
    return None


def _copy_tree(src, dst):
    for root, dirs, files in os.walk(src):
        rel_ = os.path.relpath(root, src)
        tgt = dst if rel_ == "." else os.path.join(dst, rel_)
        os.makedirs(tgt, exist_ok=True)
        for f in files:
            shutil.copy2(os.path.join(root, f), os.path.join(tgt, f))


def run_case_script(script, workdir, timeout=420):
    """`python3 -I -B <用例脚本>`，cwd=独立物化目录；只解析 `CASE <name> PASS|FAIL`。"""
    env = dict(MIN_ENV)
    env["HOME"] = workdir
    try:
        p = subprocess.run([PY, "-I", "-B", script], cwd=workdir, capture_output=True, text=True,
                           timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return {"rc": 124, "cases": [], "stderr_tail": "TIMEOUT"}
    except Exception as e:  # pragma: no cover
        return {"rc": 125, "cases": [], "stderr_tail": str(e)[:200]}
    cases = []
    for ln in p.stdout.splitlines():
        m = CASE_RE.match(ln.strip())
        if m:
            cases.append({"name": m.group(1), "status": m.group(2), "detail": (m.group(3) or "")[:200]})
    return {"rc": p.returncode, "cases": cases, "stderr_tail": p.stderr[-200:]}


def _scope_of(skey, scope):
    """臂级验收归属: require（本窗即验收面）/ nonrequired（已声明非验收面, 须给理由）/ undeclared（fail-closed）。"""
    if scope is None:
        return "require"
    for p in (scope.get("require") or []):
        if fnmatch.fnmatch(skey, p):
            return "require"
    for ent in (scope.get("nonrequired") or []):
        if fnmatch.fnmatch(skey, ent.get("pattern") or ""):
            return "nonrequired"
    return "undeclared"


def _early_scope(win, arm, key, what, scope, out):
    """早退分支 (task_not_in_taskset / missing_case_script) 的验收面归属。

    R523 修: 原先这些分支只进全局 `blocked` ⇒ 已声明**非验收面**的臂缺脚本也能把 rc 顶成 1
    (R522「blocked 非空即 rc=1」补丁把这条修过头)。修后: 与正常路径同规则 ——
    require ⇒ 进 blocked_scoped; undeclared ⇒ 进 blocked_scoped(UNDECLARED_SCORE 语义);
    nonrequired ⇒ 只进全局 blocked 并单列读数。全局 blocked 始终非空 (如实记账, 不放水)。
    """
    skey = "%s/%s" % (win, arm)
    sc = _scope_of(skey, scope)
    msg = "%s/%s %s" % (win, key, what)
    out["blocked"].append(msg)
    if sc == "undeclared":
        out["undeclared_arms"].append(skey)
    if sc != "nonrequired":
        out["blocked_scoped"].append(msg)
        return {"scope": sc, "blocking": True}
    out["nonrequired_arms"].append({"arm": skey, "correct": False, "detail": msg})
    return {"scope": sc, "blocking": False}


def _prereg_of(src):
    """载入 prereg 全文（策略与 evidence_scope 同源; 缺 ⇒ {}）。"""
    try:
        return load(src) or {}
    except Exception:
        return {}


def _policy_plan(prereg, prereg_src, opens):
    """R529 J4: `unreliable_policy` 机检 (全部条目不满足 ⇒ 拒绝生效, fail-closed)。

    `opens` = [(win, artifacts_path), ...]. 三条硬门:
      A1 rule 匹配 ∧ declared_before_run is True;
      A2 `policy_declared_ts` 可解析 ∧ prereg 文件自身 mtime >= 该 ts（时间戳不得是事后/虚构的）;
      A3 该轮**每个窗**的 artifacts.json mtime >= policy_declared_ts（先声明再跑; 违反 ⇒ 整体拒绝）。
    返回 {"active": bool, "reason": str, "excluded_windows": [...], "checks": {...}}。
    """
    info = {"active": False, "reason": "", "checks": {}, "declared_ts": None}
    pol = prereg.get("unreliable_policy")
    if not isinstance(pol, dict):
        info["reason"] = "no_policy_key"
        return info
    if pol.get("rule") != "truth_arm_window_unavailable" or pol.get("declared_before_run") is not True:
        info["reason"] = "rule_or_flag_mismatch"
        return info
    raw = pol.get("policy_declared_ts")
    try:
        from datetime import datetime, timezone
        ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        epoch = ts.timestamp()
    except Exception:
        info["reason"] = "policy_ts_unparsable:%s" % raw
        return info
    info["declared_ts"] = raw
    try:
        p_epoch = os.path.getmtime(prereg_src)
    except OSError:
        info["reason"] = "prereg_unstattable"
        return info
    info["checks"]["A2_prereg_mtime_not_before_ts"] = bool(p_epoch >= epoch - 1.0)
    if not info["checks"]["A2_prereg_mtime_not_before_ts"]:
        info["reason"] = "prereg_mtime_predates_declared_ts"
        return info
    late = []
    for win, apath in opens:
        try:
            if os.path.getmtime(apath) < epoch - 1.0:
                late.append(win)
        except OSError:
            late.append(win + "(stat_fail)")
    info["checks"]["A3_all_windows_after_ts"] = (not late)
    info["checks"]["A3_late_windows"] = late
    if late:
        info["reason"] = "windows_predate_policy:" + ",".join(late)
        return info
    info["active"] = True
    info["truth_arm_patterns"] = list(pol.get("truth_arm_patterns") or [])
    info["effect"] = pol.get("effect")
    info["bars"] = pol.get("bars")
    return info


def _resolve_scope(scope_arg, ts_path, rounds_dir=None):
    """验收面来源: 显式 `--scope`（事后）> 题集同目录 `prereg-<名>.json` 内的 `evidence_scope`（预注册）。
    返回 (scope_dict|None, source_path|None, is_prereg:bool)。**缺 = 全臂皆验收面**（不放水）。"""
    if scope_arg and os.path.isfile(scope_arg):
        return (load(scope_arg) or {}).get("evidence_scope"), scope_arg, False
    base = os.path.basename(ts_path).replace("taskset-", "prereg-")
    cand = os.path.join(os.path.dirname(os.path.abspath(ts_path)), base)
    if os.path.isfile(cand):
        sc = (load(cand) or {}).get("evidence_scope")
        if sc:
            return sc, cand, True
    return None, None, False


def run_project(label, taskset_path, win_root, snap_root, wins, out_path, timeout=420, keep=False,
                scope=None, scope_src=None, scope_prereg=False):
    rdir = os.path.dirname(os.path.abspath(taskset_path))
    ts = load(taskset_path)
    tasks = {}
    for t in ((ts.get("tasks") or []) if isinstance(ts, dict) else ts):
        tasks[t["tid"]] = t
    out = {"label": label, "layout": "project", "taskset": rel(taskset_path),
           "snapshot_root": rel(snap_root), "tasks_n": len(tasks), "windows_n": len(wins),
           "rule": "可验收前置(project 布局): 仓内不可变快照 ⇒ 独立物化到全新临时目录 ⇒ python3 -I -B 实跑隐藏用例脚本 ⇒ 逐条机械判对; 自报 all_pass 只作对照不吃",
           "declared_absent": [],
           "scope_source": (rel(scope_src) if scope_src else None),
           "scope_prereg": bool(scope_prereg),
           "scope_require": (scope or {}).get("require"),
           "scope_nonrequired": (scope or {}).get("nonrequired"),
           "windows": {}, "self_report_mismatch": [], "claim_unmapped": [],
           "blocked": [], "blocked_scoped": [], "nonrequired_arms": [], "undeclared_arms": []}
    for win in wins:
        wdir = os.path.join(win_root, win)
        claimed = _claimed_rows(wdir)
        codex_tags = sorted({t for (t, _), v in claimed.items() if v.get("side") == "codex"})
        wrec = {"dir": rel(wdir), "arms": {}}
        snapwin = os.path.join(snap_root, win)
        if not os.path.isdir(snapwin):
            msg = "%s 快照目录缺失 %s" % (win, rel(snapwin))
            out["blocked"].append(msg)
            out["blocked_scoped"].append(msg)   # 整窗不可核验 ⇒ 必进验收面 (fail-closed)
            out["windows"][win] = wrec
            continue
        for arm in sorted(os.listdir(snapwin)):
            for tid in sorted(os.listdir(os.path.join(snapwin, arm))):
                src = os.path.join(snapwin, arm, tid)
                if not os.path.isdir(src):
                    continue
                key = "%s/%s" % (arm, tid)
                tag = _dir_to_tag(arm, codex_tags)
                task = tasks.get(tid)
                rec = {"arm": arm, "tag": tag, "tid": tid,
                       "side": ((claimed.get((tag, tid)) or {}).get("side")
                                or ("codex" if arm == "codex" else "agent")),
                       "kind": (task or {}).get("kind") or "project",
                       "family": (task or {}).get("family")}
                if task is None:
                    rec.update({"status": "task_not_in_taskset", "correct": False})
                    rec.update(_early_scope(win, arm, key, "task_not_in_taskset", scope, out))
                    wrec["arms"][key] = rec
                    continue
                script = os.path.join(rdir, task.get("cases") or "")
                if not os.path.isfile(script):
                    rec.update({"status": "missing_case_script", "correct": False})
                    rec.update(_early_scope(win, arm, key, "missing_case_script %s" % (task.get("cases")),
                                            scope, out))
                    wrec["arms"][key] = rec
                    continue
                tmp = tempfile.mkdtemp(prefix="precond-%s-%s-" % (win, arm.replace("/", "_")))
                _copy_tree(src, tmp)
                r = run_case_script(script, tmp, timeout)
                exp_n = int(task.get("hidden_cases") or 0)
                npass = sum(1 for c in r["cases"] if c["status"] == "PASS")
                count_ok = (exp_n == 0) or (len(r["cases"]) == exp_n)
                correct = bool(r["rc"] == 0 and r["cases"] and npass == len(r["cases"]) and count_ok)
                crow = claimed.get((tag, tid)) if tag else None
                rec.update({"cases_n": len(r["cases"]), "cases_expected": exp_n, "cases_pass": npass,
                            "rc": r["rc"], "correct": correct, "work_dir": tmp if keep else None,
                            "failed_cases": [c["name"] for c in r["cases"] if c["status"] != "PASS"],
                            "claimed_all_pass": (None if crow is None else bool(crow.get("all_pass"))),
                            "claimed_src": (None if crow is None else crow.get("src")),
                            "stderr_tail": r["stderr_tail"]})
                if crow is None:
                    out["claim_unmapped"].append("%s/%s tag=%s 无自报行(对照不可用, 不影响实测判定)" % (win, key, tag))
                elif bool(crow.get("all_pass")) != correct:
                    out["self_report_mismatch"].append("%s/%s 自报 all_pass=%s 实测 correct=%s" % (win, key, crow.get("all_pass"), correct))
                skey = "%s/%s" % (win, arm)
                rec["scope"] = _scope_of(skey, scope)
                msg = "%s/%s rc=%s cases=%s/%s(expect %s) failed=%s" % (
                    win, key, r["rc"], npass, len(r["cases"]), exp_n, ",".join(rec["failed_cases"]) or "-")
                if rec["scope"] == "nonrequired":
                    out["nonrequired_arms"].append({"arm": skey, "correct": correct, "detail": msg})
                    rec["blocking"] = False
                elif rec["scope"] == "undeclared":
                    out["undeclared_arms"].append(skey)
                    out["blocked_scoped"].append("UNDECLARED_SCOPE " + skey)
                    rec["blocking"] = True
                else:
                    rec["blocking"] = True
                if not correct:
                    out["blocked"].append(msg)
                    if rec["blocking"]:
                        out["blocked_scoped"].append(msg)
                wrec["arms"][key] = rec
        out["windows"][win] = wrec
    # ---- R529 J4(a): 声明臂缺席 ⇒ fail-closed (缺臂不得被静默跳过而成假绿) ----
    if scope is not None:
        for win in wins:
            for skey in [s for s in (scope.get("require") or []) if s.startswith(win + "/")]:
                adir = os.path.join(snap_root, win, skey.split("/", 1)[1])
                if not os.path.isdir(adir):
                    out["declared_absent"].append(skey)
                    out["blocked"].append("DECLARED_ARM_ABSENT %s (声明为验收面成员但快照缺失)" % skey)
                    out["blocked_scoped"].append("DECLARED_ARM_ABSENT %s (声明为验收面成员但快照缺失)" % skey)
    # ---- R529 J4(b): 外部真值失败窗 unreliable 判据化 (只能靠预注册驱动; 无 key ⇒ 本段完全不生效 ⇒ 历史轮 rc 不变) ----
    _prereg_obj = _prereg_of(scope_src) if (scope_prereg and scope_src) else {}
    pol = _policy_plan(_prereg_obj, scope_src, [(w, os.path.join(win_root, w, "artifacts.json")) for w in wins])
    out["policy"] = pol
    if pol.get("active"):
        pats = [p for p in (pol.get("truth_arm_patterns") or []) if p]
        demoted, unreli = [], []
        for win in wins:
            wrec2 = out["windows"].get(win) or {"arms": {}}
            declared = [s.split("/", 1)[1] for s in (scope or {}).get("require") or []
                        if s.startswith(win + "/") and any(fnmatch.fnmatch(s, p) for p in pats)]
            # 臂键形如 "codex/t1"; 预注册模式是**臂级** "*/codex" ⇒ 必须用臂名 (去 tid) 去匹配
            seen = sorted({k.split("/")[0] for k in wrec2["arms"]
                           if any(fnmatch.fnmatch("%s/%s" % (win, k.split("/")[0]), p) for p in pats)})
            cand = sorted(set(declared) | set(seen))
            bad = []
            for a in cand:
                rows = {k: v for k, v in wrec2["arms"].items() if k.split("/")[0] == a}
                ok = bool(rows) and all(v.get("correct") for v in rows.values())
                if not ok:
                    bad.append(a)
            if not bad:
                continue
            unreli.append({"window": win, "truth_arms_unavailable": bad,
                           "note": "外侧(外部真值)臂未全对/缺席 ⇒ 该窗对照列标 unreliable; 本侧臂失败不受本规则影响"})
            for a in bad:
                demoted.append((win, a))
                for k, v in wrec2["arms"].items():
                    if k.split("/")[0] == a:
                        v["blocking"] = False
                        v["policy"] = "unreliable_excluded"
        if demoted:
            ptid = tuple("%s/%s/" % (w, a) for w, a in demoted)
            parm = tuple("DECLARED_ARM_ABSENT %s/%s" % (w, a) for w, a in demoted)
            pund = tuple("UNDECLARED_SCOPE %s/%s" % (w, a) for w, a in demoted)
            before_n = len(out["blocked_scoped"])
            out["blocked_scoped"] = [m for m in out["blocked_scoped"]
                                     if not (m.startswith(ptid) or m.startswith(parm) or m.startswith(pund))]
            out["policy_demoted"] = sorted("%s/%s" % (w, a) for w, a in demoted)
            out["policy_removed_msgs"] = before_n - len(out["blocked_scoped"])
            for s in [x for x in list(out["declared_absent"]) if any(x.startswith("%s/%s" % (w, a)) for w, a in demoted)]:
                out["declared_absent"].remove(s)
        out["unreliable_windows"] = unreli
    out["self_report_agrees"] = not out["self_report_mismatch"]
    out["executable_and_correct"] = (not out["blocked"]) and out["self_report_agrees"]
    out["acceptable_scoped"] = ((not out["blocked_scoped"]) and out["self_report_agrees"]
                                and (scope is not None))
    if scope is None:
        out["acceptable_scoped"] = out["executable_and_correct"]
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    io.open(out_path, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    for win, wrec in out["windows"].items():
        tot = len(wrec["arms"])
        good = sum(1 for v in wrec["arms"].values() if v.get("correct"))
        print("%-7s arms=%d correct=%d" % (win, tot, good))
        for key, v in sorted(wrec["arms"].items()):
            print("   %-16s side=%-6s cases=%-6s rc=%-4s correct=%-5s claimed=%-5s %s" %
                  (key, v.get("side"), "%s/%s" % (v.get("cases_pass"), v.get("cases_n")), v.get("rc"),
                   v.get("correct"), v.get("claimed_all_pass"), ",".join(v.get("failed_cases") or [])))
    print("DECLARED_ABSENT=%s" % (",".join(out["declared_absent"]) or "-"))
    print("POLICY_ACTIVE=%s reason=%s ts=%s checks=%s" % ((out.get("policy") or {}).get("active"),
          (out.get("policy") or {}).get("reason"), (out.get("policy") or {}).get("declared_ts"),
          json.dumps((out.get("policy") or {}).get("checks"), ensure_ascii=False)))
    if out.get("unreliable_windows"):
        print("UNRELIABLE_WINDOWS=" + json.dumps(out["unreliable_windows"], ensure_ascii=False))
    if out.get("policy_demoted"):
        print("POLICY_DEMOTED=%s (从验收面移出 %d 条; 非本侧臂)" % (",".join(out["policy_demoted"]), out.get("policy_removed_msgs")))
    print("SELF_REPORT_AGREES=%s" % out["self_report_agrees"])
    print("EXECUTABLE_AND_CORRECT=%s (全局, 任一臂-题不许错)" % out["executable_and_correct"])
    print("SCOPE_SOURCE=%s PREREG=%s" % (out["scope_source"], out["scope_prereg"]))
    if out["scope_source"] and not out["scope_prereg"]:
        print("SCOPE_POSTHOC=1 (事后声明, 非预注册 ⇒ 只可作参考, 不得当验收依据)")
    print("ACCEPTABLE_SCOPED=%s" % out["acceptable_scoped"])
    for v in out["nonrequired_arms"]:
        print("NONREQUIRED %s correct=%s :: %s" % (v["arm"], v["correct"], v["detail"]))
    if out["undeclared_arms"]:
        print("UNDECLARED: " + " | ".join(out["undeclared_arms"]))
    if out["blocked"]:
        print("BLOCKED: " + " | ".join(out["blocked"]))
    print("OUT=" + out_path)
    if out["scope_source"] and not out["scope_prereg"]:
        print("VERDICT_POSTHOC_ONLY ⇒ rc=1 (事后声明不构成验收面)")
        return 1
    if out["blocked_scoped"]:
        print("VERDICT_BLOCKED ⇒ rc=1 (验收面 [require ∪ 未声明] 存在未执行/不正确臂 ⇒ 不得 rc=0 假绿)")
        if out["blocked"] and len(out["blocked"]) != len(out["blocked_scoped"]):
            print("  (全局 blocked %d 项 > 验收面 blocked_scoped %d 项: 差额为非验收面读数, 已单列 NONREQUIRED)"
                  % (len(out["blocked"]), len(out["blocked_scoped"])))
        return 1
    if out["blocked"]:
        print("VERDICT_OK_SCOPED ⇒ rc 由验收面判定; 非验收面存在失败读数 (见 NONREQUIRED, 如实记账不阻断)")
    return 0 if out["acceptable_scoped"] else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--taskset")
    ap.add_argument("--codex")
    ap.add_argument("--agent")
    ap.add_argument("--out")
    ap.add_argument("--label", default="")
    ap.add_argument("--round", help="按轮号自动发现（eval/rover/<r>/taskset-<r>.json + data/probe/probe-*-<r>.json）")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--proj-timeout", type=float, default=420.0, help="project 布局: 单题全部用例的总超时(s)")
    ap.add_argument("--layout", choices=["auto", "stdin", "project"], default="auto")
    ap.add_argument("--scope", help="臂级验收面声明(JSON, 键 evidence_scope); 缺省读题集同目录 prereg-<名>.json")
    a = ap.parse_args()
    if a.layout == "project" and a.taskset:
        # 显式 project 面板（供 NC/沙盒: 目录自定, 不依赖 --round 命名约定）
        rdir = os.path.dirname(os.path.abspath(a.taskset))
        win_root = os.path.join(rdir, "evidence/windows")
        snap_root = os.path.join(rdir, "snapshots")
        wins = sorted(d for d in os.listdir(win_root)
                      if os.path.isfile(os.path.join(win_root, d, "artifacts.json"))) \
            if os.path.isdir(win_root) else []
        if not wins:
            print("[致命] PROJECT_NO_WINDOWS taskset=%s ⇒ rc=3" % a.taskset)
            return 3
        scope, ssrc, spre = _resolve_scope(a.scope, a.taskset)
        return run_project(a.label or "EXPLICIT", a.taskset, win_root, snap_root, wins,
                           a.out or "/tmp/precond-explicit.json", a.proj_timeout,
                           scope=scope, scope_src=ssrc, scope_prereg=spre)
    if a.round and a.layout in ("auto", "project"):
        proj = _discover_project(a.round)
        if proj:
            ts, win_root, snap_root, wins = proj
            a.label = a.label or a.round.upper()
            a.out = a.out or os.path.join(REPO, "eval/rover/r507pre", "precondition-%s.json" % a.round.lower())
            print("DISCOVER layout=project taskset=%s windows=%d snapshot_root=%s" %
                  (os.path.relpath(ts, REPO), len(wins), os.path.relpath(snap_root, REPO)))
            scope, ssrc, spre = _resolve_scope(a.scope, ts)
            return run_project(a.label, ts, win_root, snap_root, wins, a.out, a.proj_timeout,
                               scope=scope, scope_src=ssrc, scope_prereg=spre)
        if a.layout == "project":
            print("[致命] PROJECT_NOT_APPLICABLE round=%s ⇒ rc=3" % a.round)
            return 3
    if a.round:
        ts, cx, ag = _discover(a.round)
        if not ts or not cx or not ag:
            print("[致命] DISCOVER_FAIL round=%s taskset=%s codex=%s agent=%s ⇒ rc=3" % (a.round, ts, cx, ag))
            return 3
        a.taskset, a.codex, a.agent = ts, cx, ag
        a.label = a.label or a.round.upper()
        a.out = a.out or os.path.join(REPO, "eval/rover/r507pre", "precondition-%s.json" % a.round)
        for k, v in (("taskset", ts), ("codex", cx), ("agent", ag)):
            print("DISCOVER %-7s %s" % (k, os.path.relpath(v, REPO)))
    for k in ("taskset", "codex", "agent", "out"):
        if not getattr(a, k):
            print("[致命] MISSING_ARG --%s ⇒ rc=3" % k)
            return 3
    for p in (a.taskset, a.codex, a.agent):
        if not os.path.isfile(p):
            print("[致命] 输入缺失: %s ⇒ fail-closed rc=3" % p)
            return 3
    ts = load(a.taskset)
    tasks = {t["tid"]: t for t in ts}
    work = "/tmp/r507pre"
    os.makedirs(work, exist_ok=True)
    out = {"label": a.label, "taskset": rel(a.taskset), "tasks_n": len(tasks),
           "rule": "对比数据可验收前置: 两侧产出物须可实际执行且正确 (用户 2026-09-17 令)", "sides": {}}
    for side, path in (("codex", a.codex), ("agent", a.agent)):
        rows = check_side(side, load(path), tasks, work, a.timeout)
        prog = [r for r in rows if r.get("kind") == "program"]
        out["sides"][side] = {
            "summary": rel(path),
            "program_tasks": len(prog),
            "exec_ok": sum(1 for r in prog if r.get("exec") == "ok"),
            "correct_n": sum(1 for r in prog if r.get("correct")),
            "rows": rows,
        }
    bad = []
    for side, s in out["sides"].items():
        for r in s["rows"]:
            if r.get("kind") == "program" and (r.get("exec") != "ok" or not r.get("correct")):
                bad.append("%s/%s exec=%s correct=%s cases=%s/%s" %
                           (side, r["tid"], r.get("exec"), r.get("correct"),
                            r.get("cases_pass"), r.get("cases_n")))
    out["executable_and_correct"] = not bad
    out["blocked"] = bad
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    for side, s in out["sides"].items():
        print("%-6s program=%d exec_ok=%d correct=%d" % (side, s["program_tasks"], s["exec_ok"], s["correct_n"]))
        for r in s["rows"]:
            if r.get("kind") == "program":
                print("   %-5s %-24s graded=%-8s exec=%-6s cases=%s/%s correct=%s src=%s" %
                      (r["tid"], r.get("family"), r.get("graded_mode"), r.get("exec"),
                       r.get("cases_pass"), r.get("cases_n"), r.get("correct"), r.get("code_source")))
            else:
                print("   %-5s %-24s (kind=%s) correct=%s" % (r["tid"], r.get("family"), r.get("kind"), r.get("correct")))
    print("EXECUTABLE_AND_CORRECT=%s" % out["executable_and_correct"])
    if bad:
        print("BLOCKED: " + " | ".join(bad))
    print("OUT=" + a.out)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
