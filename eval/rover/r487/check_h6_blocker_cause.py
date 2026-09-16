#!/usr/bin/env python3
"""R487 候选④ 机检: 起手闸 blocker_cause **多因并列** (禁二选一) 的差分负控。

语言无关: 只做进程/内存事实判定与 JSON 字段断言。
三态: rc=0 PASS / rc=2 断言失败 (fail-closed) / rc=3 缺输入 (弃权)。

判据 (预注册 H6):
  C1 常规 (无开关)              ⇒ rc=0  PASS, blocker_causes == []
  C2 --nc-block (门槛不可达)     ⇒ rc=2  GATE_BLOCKED, causes == ["内存不足"]
  C3 --nc-both + 人造 build-server 进程 ⇒ rc=2, causes == ["内存不足","build-server 残留"]  (causes_n == 2)
差分性 (承重): 修前的三元表达式**只能**产出单条字符串 ⇒ C3 的 causes_n=2 在修前不可达
  (修前代码由 git 保留: `git show <R487 前>:eval/rover/r483/preflight_gate.py`)。
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "eval" / "rover" / "r483" / "preflight_gate.py"
OUTD = ROOT / "eval" / "rover" / "r487"
FAKE_DIR = Path("/tmp/nc_r487")


def run_gate(args):
    out = OUTD / ("preflight_%s.json" % args["tag"])
    cmd = [sys.executable, str(GATE), "--out", str(out), "--round", args["round"], "--settle-max", "4"] + args["flags"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    rec = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    return p.returncode, rec


def spawn_fake_build_server():
    """人造 build-server 残留进程: 以 argv0 = VBCSCompiler 执行 sleep (RSS 极小 ⇒ 不干扰 mem 因)。"""
    FAKE_DIR.mkdir(parents=True, exist_ok=True)
    link = FAKE_DIR / "VBCSCompiler"
    if link.exists() or link.is_symlink():
        link.unlink()
    os.symlink(shutil.which("sleep") or "/usr/bin/sleep", link)
    proc = subprocess.Popen([str(link), "60"])
    time.sleep(0.5)
    # 自证: 该进程确实被闸的扫描口径看见 (argv0 非 shell ∧ cmd 含监视字串)
    seen = False
    for pe in Path("/proc").iterdir():
        if not pe.name.isdigit():
            continue
        try:
            raw = (pe / "cmdline").read_bytes().decode("utf-8", "replace")
        except OSError:
            continue
        if raw.startswith(str(link)):
            seen = True
            break
    return proc, seen


def main():
    if not GATE.is_file():
        print("MISS: 缺闸器具", GATE)
        return 3
    readings = {"round": "R487", "gate_tool": str(GATE.relative_to(ROOT)), "cases": {}, "asserts": {}}

    # ---- C1 常规: 须 PASS 且 causes 为空表 ----
    rc1, r1 = run_gate({"tag": "h6_c1", "round": "R487", "flags": []})
    readings["cases"]["C1_plain"] = {"rc": rc1, "verdict": r1.get("verdict"),
                                     "blocker_causes": r1.get("blocker_causes"),
                                     "mem_available_mb": r1.get("mem_available_mb")}
    a1 = (rc1 == 0 and r1.get("verdict") == "PASS" and r1.get("blocker_causes") == [])

    # ---- C2 单因 (mem): 门槛抬到不可达 ----
    rc2, r2 = run_gate({"tag": "h6_c2", "round": "R487", "flags": ["--nc-block"]})
    readings["cases"]["C2_nc_block"] = {"rc": rc2, "verdict": r2.get("verdict"),
                                        "blocker_causes": r2.get("blocker_causes"),
                                        "blocker_cause": r2.get("blocker_cause")}
    a2 = (rc2 == 2 and r2.get("verdict") == "GATE_BLOCKED"
          and r2.get("blocker_causes") == ["内存不足"] and r2.get("blocker_cause") == "内存不足")

    # ---- C3 双因并列: mem (门槛不可达) ∧ build-server 残留 (人造进程) ----
    proc, seen = spawn_fake_build_server()
    try:
        rc3, r3 = run_gate({"tag": "h6_c3", "round": "R487", "flags": ["--nc-both"]})
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    causes3 = r3.get("blocker_causes") or []
    readings["cases"]["C3_nc_both"] = {"rc": rc3, "verdict": r3.get("verdict"),
                                       "blocker_causes": causes3,
                                       "blocker_cause": r3.get("blocker_cause"),
                                       "blockers": r3.get("blockers"),
                                       "fake_proc_seen_by_scan": seen,
                                       "causes_n": len(causes3)}
    a3 = (rc3 == 2 and causes3 == ["内存不足", "build-server 残留"]
          and r3.get("blocker_cause") == "内存不足+build-server 残留"
          and seen and any(p.get("watch") == "VBCSCompiler" for p in (r3.get("blockers") or [])))

    readings["asserts"] = {"C1_pass_and_empty_causes": a1, "C2_single_cause_mem": a2,
                           "C3_two_causes_parallel": a3}
    readings["verdict"] = "PASS" if (a1 and a2 and a3) else "FAIL"
    (OUTD / "h6_blocker_cause_readings.json").write_text(
        json.dumps(readings, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(readings, ensure_ascii=False, indent=1, sort_keys=True))
    return 0 if readings["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
