#!/usr/bin/env python3
"""R462 判分器具 —— 只读**产品实发全文** (full-*.json, ADAPTER_DUMP_FULL=1) + 轮结果, 不重建 prompt。

判据 (预注册, 见 prereg-r462-e2e.json):
  P1 召回-现实一致性闸生效: 实发注入面出现 `[核验✗` 且同片段引用 report.md (不存在的文件) ⇒ 陈旧召回可见
  P2 语言无关召回: 注入面含 `[工作区文件 logic.unit]` (文本/非白名单后缀) 且**不含** blob.bin (含 NUL 二进制)
  P3 只打假 ⇒ 零 token 成本: 实发面**不得**出现 `[核验✓` (一致时不注入字节)
  P4 不回退: 6 轮 ok; 产物 count.txt=4 / merged.txt 三行 / stats.txt=chars=14 / first.txt; 契约声明不上前台
负控 (判别力): 用 R461 实发全文跑 P1/P2 同判据 ⇒ 必须为 False (旧二进制无闸/白名单)
"""
import glob
import json
import os
import re
import sys

A = "/home/agentuser/AgentFramework"
E = os.environ.get("R462_ENV", "/tmp/r462_env")
OUT = os.path.join(E, "logs")


def load_full(root):
    texts = []
    for p in sorted(glob.glob(os.path.join(root, "adapter", "full-*.json"))):
        try:
            msgs = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        for m in msgs if isinstance(msgs, list) else []:
            c = m.get("content") if isinstance(m, dict) else None
            if isinstance(c, str):
                texts.append(c)
    return texts


def load_turns(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
        return d.get("turns", []) if isinstance(d, dict) else []
    except Exception:
        return []


def main():
    texts = load_full(OUT)
    joined = "\n".join(texts)
    turns = load_turns(os.path.join(OUT, "agent-turns.jsonl"))
    work = os.path.join(E, "agent", "work")

    def read(name):
        try:
            return open(os.path.join(work, name), encoding="utf-8", errors="replace").read()
        except Exception:
            return ""

    bad_hits = [t for t in texts if "核验✗" in t]
    p1 = bool(bad_hits) and any("report.md" in t for t in bad_hits)
    # P2 (v3 修订): 只对**召回通道**断言 —— 运行期的 list_dir 工具结果会合法地列出 blob.bin 文件名。
    p2 = ("[工作区文件 logic.unit]" in joined) and ("[工作区文件 blob.bin]" not in joined)
    # P3 (v2 修订): 「只打假」是**工作区召回片段**的契约 (逐轮进 prompt ⇒ 一致时零字节);
    #   记忆块 (SessionMemoryBlock) 走全标注 ⇒ 允许出现 ✓。故只在召回片段内断言无 ✓。
    p3 = True
    for t in texts:
        for seg in re.split(r"(?=\[工作区文件 )", t):
            if seg.startswith("[工作区文件 ") and "核验✓" in seg.split("\n\n")[0]:
                p3 = False
    count_ok = read("count.txt").strip() == "4"
    merged = read("merged.txt")
    merged_ok = merged.count("\n") >= 2 and "ALPHA" in merged and "BETA" in merged and "GAMMA" in merged
    stats_ok = "chars=14" in read("stats.txt")
    first_ok = read("first.txt").strip().startswith("R455 fixture note")
    # P4 (v3 修订): 契约声明只看**回复面** —— system prompt 里对模型的契约说明不是「上前台」。
    replies = "\n".join((t.get("reply") or "") for t in turns)
    contract_front = bool(re.search(r"clickproof|no_formal\s*:|^premise\s*:|^goal\s*:", replies, re.M))
    p4 = (len(turns) == 7 and all(t.get("ok") for t in turns)
          and count_ok and merged_ok and stats_ok and first_ok and not contract_front)

    verdict = {
        "round": "R462",
        "env": E,
        "n_full_msgs": len(texts),
        "checks": {
            "P1_recall_reality_gate_visible": p1,
            "P2_language_agnostic_recall": p2,
            "P3_fail_only_zero_token": p3,
            "P4_no_regress": p4,
        },
        "detail": {
            "核验✗_blocks": len(bad_hits),
            "logic.unit_recalled": "[工作区文件 logic.unit]" in joined,
            "blob.bin_present": "blob.bin" in joined,
            "核验✓_present": "核验✓" in joined,
            "count.txt": read("count.txt").strip(),
            "merged.txt_lines": merged.count("\n") + (1 if merged and not merged.endswith("\n") else 0),
            "stats.txt": read("stats.txt").strip(),
            "first.txt": read("first.txt").strip()[:40],
            "turns": len(turns),
            "turns_ok": sum(1 for t in turns if t.get("ok")),
            "contract_on_front": contract_front,
        },
    }
    # R453: 跑测后才发现/改动的观测项单列, 不混入预注册判据。
    verdict["checks_posthoc"] = {
        "menu_present": bool(re.search(r"①|1\.\s", joined)),
        "recall_stale_refs": sorted(set(re.findall(r"[A-Za-z0-9_\-]+\.[A-Za-z0-9]{1,8}", "\n".join(bad_hits)))),
    }
    out = os.environ.get("R462_OUT") or os.path.join(A, "eval", "rover", "r462", "verdict-r462.json")
    json.dump(verdict, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(verdict["checks"], ensure_ascii=False))
    print("PASS" if all(verdict["checks"].values()) else "FAIL", "->", out)


if __name__ == "__main__":
    main()
