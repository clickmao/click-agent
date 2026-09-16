#!/usr/bin/env python3
"""R489 候选④ 判据: R486 空正文差分夹具在 **ACTION_LOOP=on** 下的读数 (机取, 与 prereg_r486 的 H1 对齐)。

pre = /tmp/pub_r476/agenthost (R476 修复前), post = /tmp/pub_r479v2/agenthost (修复后);
prereg_r486 H1 声明 = "pre 比 post **多 1** 次桩请求 (浪费重试被修复消除)"。
输入: eval/rover/r489/stub-requests-<tag>.jsonl (桩侧真实请求条数) + tel/tel-<tag>.jsonl (宿主遥测)。
输出: eval/rover/r489/verdict-loop-r489.json; rc=0 与预注册一致 / 1 证伪 / 3 缺输入。
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TAGS = ["pre-empty", "post-empty", "pre-plain", "post-plain"]


def nreq(tag):
    p = os.path.join(HERE, f"stub-requests-{tag}.jsonl")
    if not os.path.exists(p):
        sys.exit("缺输入 (fail-closed): %s" % p)
    return sum(1 for l in io.open(p, encoding="utf-8-sig") if l.strip())


def tele(tag):
    p = os.path.join(HERE, "tel", f"tel-{tag}.jsonl")
    if not os.path.exists(p):
        return None
    rows = [json.loads(l) for l in io.open(p, encoding="utf-8-sig") if l.strip()]
    return {
        "rows": len(rows),
        "empty_body_events": sum(1 for r in rows if r.get("point") == "llm_call_empty_body"),
        "retry_skipped_true": sum(1 for r in rows if r.get("point") == "llm_call_empty_body"
                                  and str((r.get("kv") or {}).get("retry_skipped")) == "True"),
        "action_loop_events": sum(1 for r in rows if "action" in str(r.get("point", "")).lower()),
    }


out = {"round": "R489", "candidate": "④ R486 差分夹具打开 ACTION_LOOP 重跑",
       "prereg_source": "eval/rover/r486/prereg_r486.json (H1: pre 比 post 多 1 次桩请求)",
       "action_loop": "on", "stub_requests": {t: nreq(t) for t in TAGS},
       "telemetry": {t: tele(t) for t in TAGS}, "checks": []}
sr = out["stub_requests"]
out["checks"].append({
    "id": "H1-on", "desc": "空正文(带 tool_calls) 模式: pre 比 post 多 1 次桩请求 (prereg_r486 H1)",
    "ok": sr["pre-empty"] - sr["post-empty"] == 1,
    "detail": f"pre={sr['pre-empty']} post={sr['post-empty']} 差={sr['pre-empty']-sr['post-empty']}"})
out["checks"].append({
    "id": "NC-plain", "desc": "plain 模式两二进制应同值 (阴性对照; 差异说明夹具噪声)",
    "ok": sr["pre-plain"] == sr["post-plain"],
    "detail": f"pre={sr['pre-plain']} post={sr['post-plain']}"})
out["verdict"] = "与预注册一致" if all(c["ok"] for c in out["checks"]) else "预注册 H1 被证伪 (宣称收窄)"
io.open(os.path.join(HERE, "verdict-loop-r489.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1) + "\n")
print(json.dumps({"stub_requests": sr, "telemetry": out["telemetry"], "checks": out["checks"],
                  "verdict": out["verdict"]}, ensure_ascii=False, indent=1))
sys.exit(0 if all(c["ok"] for c in out["checks"]) else 1)
