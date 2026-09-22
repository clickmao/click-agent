#!/usr/bin/env python3
"""R630 · baselines.json 追加两条**冻结不变量**（spec 档 chars/sha）。

处置纪律（同 registry 重钉件）:
  ① 改前断言序列化器**逐字节复现原文件**（自动探测 indent / ensure_ascii / 末尾换行）；失败即拒改；
  ② 只追加两条新 entry，**不改动任何既有 entry**（numstat 量级复核）；
  ③ 幂等；④ 写后读回 + 跑 `status_gen.py --check`（漂移 0 / 缺源 0）。
用法: python3 eval/rover/r630/add_baselines_r630.py [--apply]
"""
import hashlib
import io
import json
import os
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
BL = os.path.join(REPO, "eval/capability/baselines.json")
SRC = "eval/rover/r630/prefix-r630.json"


def sha12(rel):
    with io.open(os.path.join(REPO, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:12]


def detect_serializer(raw, obj):
    for indent in (1, 2, None):
        for ea in (False, True):
            for tail in ("\n", ""):
                if json.dumps(obj, ensure_ascii=ea, indent=indent) + tail == raw:
                    return indent, ea, tail
    return None


def main():
    apply = "--apply" in sys.argv
    raw = io.open(BL, encoding="utf-8").read()
    d = json.loads(raw)
    det = detect_serializer(raw, d)
    if det is None:
        print("SER_ASSERT=FAIL ⇒ 拒改（无法逐字节复现原文件, 改法会重排整份文件）")
        return 3
    indent, ea, tail = det
    print("SER_ASSERT=OK (indent=%s, ensure_ascii=%s, tail=%r)" % (indent, ea, tail))

    pf = json.load(io.open(os.path.join(REPO, SRC), encoding="utf-8"))
    spec = pf["pin_spec_tier"]
    s12 = sha12(SRC)
    new = [
        {"id": "F_env.prefix.spec_chars", "face": "F_env", "kind": "frozen_invariant",
         "metric": "R630 治疗档（规格保真尾块）恒前缀字符数",
         "value": spec["chars"], "unit": "chars",
         "source_path": SRC, "source_sha12": s12,
         "check_cmd": "python3 -c \"import io,json;d=json.load(io.open('%s'));print(d['pin_spec_tier']['chars'])\"" % SRC,
         "threshold": "只许加厚：缺省档 %d → spec 档 %d（正文逐位为前缀 ∧ 只追加 <spec_fidelity> 尾块）"
                      % (pf["pin_current"]["chars"], spec["chars"]),
         "threshold_source": "%s:pin_spec_tier.chars" % SRC,
         "ground_rule": "跨轮禁相减；治疗档只作**轴档锚**，不得当作收益读数（R630 实测摆动 8 ≥ 效应 0 ⇒ 该轴定案关闭）",
         "negative_control": "eval/rover/r630/judge_r630.py --selftest（S2 变异：T 档落回缺省档 ⇒ 判 VOID rc=2）"},
        {"id": "F_env.prefix.spec_sha256", "face": "F_env", "kind": "frozen_invariant",
         "metric": "R630 治疗档恒前缀 sha256",
         "value": spec["sha256"], "unit": "hex64",
         "source_path": SRC, "source_sha12": s12,
         "check_cmd": "python3 -c \"import io,json;d=json.load(io.open('%s'));print(d['pin_spec_tier']['sha256'])\"" % SRC,
         "threshold": "四档 sha 互异（default/r615/legacy/spec）由 eval/rover/r630/gen_prefix_r630.py 机检 rc=0",
         "threshold_source": "%s:pin_spec_tier.sha256" % SRC,
         "ground_rule": "逐跑次 transcript.prefix_sha256 必须逐位等于本锚（T 档）；不等即轴未生效 ⇒ 整轮 VOID",
         "negative_control": "同 F_env.prefix.spec_chars（影子自检 7 态）"},
    ]
    have = {e["id"] for e in d["entries"]}
    add = [e for e in new if e["id"] not in have]
    print("ADD=%d (已有: %s)" % (len(add), [e["id"] for e in new if e["id"] in have]))
    if not apply or not add:
        print("DRY_RUN" if not apply else "IDEMPOTENT (无变化)")
        return 0
    d["entries"].extend(add)
    io.open(BL, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=ea, indent=indent) + tail)
    back = json.load(io.open(BL, encoding="utf-8"))
    print("READBACK_IDS=%s" % [e["id"] for e in back["entries"][-2:]])
    print("NUMSTAT:", subprocess.run(["git", "diff", "--numstat", "eval/capability/baselines.json"],
                                     cwd=REPO, capture_output=True, text=True).stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
