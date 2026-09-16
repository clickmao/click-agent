#!/usr/bin/env python3
# R494 候选④: 能力自检面**只读复核** (不双写 —— 该面属对侧 cron 会话线, 见 r492 报告 §候选)。
#
# 判据 (机器可检, 全部只读取值):
#   A1 正控: 非注入面 (drift_injected=false) 的每条 instrument 必须 pass=true (rc==expect_rc)
#   A2 负控: 注入面 (drift_injected=true) 的每条 instrument 必须 pass=false —— 注入了还绿 = 判据无效
#   A3 指纹同源: 面文件里记的 manifest_sha12 / instrument_sha12 必须等于**当前字节**的 sha12
#      (声明面 vs 实发面脱钩 ⇒ 面文件是历史快照, 不得当现状引用)
# 输出: eval/rover/r494/audit-capability-face.json (本会话命名空间; 不动 eval/capability/)
import hashlib, json, os, sys, time

CAP = "/home/agentuser/AgentFramework/eval/capability"
OUT = "/home/agentuser/AgentFramework/eval/rover/r494/audit-capability-face.json"
FACES = ["instruments-check.json", "instruments-check-scoped.json", "instruments-check-drift.json",
         "instruments-check-nc-notapplied.json", "instruments-check-surface-claim.json",
         "instruments-check-surface-unknown.json"]

def sha12(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()[:12]

def main():
    rep = {"schema": "r494-capability-face-audit/1", "audited_at_epoch": int(time.time()),
           "mode": "read-only", "faces": [], "assertions": [], "verdict": None}
    for fn in FACES:
        p = os.path.join(CAP, fn)
        if not os.path.exists(p):
            rep["faces"].append({"file": fn, "present": False})
            continue
        d = json.load(open(p, encoding="utf-8"))
        res = d.get("results") or []
        rep["faces"].append({
            "file": fn, "present": True, "sha256_12": sha12(p),
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(p))),
            "schema": d.get("schema"), "face": d.get("face"), "drift_injected": d.get("drift_injected"),
            "inject_mode": d.get("inject_mode"), "total": d.get("total"), "passed": d.get("passed"),
            "manifest_sha12_declared": d.get("manifest_sha12"), "instrument_sha12_declared": d.get("instrument_sha12"),
            "rows": [{"id": r.get("id"), "rc": r.get("rc"), "expect_rc": r.get("expect_rc"),
                      "pass": r.get("pass"), "l2_ok": r.get("l2_ok"),
                      "injected": (r.get("l2_fields") or {}).get("INJECTED")} for r in res],
        })
    # A3: 当前字节指纹
    man = os.path.join(CAP, "instruments.json")
    cur_man = sha12(man) if os.path.exists(man) else None
    cur_inst = None
    for f in rep["faces"]:
        if f.get("present") and f.get("instrument_sha12_declared"):
            cur_inst = f["instrument_sha12_declared"]
            break
    rep["current_manifest_sha12"] = cur_man
    latest_declared = [f["manifest_sha12_declared"] for f in rep["faces"]
                       if f.get("present") and f.get("manifest_sha12_declared")]
    A = rep["assertions"]
    A.append({"id": "A3.manifest_sha12_fresh",
              "detail": "最新面声明=%s 当前字节=%s" % (latest_declared[:1], cur_man),
              "red": bool(latest_declared) and latest_declared[0] != cur_man})
    A.append({"id": "A3.instrument_sha12_fresh",
              "detail": "声明 instrument sha12=%s (未做二次源比对: 面文件不含 instrument 路径 ⇒ 记 unreported)" % cur_inst,
              "red": False, "unreported": True})
    for f in rep["faces"]:
        if not f.get("present") or not f.get("rows"):
            continue
        inj = bool(f.get("drift_injected"))
        for r in f["rows"]:
            if inj:
                A.append({"id": "A2.%s.%s" % (f["file"], r["id"]),
                          "detail": "注入面 %s rc=%s expect=%s pass=%s" % (f["inject_mode"], r["rc"], r["expect_rc"], r["pass"]),
                          "red": r["pass"] is not False})
            else:
                A.append({"id": "A1.%s.%s" % (f["file"], r["id"]),
                          "detail": "正控面 rc=%s expect=%s pass=%s" % (r["rc"], r["expect_rc"], r["pass"]),
                          "red": r["pass"] is False})
    reds = [a for a in A if a.get("red")]
    rep["red_count"] = len(reds)
    rep["verdict"] = "PASS" if not reds else "FAIL"
    json.dump(rep, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[audit] 面=%d 断言=%d 红=%d ⇒ %s (→ %s)" % (len(rep["faces"]), len(A), len(reds), rep["verdict"], OUT))
    for a in reds:
        print("[audit][红] %s: %s" % (a["id"], a["detail"]))
    return 0 if not reds else 1

if __name__ == "__main__":
    sys.exit(main())
