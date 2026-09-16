#!/usr/bin/env python3
# R495 pin: **src 树哈希 + 产物 sha 双钉** (R494 候选③)。
#
# 动因 (R494 教训): AOT 产物的 sha256 会随 obj/ 中间生成物漂移 (语义未变) ⇒ 只钉产物会把
# "中间物重生成"误判成"链代码变了"; 只钉 src 又挡不住"产物是旧构建"。故双钉 + 显式记录
# 树态 (committed vs dirty), dirty 时降级为 unreported 并列出脏文件 (禁冒充干净)。
#
# 台账核对码配方也在此钉定 (判据器/复核器必须同一配方, 详见 LocalDecisionLedger.CodeOf)。
import hashlib, json, os, subprocess, sys, time

ROOT = "/home/agentuser/AgentFramework"
OUT = os.path.join(ROOT, "eval/rover/r495/pin-r495.json")
HOST = os.environ.get("AGENTFRAMEWORK_HOST_BIN", "/tmp/pub_r495/agenthost")


def sh(*a):
    return subprocess.run(a, cwd=ROOT, capture_output=True, text=True).stdout.strip()


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    rep = {"schema": "r495-pin/1", "ts_epoch": int(time.time()), "round": "R495"}
    rep["git_head"] = sh("git", "rev-parse", "HEAD")
    rep["src_tree"] = sh("git", "rev-parse", "HEAD:src")          # 已提交 src 树对象哈希 (稳定)
    rep["src_tree_head_only"] = True
    dirty = [l[3:] for l in sh("git", "status", "--porcelain", "--", "src/").splitlines() if l.strip()]
    rep["src_dirty"] = dirty
    rep["src_tree_effective"] = rep["src_tree"] if not dirty else None
    rep["src_tree_effective_kind"] = "committed-tree" if not dirty else "unreported (工作树脏: 树哈希不含未提交改动)"
    if os.path.exists(HOST):
        rep["host_path"] = HOST
        rep["host_sha256"] = sha256(HOST)
        rep["host_bytes"] = os.path.getsize(HOST)
        rep["host_mtime_epoch"] = int(os.path.getmtime(HOST))
    else:
        rep["host_sha256"] = None
        rep["host_bytes"] = None
        rep["host_note"] = "unreported: 产物不存在"
    rep["obj_drift_note"] = ("AOT 产物 sha 随 obj/ 中间生成物漂移(语义未变) ⇒ 与 src_tree 双钉: "
                             "src_tree 变=语义变; host_sha256 变而 src_tree 同=构建面漂移")
    rep["ledger_code_recipe"] = "LCM- + sha256(session_raw + '|' + '\\n'.join(f'{turn}|{kind}|{chars}'))[:12] 小写 hex"
    rep["mount_header"] = "[本地决策台账-链自持]"
    json.dump(rep, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: rep[k] for k in ("git_head", "src_tree", "src_tree_effective_kind",
                                          "src_dirty", "host_sha256", "host_bytes")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
