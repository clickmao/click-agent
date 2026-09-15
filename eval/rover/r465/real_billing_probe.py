#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R465 ④ 分母口径升级: 用真实供应商 usage 校准桩侧 token 估算器。

- 输入: 桩侧 calls-$ARM.jsonl 里**逐字捕获**的 messages (实发文本)。
- 动作: 以 max_tokens=1 回放给真实端点, 只取 usage.prompt_tokens / completion_tokens / cache 命中。
- 输出: per-call (est vs real) + 校准因子 mean(est/real) + 用真值重算的臂降幅。
凭据: 只从环境或 .env.local 读, **不打印值**, 不落盘。
用法: python3 real_billing_probe.py <n_arele> <n_r>
"""
import io, json, os, statistics, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
URL = "https://api.deepseek.com/v1/chat/completions"
MODELS = ["deepseek-flash", "deepseek-chat"]

def key():
    k = os.environ.get("AGENTFRAMEWORK_KEYS_DEEPSEEK", "").strip()
    if k and not k.startswith("dummy"):
        return k
    p = os.path.join(ROOT, ".env.local")
    if os.path.exists(p):
        for line in io.open(p, encoding="utf-8"):
            if line.startswith("AGENTFRAMEWORK_KEYS_DEEPSEEK="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

def rows(p):
    return [json.loads(l) for l in io.open(p, encoding="utf-8") if l.strip()]

def call(k, msgs):
    last = None
    for m in MODELS:
        body = json.dumps({"model": m, "messages": msgs, "max_tokens": 1, "stream": False}).encode("utf-8")
        req = urllib.request.Request(URL, data=body, headers={
            "Content-Type": "application/json", "Authorization": "Bearer " + k})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                o = json.loads(r.read().decode("utf-8"))
            return m, (o.get("usage") or {}), (o.get("choices") or [{}])[0].get("finish_reason")
        except urllib.error.HTTPError as e:
            last = "HTTP %s %s" % (e.code, e.read().decode("utf-8", "replace")[:200])
            if e.code in (400, 404):
                continue
            return None, {"error": last}, None
        except Exception as e:
            return None, {"error": "%s: %s" % (type(e).__name__, e)}, None
    return None, {"error": last}, None

def main():
    na, nr = int(sys.argv[1]), int(sys.argv[2])
    k = key()
    if not k:
        print(json.dumps({"VOID": "无可用真实密钥 (env/.env.local 均为空或 dummy)"}, ensure_ascii=False))
        return
    d = os.path.join(ROOT, "eval", "rover", "r465")
    out = {"endpoint": URL, "samples": []}
    for arm, n in (("Arole", na), ("R", nr)):
        rs = rows(os.path.join(d, "calls-%s.jsonl" % arm))
        if not rs:
            continue
        idx = sorted({0, len(rs) // 2, len(rs) - 1})[:n]
        for i in idx:
            rec = rs[i]
            model, usage, fr = call(k, rec["messages"])
            out["samples"].append({
                "arm": arm, "call": i + 1, "model": model,
                "est": rec.get("prompt_tokens_est"), "real_prompt": usage.get("prompt_tokens"),
                "real_completion": usage.get("completion_tokens"),
                "cache_hit": usage.get("prompt_cache_hit_tokens"),
                "finish": fr, "error": usage.get("error"),
            })
            print("[%s#%d] est=%s real_prompt=%s cache_hit=%s err=%s" % (
                arm, i + 1, rec.get("prompt_tokens_est"), usage.get("prompt_tokens"),
                usage.get("prompt_cache_hit_tokens"), usage.get("error")))
    ok = [s for s in out["samples"] if s.get("real_prompt") and s.get("est")]
    if ok:
        ratios = [s["est"] / s["real_prompt"] for s in ok]
        out["ratio_est_over_real"] = round(statistics.mean(ratios), 4)
        out["ratio_min"] = round(min(ratios), 4)
        out["ratio_max"] = round(max(ratios), 4)
        out["n"] = len(ok)
        out["real_total_tokens_sampled"] = sum(s["real_prompt"] for s in ok)
    p = os.path.join(d, "real_billing_probe.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({x: out[x] for x in out if x not in ("samples",)}, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
