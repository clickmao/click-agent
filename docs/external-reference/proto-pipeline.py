#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R1 管道：由「精准语义」驱动的确定性执行器（fail-closed）。

分层（对应 Fable 5.1 的「安全在每个能力边界再断言」设计）:
  闸0 契约校验   → 不过 = 不执行, rc=3
  闸1 硬门/intent → refusal / 非执行类 = 不执行
  闸2 语义完整   → missing_slots 或 ambiguities 非空 = 停下要澄清, rc=2
  闸3 计划合法性 → 工具白名单 + DAG + 路径不得逃出沙箱, rc=4
  闸4 执行       → 逐步骤写/跑, 逐步留 rc/stdout 证据
"""
import json
import os
import subprocess

BANNED = ("sudo", "rm -rf /", "curl ", "wget ", "pip install", "apt-get", "git push",
          "chmod 777", ":(){", "mkfs", "dd if=")


class Halt(Exception):
    def __init__(self, rc, stage, reason):
        super().__init__(reason)
        self.rc, self.stage, self.reason = rc, stage, reason


def gate_scope(path, sandbox):
    """路径合法性：必须落在沙箱根内（拒绝绝对路径 / .. 逃逸 / 符号链接逃逸）。"""
    if os.path.isabs(path):
        raise Halt(4, "scope", "拒绝绝对路径: %s" % path)
    full = os.path.realpath(os.path.join(sandbox, path))
    root = os.path.realpath(sandbox)
    if not (full == root or full.startswith(root + os.sep)):
        raise Halt(4, "scope", "路径逃出沙箱: %s -> %s" % (path, full))
    return full


def gate_plan(plan, sandbox):
    ids = []
    for st in plan:
        tid, tool, args = st["id"], st["tool"], st.get("args") or {}
        if tool not in ("write_file", "run", "none"):
            raise Halt(4, "plan", "非白名单工具: %r" % tool)
        for d in st.get("depends_on") or []:
            if d not in ids:
                raise Halt(4, "plan", "depends_on 引用不存在/后置: %r (step %s)" % (d, tid))
        if tool == "write_file":
            gate_scope(args["path"], sandbox)
        if tool == "run":
            cmd = args["cmd"]
            for b in BANNED:
                if b in cmd:
                    raise Halt(4, "plan", "命令含禁用片段 %r: %s" % (b, cmd))
        ids.append(tid)


def execute(plan, sandbox, timeout_s=60):
    ev = []
    for st in plan:
        tool, args = st["tool"], st.get("args") or {}
        if tool == "write_file":
            full = gate_scope(args["path"], sandbox)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8", newline="\n") as f:
                f.write(args["content"])
            ev.append({"id": st["id"], "tool": tool, "path": args["path"],
                       "bytes": len(args["content"].encode()), "rc": 0})
        elif tool == "run":
            p = subprocess.run(["bash", "-lc", args["cmd"]], cwd=sandbox, timeout=timeout_s,
                               capture_output=True, text=True)
            out = (p.stdout or "").strip()
            exp = args.get("expect_stdout")
            ok = (p.returncode == 0) and (exp is None or out == exp)
            ev.append({"id": st["id"], "tool": tool, "cmd": args["cmd"], "rc": p.returncode,
                       "stdout": out[:400], "expect_stdout": exp, "ok": ok})
            if not ok:
                raise Halt(5, "exec", "步骤 %s 未达期望: rc=%d stdout=%r expect=%r"
                           % (st["id"], p.returncode, out[:200], exp))
        else:
            ev.append({"id": st["id"], "tool": tool, "rc": 0})
    return ev


def run(sem, sandbox, outdir):
    """sem=精准语义 dict; 返回 (rc, 证据 dict)。"""
    rec = {"intent": sem["intent"], "confidence": sem["confidence"], "evidence": [],
           "entities": sem["entities"], "constraints": sem["constraints"]}
    try:
        if sem.get("refusal"):
            raise Halt(3, "hard_gate", "模型判定应拒答: %s" % sem["refusal"]["reason"])
        if sem.get("missing_slots") or sem.get("ambiguities"):
            raise Halt(2, "semantics_incomplete",
                       "缺信息/有歧义 ⇒ 停下澄清: slots=%s amb=%s"
                       % (sem.get("missing_slots"), [a["issue"] for a in sem.get("ambiguities") or []]))
        if sem["intent"] not in ("code_task", "ops_task"):
            raise Halt(0, "non_exec", "intent=%s 无需执行（信息类）" % sem["intent"])
        gate_plan(sem["plan"], sandbox)
        rec["evidence"] = execute(sem["plan"], sandbox)
    except Halt as h:
        rec.update({"rc": h.rc, "stage": h.stage, "reason": h.reason, "halted": True})
    else:
        rec.update({"rc": 0, "stage": "done", "halted": False})
    with open(os.path.join(outdir, "pipeline-run.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    return rec["rc"], rec
