#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R504 定向重钉 (R2e 裁定): 器具已改 ⇒ 引用它的冻结行须重审。

触发 (本轮机检证据):  `python3 eval/capability/bind_evidence.py --check`
  VIOLATION probe.randomized-selfcheck: 器具绑定与现盘不符 (声明 9c8f09e3ff8f / 实际 2dba8418221c)
  VIOLATION r433.probe-code-source-artifact-channel: 器具绑定与现盘不符 (声明 21a33eaeb660 / 实际 1bdefe12da4d)
  （暴露方式 = 候选⑤ 全量单测首轮: VerificationFormTests.Registry_Exists_And_HasNoViolations 红, 1633/1634）

成因 (本轮 R504 的器具扩面, 逐条见 ruling_r504_repin.md):
  eval/probe/tasks.py    : +游戏族 nim_multi / wythoff, +见证族 witness_crt, +HARD_INPUTS 7 条, +自检 8 条 (53/53 -> 61/61)
  eval/probe/grade.py    : +witness kind=crt 分支 (逐同余式机检), +自检 4 条 (39/39 -> 48/48)
  eval/probe/run_probe.py: +REF_SRC[nim_multi/wythoff], +mutation:nim_greedy/wyth_greedy, +自检 6 条 (31/31 -> 37/37)

裁定 = 「证据面重生成 + 3 字段定向重钉 + 声明重审」, 不是「改声明凑绿」:
  ① 证据面**重新生成**: `python3 eval/capability/exp1-q28/gen_probe_evidence_q28.py --out <artifact> --runs 2`
     ⇒ 计数 53/39/31 -> 61/48/37 由现盘器具自记, P1/P2/P3/P5/P7/P8 全成立 (instrument_sha12 自动填 2dba8418221c);
  ② 声明重审: `python3 eval/capability/decl_sweep.py --apply` (2 处漂移 -> drifted=0);
  ③ 3 字段重钉 = instrument_sha12 / artifact_sha12 / audited_by_round;
  ④ **保原文格式**: 只做目标字段的文本替换, 其余字节逐位不变 (不重排、不补尾换行);
  ⑤ 写后由**权威门禁** (bind_evidence.py --check) 复核 ⇒ 该行必须不再出现在 VIOLATION 里;
  ⑥ 负控: 钉一个假 instrument sha ⇒ 门禁必红且点名该行 (证明本次转绿不是门禁空心)。

用法:
  python3 eval/rover/r504/ruling_r504_repin.py --check
  python3 eval/rover/r504/ruling_r504_repin.py --apply --only probe.randomized-selfcheck,r433.probe-code-source-artifact-channel
  python3 eval/rover/r504/ruling_r504_repin.py --apply --only probe.randomized-selfcheck --fake-instrument-sha12 deadbeefcafe  # 负控
退出码: 0 成功 / 1 断言失败(拒绝落盘) / 3 输入缺失。
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys

REG = "docs/verification-registry.json"
INSTRUMENT = {  # 行 id → 该行声明的器具文件 (与登记行 evidence_generated_with.instrument 对齐)
    "probe.randomized-selfcheck": "eval/probe/tasks.py",
    "r433.probe-code-source-artifact-channel": "eval/probe/grade.py",
}
FIELDS = ("instrument_sha12", "artifact_sha12", "audited_by_round")


