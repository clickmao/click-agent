#!/usr/bin/env python3
"""R449 验收补 · AOT 形态下 think-memory 开关的**机检**（预注册判据, fail-closed）。

背景（为什么要有这个器具）:
  计划 §4 机检② 预注册「每档 `think_memory_boot` 必带 enabled/mode/loaded 字段, 缺字段 fail-closed」,
  但首版遥测只发了 `embedder_injected/available/instance` ⇒ 开关**只改行为、不可观测**,
  消融 C5「各档打点形状互不相同」无从机检。本器具把该判据落成可复算的读数。

臂（同一二进制、同一 cwd 模板, 单变量 = 环境变量）:
  ARM-OFF : AGENTFRAMEWORK_THINK_MEMORY=off（全关: 不读盘/不落盘/不召回）
  ARM-ON  : 不设该变量（默认档 = 现网行为）
  NC-TEL  : ARM-OFF + AGENTFRAMEWORK_TELEMETRY=off（**器具负控**: 必须读不到 boot 记录）

预注册判据（合取; 任一 FAIL ⇒ 退出码 3）:
  V1 非空心   : 两臂都**必须**存在 think_memory_boot 且含 mode/enabled/loaded/records 四字段。
                缺任一字段 ⇒ 该臂记 n/a（不得以「没打点」冒充「档位无效」）。
  V2 档位实读 : OFF ⇒ mode=="off" ∧ enabled==False；ON ⇒ mode=="on" ∧ enabled==True。
  V3 读盘成对 : OFF ⇒ loaded==0 ∧ records==0；ON ⇒ loaded>0 ∧ records>0
                （成对才有判别力: 证明 OFF 的 0 不是「库本来就空」）。
  V4 不落盘   : OFF 臂库文件 (bytes, sha256, mtime_ns) 跑前跑后**逐位相同**。
  V5 形态自证 : 两臂 rc==0 ∧ stdout 含 "NativeAOT"（读数来自 AOT 产物, 非 IL apphost）。
  NC 判别力   : NC-TEL 臂必须**读不到** boot 记录（否则 V1 的「存在」是仪器噪声/文件残留）。

用法: python3 verify_boot_telemetry.py --bin /tmp/pub_r449b/agenthost [--json out.json] [--work /tmp/r449-aot]
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = "/home/agentuser/AgentFramework"
LIB_SEED = os.path.join(ROOT, "data", "think-memory.json")
FIELDS = ("mode", "enabled", "loaded", "records")


def digest(path):
    if not os.path.exists(path):
        return None
    b = open(path, "rb").read()
    st = os.stat(path)
    return {"exists": True, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
            "mtime_ns": st.st_mtime_ns}


def read_boot(telemetry_dir):
    """返回 (found: bool, record: dict|None, n_lines)。"""
    p = os.path.join(telemetry_dir, "host.jsonl")
    if not os.path.exists(p):
        return False, None, 0
    rec, n = None, 0
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        n += 1
        try:
            o = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if o.get("point") == "think_memory_boot":
            rec = o
    return rec is not None, rec, n


def run_arm(bin_path, work, arm, env_mode, telemetry_off=False, timeout=180):
    d = os.path.join(work, arm)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(os.path.join(d, "data"), exist_ok=True)
    lib = os.path.join(d, "data", "think-memory.json")
    if os.path.exists(LIB_SEED):
        shutil.copy2(LIB_SEED, lib)
    before = digest(lib)

    env = {k: v for k, v in os.environ.items() if not k.startswith("AGENTFRAMEWORK_")}
    env["DOTNET_ROOT"] = os.path.expanduser("~/.dotnet")
    if env_mode is not None:
        env["AGENTFRAMEWORK_THINK_MEMORY"] = env_mode
    if telemetry_off:
        env["AGENTFRAMEWORK_TELEMETRY"] = "off"

    p = subprocess.run([os.path.abspath(bin_path)], cwd=d, env=env, input="/exit\n",
                       capture_output=True, text=True, timeout=timeout)
    out = (p.stdout or "") + (p.stderr or "")
    found, rec, nlines = read_boot(os.path.join(d, "data", "telemetry"))
    after = digest(lib)
    return {"arm": arm, "env": {"AGENTFRAMEWORK_THINK_MEMORY": env_mode,
                                "AGENTFRAMEWORK_TELEMETRY": "off" if telemetry_off else None},
            "rc": p.returncode,
            "stdout_has_nativeaot": "NativeAOT" in out,
            "stdout_head": out.strip().splitlines()[0] if out.strip() else "",
            "telemetry_lines": nlines,
            "boot_found": found, "boot": rec,
            "lib_before": before, "lib_after": after,
            "lib_unchanged": before == after,
            "lib_seeded": before is not None}


def kv(rec):
    return (rec or {}).get("kv") or {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    ap.add_argument("--json")
    ap.add_argument("--work", default="/tmp/r449-aot")
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    bin_digest = digest(a.bin)
    if bin_digest is None:
        print(f"[致命] 被测二进制不存在: {a.bin}")
        return 2

    print("=== R449 验收补 · AOT 形态开关机检（预注册 V1..V5 + NC）===")
    print(f"被测二进制: {os.path.abspath(a.bin)}  sha256={bin_digest['sha256'][:16]}  bytes={bin_digest['bytes']}")
    arms = [run_arm(a.bin, a.work, "ARM-OFF", "off"),
            run_arm(a.bin, a.work, "ARM-ON", None),
            run_arm(a.bin, a.work, "NC-TEL", "off", telemetry_off=True)]
    checks = {}
    for r in arms:
        print(json.dumps({k: r[k] for k in ("arm", "rc", "stdout_has_nativeaot", "telemetry_lines",
                                            "boot_found", "lib_seeded", "lib_unchanged")},
                         ensure_ascii=False))
        if r["boot"]:
            print("   boot.kv =", json.dumps(kv(r["boot"]), ensure_ascii=False))

    off, on, nc = arms
    off_kv, on_kv = kv(off["boot"]), kv(on["boot"])

    missing_off = [f for f in FIELDS if f not in off_kv]
    missing_on = [f for f in FIELDS if f not in on_kv]
    checks["V1a_off_boot_has_fields"] = (off["boot_found"] and not missing_off)
    checks["V1b_on_boot_has_fields"] = (on["boot_found"] and not missing_on)
    checks["V2a_off_mode_enabled"] = (off_kv.get("mode") == "off" and off_kv.get("enabled") is False)
    checks["V2b_on_mode_enabled"] = (on_kv.get("mode") == "on" and on_kv.get("enabled") is True)
    checks["V3a_off_no_read"] = (off_kv.get("loaded") == 0 and off_kv.get("records") == 0)
    checks["V3b_on_read_nonempty"] = ((on_kv.get("loaded") or 0) > 0 and (on_kv.get("records") or 0) > 0)
    checks["V4_off_no_persist"] = (off["lib_seeded"] and off["lib_unchanged"])
    checks["V5a_rc_zero"] = all(r["rc"] == 0 for r in arms)
    checks["V5b_nativeaot_banner"] = all(r["stdout_has_nativeaot"] for r in arms)
    checks["NC_telemetry_off_yields_no_boot"] = (not nc["boot_found"])

    for k, v in checks.items():
        print(f"{k} = {'PASS' if v else 'FAIL'}")
    if missing_off or missing_on:
        print(f"[n/a 纪律] 缺字段: off={missing_off} on={missing_on} ⇒ 相关计数读数记 n/a, 不记 0")
    verdict = "PASS" if all(checks.values()) else "RED"
    print(f"裁决: {verdict}")
    if a.json:
        json.dump({"bin": os.path.abspath(a.bin), "bin_sha256": digest(a.bin)["sha256"],
                   "ts": datetime.now(timezone.utc).isoformat(), "arms": arms,
                   "checks": checks, "missing_fields": {"off": missing_off, "on": missing_on},
                   "verdict": verdict}, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[written] {a.json}")
    return 0 if verdict == "PASS" else 3


if __name__ == "__main__":
    sys.exit(main())
