#!/usr/bin/env python3
"""EXP1-Q29: 自引用行的**块级**重审 (器具 sha 变 ⇒ 引用它的证据必须重审, 承 R409/Q24 缺陷族).

为什么不用 --apply: 实测其粒度为**全表**重审 (TOUCHED=104), 单行重审会被 103 行纯归属漂移淹没
(R481 曾为此回退 96 行)。故走块级替换: 断言全部前置条件 -> 只在该行块内替换 -> 写后读回 -> 幂等。
块级编辑纪律 (承 R409): ①序列化器逐字节复现断言 ②只补「前一行逗号」/不动行尾逗号 ③幂等 ④读回校验。
"""
import hashlib, json, os, subprocess, sys

ROUND = "EXP1-Q29"
TOOL = "eval/capability/bind_evidence.py"
REG = "docs/verification-registry.json"
ROW_ID = "r476.evidence-binding-round-param"
OLD_ROUND = "R478"


def root():
    return subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                          text=True, check=True).stdout.strip()


ROOT = root()


def rd(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def wr(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def main():
    reg_abs = os.path.join(ROOT, REG)
    raw = rd(reg_abs)
    doc = json.loads(raw)

    # --- 契约断言: 序列化器逐字节复现 (EXP1-Q29 修后器具同判据) ---
    ser = json.dumps(doc, indent=1, ensure_ascii=False)
    tail = "\n" if raw.endswith("\n") else ""
    if ser + tail != raw:
        print("BLOCK_ASSERT=FAIL 全文件不可逐字节复现 (禁改写)"); return 3
    print("BLOCK_ASSERT=OK (全文件逐字节复现, tail=%s)" % ("LF" if tail else "NONE"))

    new_sha12 = hashlib.sha256(open(os.path.join(ROOT, TOOL), "rb").read()).hexdigest()[:12]
    row = next((r for r in doc["rows"] if r.get("id") == ROW_ID), None)
    if row is None:
        print("MEASURE/row_missing %s" % ROW_ID); return 3
    f = row["evidence_generated_with"]
    old_pin = f["artifact_sha12"]
    if f["instrument_sha12"] != old_pin or row["evidence_path"] != TOOL or f["instrument"] != TOOL:
        print("MEASURE/row_shape_unexpected %s" % json.dumps(f, ensure_ascii=False)); return 3
    if new_sha12 == old_pin:
        print("IDEMPOTENT=OK (器具 sha 未变 %s, 无需重审)" % new_sha12)
        return 0

    # --- 块级定位 (只在该行对象内替换) ---
    i = raw.index('"id": "%s"' % ROW_ID)
    j = raw.index("\n  },", i) + len("\n  },")
    block = raw[i:j]
    n_sha = block.count(old_pin)
    n_round = block.count('"audited_by_round": "%s"' % OLD_ROUND)
    if n_sha != 2 or n_round != 1:
        print("MEASURE/block_shape old_pin x%d (exp 2), old_round x%d (exp 1)" % (n_sha, n_round)); return 3
    new_block = block.replace(old_pin, new_sha12).replace('"audited_by_round": "%s"' % OLD_ROUND,
                                                          '"audited_by_round": "%s"' % ROUND)
    out = raw[:i] + new_block + raw[j:]
    # 结构不变式: 行数相同 ∧ 仅 ROW_ID 行可变 ∧ 其余行逐字段相同 ∧ 该行只有 3 键变
    #   (首版误用「总长度不变」做断言 —— 轮号 R478→EXP1-Q29 本身就会改长度, 属判据缺陷, 已换)
    d_new = json.loads(out)
    if len(d_new["rows"]) != len(doc["rows"]):
        print("BLOCK_ASSERT=FAIL 行数变化 %d -> %d" % (len(doc["rows"]), len(d_new["rows"]))); return 3
    by_new = {r.get("id"): r for r in d_new["rows"]}
    changed_rows = []
    for r in doc["rows"]:
        if r != by_new.get(r.get("id")):
            changed_rows.append(r.get("id"))
    if changed_rows != [ROW_ID]:
        print("BLOCK_ASSERT=FAIL 变动行非唯一: %s" % changed_rows); return 3
    f1 = row["evidence_generated_with"]
    f2 = by_new[ROW_ID]["evidence_generated_with"]
    ck = sorted(k for k in set(f1) | set(f2) if f1.get(k) != f2.get(k))
    if ck != ["artifact_sha12", "audited_by_round", "instrument_sha12"]:
        print("BLOCK_ASSERT=FAIL 变更键集非预期: %s" % ck); return 3
    print("BLOCK_ASSERT=OK (行数不变 ∧ 仅 %s 变 ∧ 变更键集=%s)" % (ROW_ID, ck))

    wr(reg_abs, out)
    back = rd(reg_abs)
    if back != out:
        print("WRITE_READBACK=MISMATCH"); return 2
    print("WRITE_READBACK=OK")
    d2 = json.loads(back)
    r2 = next(r for r in d2["rows"] if r.get("id") == ROW_ID)["evidence_generated_with"]
    ok = (r2["artifact_sha12"] == new_sha12 and r2["instrument_sha12"] == new_sha12
          and r2["audited_by_round"] == ROUND and r2["binding"] == f["binding"])
    print("REPIN_VERIFY=%s (artifact=%s instrument=%s round=%s)"
          % ("OK" if ok else "FAIL", r2["artifact_sha12"], r2["instrument_sha12"], r2["audited_by_round"]))
    ser2 = json.dumps(d2, indent=1, ensure_ascii=False)
    print("TAIL_FORM_PRESERVED=%s" % (ser2 + tail == back))
    print("ROW_COUNT %d -> %d" % (len(doc["rows"]), len(d2["rows"])))
    print(subprocess.run(["git", "diff", "--numstat", "--", REG], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip())
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