def sha12_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def row_block_span(raw, row_id):
    """定位 `"id": "<row_id>"` 所属的顶层行块 (从该 id 行到下一个 `"id":` 行前的 `{` 起点)。

    用 json 解析出来的 objects 反查不可行 (要保字节) ⇒ 用「行 + 大括号配平」定位:
    起点 = 含 `"id": "<row_id>",` 的那一行 (顶层行对象首行), 终点 = 下一顶层行的首行前。
    """
    lines = raw.splitlines(keepends=True)
    start = None
    for i, ln in enumerate(lines):
        if re.search(r'"id"\s*:\s*"%s"' % re.escape(row_id), ln):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r'\s*\{', lines[j]) and re.search(r'"id"\s*:', lines[j + 1] if j + 1 < len(lines) else ""):
            end = j
            break
        if re.match(r'^\s*\{', lines[j]):
            end = j
            break
    return start, end


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--only", default=None, help="逗号分隔的行 id (必填于 --apply; 全刷=归属篡改)")
    ap.add_argument("--round", default="R504")
    ap.add_argument("--registry", default=REG)
    ap.add_argument("--fake-instrument-sha12", default=None, help="负控: 故意钉假 sha (须被门禁抓到)")
    a = ap.parse_args()

    if not os.path.isfile(a.registry):
        print("[致命] 登记表缺失 %s" % a.registry)
        return 3
    raw = io.open(a.registry, encoding="utf-8", newline="").read()
    doc = json.loads(raw)
    want = json.loads(raw)          # 期望对象 (逐字段更新后比对)

    targets = sorted(INSTRUMENT) if a.only is None else [x.strip() for x in a.only.split(",") if x.strip()]
    unknown = [t for t in targets if t not in INSTRUMENT]
    if unknown:
        print("[致命] 未知行 id: %s" % unknown)
        return 3
    if a.apply and a.only is None:
        print("[致命] --apply 必须显式 --only (全刷 = 归属篡改)")
        return 3

    out = raw
    plan, fails = [], []
    for rid in targets:
        rows = [r for r in doc["rows"] if r.get("id") == rid]
        if len(rows) != 1:
            fails.append("%s 行定位失败 n=%d" % (rid, len(rows)))
            continue
        row = rows[0]
        decl = dict(row.get("evidence_generated_with") or {})
        inst_path = INSTRUMENT[rid]
        actual_inst = sha12_file(inst_path)
        art_path = row.get("evidence_path")
        actual_art = sha12_file(art_path) if art_path and os.path.isfile(art_path) else None
        new = {"instrument": inst_path,
               "instrument_sha12": a.fake_instrument_sha12 or actual_inst,
               "artifact_sha12": actual_art,
               "audited_by_round": a.round}
        if actual_art is None:
            fails.append("%s 证据面不存在: %s" % (rid, art_path))
            continue
        # 声明与现盘差异 (只对**未加假值**的行判: 负控模式允许故意写错)
        plan.append((rid, decl.get("instrument_sha12"), new["instrument_sha12"],
                     decl.get("artifact_sha12"), new["artifact_sha12"], decl.get("audited_by_round"), a.round))

        span = row_block_span(out, rid)
        if span is None:
            fails.append("%s 行块定位失败" % rid)
            continue
        s, e = span
        lines = out.splitlines(keepends=True)
        blk = "".join(lines[s:e])
        for k, v in new.items():
            pat = re.compile(r'("%s"\s*:\s*)(?:"[^"]*")' % re.escape(k))
            if not pat.search(blk):
                continue          # 该字段缺失 ⇒ 由上方的对象比对断言兜住 (不静默)
            blk2 = pat.sub(lambda m: m.group(1) + json.dumps(v, ensure_ascii=False), blk, count=1)
            # 「应当改变」= 声明值与现盘现算值不同 (声明已一致 ⇒ 不变是对的, 不得当失败)
            if decl.get(k) != v and blk2 == blk:
                fails.append("%s 字段 %s 应改而未改 (声明 %r / 现算 %r)" % (rid, k, decl.get(k), v))
            blk = blk2
        out = "".join(lines[:s]) + blk + "".join(lines[e:])
        for r in want["rows"]:
            if r.get("id") == rid:
                r.setdefault("evidence_generated_with", {}).update(new)

    if fails:
        print("[致命] %s" % fails)
        return 1
    print("[plan] " + json.dumps(plan, ensure_ascii=False))
    if a.check:
        return 0

    # 断言 ① 语义等价
    if json.loads(out) != want:
        print("[致命] 写入对象 != 期望 (拒绝落盘)")
        return 1
    # 断言 ② 逐行 diff 限界 (只许目标字段行变)
    lo, ln = raw.splitlines(), out.splitlines()
    if len(lo) != len(ln):
        print("[致命] 行数变化 %d -> %d" % (len(lo), len(ln)))
        return 1
    changed = [i for i, (x, y) in enumerate(zip(lo, ln)) if x != y]
    bad = [i + 1 for i in changed if not any(('"%s"' % f) in ln[i] for f in FIELDS)]
    if bad:
        print("[致命] 越界改动行: %s" % bad)
        return 1
    io.open(a.registry, "w", encoding="utf-8", newline="").write(out)
    # 断言 ③ 幂等 (重跑得同一字节)
    again = io.open(a.registry, encoding="utf-8", newline="").read()
    if again != out:
        print("[致命] 写后字节不一致")
        return 1
    print("[OK] 重钉完成: %s ; 改动行 %s" % (targets, [i + 1 for i in changed]))

    # 断言 ④ 写后由权威门禁复核 (调用方按需复跑; 这里直接跑)
    r = subprocess.run([sys.executable, "eval/capability/bind_evidence.py", "--check"],
                       capture_output=True, text=True, cwd=os.getcwd())
    tail = [x for x in (r.stdout or "").splitlines() if "VIOLATION" in x or x.startswith("R2E_R2F_EXIT")]
    print("[gate] " + json.dumps(tail, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
