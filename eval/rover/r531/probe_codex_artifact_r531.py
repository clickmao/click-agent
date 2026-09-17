#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D (R531): 外部真值侧「清理命令重试/审批拒绝」伪影的**机检探针** —— 只读既有落盘 dump, 不新跑任何臂。

被检验的假设 (R530 遗留候选): 「codex 臂出现 `rm -f`/审批拒绝的重试风暴 ⇒ 该臂调用数被伪影抬高」。
判据 (先声明后跑):
  · denial 关键词计数 (denied/reject/not permitted/approval/Operation not permitted/sandbox) 全 0 ⇒ 假设的
    「审批拒绝」机制**证据不存在**;
  · 同一规范化命令 (去空白) 在同一 (窗,臂,题) 内重复 >= 5 次 ⇒ LOOP_SUSPECT (重试风暴);
    否则 NO_LOOP_EVIDENCE。
产物: eval/rover/r531/evidence/codex-artifact-probe-r531.json
"""
import argparse, collections, glob, io, json, os, re, sys

REPO = "/home/agentuser/AgentFramework"
# 判据关键词 = 无歧义的拒绝/审批措辞 (gating);
# 另有 KW_GENERIC 仅记录不判 (裸 "reject"/"sandbox"/"approval" 会命中题面散文 ⇒ 假阳性)。
KW = ["denied", "not permitted", "operation not permitted", "permission denied",
      "approval required", "approval_policy"]
KW_GENERIC = ["reject", "sandbox", "approval", "allowlist", "blocked"]
OUT = os.path.join(REPO, "eval/rover/r531/evidence/codex-artifact-probe-r531.json")


def harvest(dump_paths):
    cmds = collections.Counter()
    kwhits = collections.Counter()
    kwhits_generic = collections.Counter()
    calls = 0
    for f in dump_paths:
        txt = io.open(f, encoding="utf-8", errors="replace").read()
        try:
            doc = json.loads(txt)
        except Exception:  # noqa: BLE001
            continue
        # 关键词只在**模型输出侧**扫 (request.instructions = 题面原文, 含 "rejects" 等词 ⇒ 会假阳性)
        scan = json.dumps(doc.get("response") or {}, ensure_ascii=False).lower()
        for k in KW:
            kwhits[k] += scan.count(k.lower())
        for k in KW_GENERIC:
            kwhits_generic[k] += scan.count(k.lower())
        msgs = [doc]
        for m in msgs:
            for tc in ((doc.get("response") or {}).get("tool_calls") or []):
                calls += 1
                fn = {"arguments": tc.get("args")}
                args = fn.get("arguments")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:  # noqa: BLE001
                        args = {"raw": args}
                if isinstance(args, dict):
                    c = args.get("command") or args.get("cmd") or args.get("script")
                    if isinstance(c, list):
                        c = " ".join(str(x) for x in c)
                    if c:
                        cmds[re.sub(r"\s+", " ", str(c)).strip()] += 1
    return calls, cmds, kwhits, kwhits_generic


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-glob", action="append",
                    default=["/home/agentuser/AgentFramework/eval/rover/r529/run-*-w*/adapter"])
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    rows = []
    for g in a.run_glob:
        for d in sorted(glob.glob(g)):
            for arm in ("codex",):
                dumps = sorted(glob.glob(os.path.join(d, "side-%s-*.json" % arm)))
                if not dumps:
                    continue
                calls, cmds, kwhits, kwhits_generic = harvest(dumps)
                mx = max(cmds.values()) if cmds else 0
                top = cmds.most_common(3)
                rows.append({"adapter_dir": os.path.relpath(d, REPO), "arm": arm, "dumps": len(dumps),
                             "tool_calls": calls, "distinct_cmds": len(cmds), "max_cmd_repeat": mx,
                             "top_cmds": [{"cmd": c[:120], "n": n} for c, n in top],
                             "denial_keyword_hits": dict(kwhits),
                             "generic_word_hits": dict(kwhits_generic),
                             "verdict": "LOOP_SUSPECT" if mx >= 5 else "NO_LOOP_EVIDENCE"})
    res = {"round": "R531", "probe": "codex_cleanup_retry_artifact", "threshold_repeat": 5,
           "denial_keywords": KW, "rows": rows,
           "hypothesis": "codex 臂调用数被 rm -f/审批拒绝重试伪影抬高",
           "falsified": all(r["max_cmd_repeat"] < 5 and sum(r["denial_keyword_hits"].values()) == 0
                            for r in rows) if rows else None,
           "verdict": ("FALSIFIED(证据不存在)" if rows and all(
               r["max_cmd_repeat"] < 5 and sum(r["denial_keyword_hits"].values()) == 0 for r in rows)
               else ("LOOP_SUSPECT" if any(r["verdict"] == "LOOP_SUSPECT" for r in rows) else "NO_DATA"))}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    for r in rows:
        print("%-58s dumps=%4d calls=%4d distinct=%4d maxrep=%d denial=%d %s" %
              (r["adapter_dir"], r["dumps"], r["tool_calls"], r["distinct_cmds"], r["max_cmd_repeat"],
               sum(r["denial_keyword_hits"].values()), r["verdict"]))
    print("VERDICT=%s" % res["verdict"])
    return 0 if res["verdict"] != "NO_DATA" else 3


if __name__ == "__main__":
    sys.exit(main())
