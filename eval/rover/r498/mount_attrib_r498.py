#!/usr/bin/env python3
"""R498 候选⑤: 挂载成本的**定长腿 vs 行为改变**归因 (纯离线, 读 R497 同窗数据)。

问题 (R497 遗留): T2→T1 只动「挂载轴」(台账尾部挂载 on), 读数 calls 13→12 (−7.69%),
total tokens 62536→71511 (**+14.35%**)。这 +8975 tokens 里,
  (a) **定长腿** = 每次远端调用尾部多出的那条台账 message 自身占的 prompt 字符/token;
  (b) **行为改变腿** = 模型见到台账后的行为差 (调用数变少、每调用内容变长、缓存命中结构变化)。
各占多少?

口径 (显式声明, 可复算):
  * 器具口径 est: 中继 relay_real_r475.py `est_tokens_from_messages` = Σ len(content)//2 (字符数//2)。
    复算对象 = calls-*.jsonl 里的 `prompt_tokens_est` 字段 (逐调用落盘) ⇒ 逐位可比。
  * 真值口径 real: usage-*.jsonl 的 `usage.prompt_tokens` / `completion_tokens` / `total_tokens` (供应商回真值)。
  * 定长腿 (est 口径, 精确): 对 T1 每次调用的 messages, **摘掉尾部台账 message** 后重算 est,
    差值 = 该调用台账块的 est 占用 (不依赖模型行为, 纯字符事实)。
  * 定长腿 (real 口径, 上界估计): 台账块字符数 × (real_est_scale), 其中 scale = 同调用
    real_prompt_tokens / est_prompt_tokens (逐调用实测比, 不拍常数)。
  * 行为腿 = real 总差 − 定长腿 (real 口径)。

fail-closed: 缺文件/行数不符/恒等式不成立 ⇒ 非零退出, 不产出结论。
"""
import json
import os
import sys

DIR = "/home/agentuser/AgentFramework/eval/rover/r497"
OUT = "/home/agentuser/AgentFramework/eval/rover/r498"
ARMS = ["T2", "T1"]          # T2 = 挂载 off; T1 = T2 + 挂载 on (单变量)


def load_jsonl(path):
    if not os.path.exists(path):
        sys.exit("[致命] 缺文件: " + path)
    rows = []
    with open(path, encoding="utf-8-sig") as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                rows.append(json.loads(ln))
    return rows


def est(msgs):
    """与 relay_real_r475.py est_tokens_from_messages 逐位同式 (chars//2)。"""
    chars = 0
    for m in msgs:
        ct = m.get("content")
        if isinstance(ct, str):
            chars += len(ct)
        elif isinstance(ct, list):
            for part in ct:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    chars += len(part["text"])
    return max(1, chars // 2)


def is_mount_msg(m):
    """台账挂载 message 的**结构指纹** (R497 口径: 尾部 system + 头部标记)。"""
    return m.get("role") == "system" and str(m.get("content", "")).lstrip().startswith("[本地决策台账")


def main():
    calls = {a: load_jsonl(os.path.join(DIR, "calls-%s.jsonl" % a)) for a in ARMS}
    usage = {a: load_jsonl(os.path.join(DIR, "usage-%s.jsonl" % a)) for a in ARMS}

    rep = {"round": "R498", "candidate": "⑤挂载成本定长腿归因", "source_round": "R497",
           "source_arms": ARMS, "data": {}, "checks": {}}

    for a in ARMS:
        c, u = calls[a], usage[a]
        # 恒等式: calls 与 usage 逐调用一一对应 (同 seq 集合)
        cs = [r["seq"] for r in c]
        us = [r["seq"] for r in u]
        if cs != us:
            sys.exit("[致命] calls/usage seq 不齐 (%s): %s vs %s" % (a, cs, us))
        n = len(c)
        real_prompt = sum(r["usage"]["prompt_tokens"] for r in u)
        real_comp = sum(r["usage"]["completion_tokens"] for r in u)
        real_total = sum(r["usage"]["total_tokens"] for r in u)
        # 供应商恒等式: total == prompt + completion (逐调用; 违者拒出结论)
        bad = [r["seq"] for r in u
               if r["usage"]["total_tokens"] != r["usage"]["prompt_tokens"] + r["usage"]["completion_tokens"]]
        if bad:
            sys.exit("[致命] usage 恒等式违规 (%s) seq=%s" % (a, bad))
        est_total = sum(r["prompt_tokens_est"] for r in c)
        rep["data"][a] = {
            "calls": n,
            "real_prompt_tokens": real_prompt,
            "real_completion_tokens": real_comp,
            "real_total_tokens": real_total,
            "est_prompt_tokens_sum": est_total,
            "real_over_est_prompt": round(real_prompt / est_total, 6),
            "cache_hit_tokens": sum(r.get("cache_hit_tokens", 0) for r in u),
            "cache_miss_tokens": sum(r.get("cache_miss_tokens", 0) for r in u),
        }

    # ── 定长腿 (est 口径, 精确: 摘 message 重算) ───────────────────────────────
    per_call = []
    mount_est_sum = 0
    mount_chars_sum = 0
    n_with = 0
    n_without = 0
    for r in calls["T1"]:
        msgs = r["messages"]
        mounts = [m for m in msgs if is_mount_msg(m)]
        if len(mounts) > 1:
            sys.exit("[致命] T1 seq=%s 台账 message 数=%d (期望 ≤1)" % (r["seq"], len(mounts)))
        e_full = est(msgs)
        if e_full != r["prompt_tokens_est"]:
            sys.exit("[致命] T1 seq=%s est 复算 %d != 落盘 %d ⇒ 器具口径漂移" % (
                r["seq"], e_full, r["prompt_tokens_est"]))
        if not mounts:
            n_without += 1
            per_call.append({"seq": r["seq"], "n_messages": r["n_messages"],
                             "est": e_full, "mount": False,
                             "note": "无台账挂载 (非主任务面调用, 结构上不挂)"})
            continue
        n_with += 1
        stripped = [m for m in msgs if not is_mount_msg(m)]
        e_strip = est(stripped)
        chars = len(mounts[0]["content"])
        mount_est_sum += e_full - e_strip
        mount_chars_sum += chars
        per_call.append({"seq": r["seq"], "n_messages": r["n_messages"],
                         "est_full_recompute": e_full, "est_without_mount": e_strip,
                         "mount_delta_est": e_full - e_strip, "mount_chars": chars,
                         "mount": True})
    if mount_est_sum <= 0 or n_with == 0:
        sys.exit("[致命] 定长腿读数为 0/空 ⇒ 挂载轴未生效, 拒出归因结论")

    rep["checks"]["est_recompute_parity"] = "PASS (逐调用 est 复算 == 落盘值, n=%d)" % len(per_call)
    rep["mount_block"] = {
        "n_calls_total": len(per_call),
        "n_calls_with_mount": n_with,
        "n_calls_without_mount": n_without,
        "chars_total": mount_chars_sum, "chars_per_call": mount_chars_sum / n_with,
        "est_delta_total": mount_est_sum, "est_delta_per_call": mount_est_sum / n_with,
        "per_call": per_call,
    }

    # ── 归因 (est 口径) ───────────────────────────────────────────────────────
    est_T2 = rep["data"]["T2"]["est_prompt_tokens_sum"]
    est_T1 = rep["data"]["T1"]["est_prompt_tokens_sum"]
    est_delta = est_T1 - est_T2
    est_behavior = est_delta - mount_est_sum

    # ── 归因 (real 口径, 定长腿按逐调用实测比例折算; 不拍常数) ──────────────────
    scale = rep["data"]["T1"]["real_over_est_prompt"]
    mount_real_upper = int(round(mount_est_sum * scale))
    real_delta = rep["data"]["T1"]["real_total_tokens"] - rep["data"]["T2"]["real_total_tokens"]
    call_delta = rep["data"]["T1"]["calls"] - rep["data"]["T2"]["calls"]
    # 调用数变化自身贡献的**行为腿** (T2 平均每次调用; 只作尺度参照, 不是因果断言)
    t2_avg_per_call = rep["data"]["T2"]["real_total_tokens"] / rep["data"]["T2"]["calls"]

    rep["attribution"] = {
        "est_caliber": {
            "est_T2_sum": est_T2, "est_T1_sum": est_T1, "est_delta": est_delta,
            "fixed_leg_est": mount_est_sum, "behavior_leg_est": est_behavior,
            "fixed_share": round(mount_est_sum / est_delta, 6) if est_delta else None,
        },
        "real_caliber": {
            "real_T2_total": rep["data"]["T2"]["real_total_tokens"],
            "real_T1_total": rep["data"]["T1"]["real_total_tokens"],
            "real_delta": real_delta,
            "prompt_vs_est_scale_T1": scale,
            "fixed_leg_real_upper": mount_real_upper,
            "behavior_leg_real_lower": real_delta - mount_real_upper,
            "fixed_share_upper": round(mount_real_upper / real_delta, 6) if real_delta else None,
            "call_count_delta": call_delta,
            "T2_real_tokens_per_call": round(t2_avg_per_call, 2),
            "note": "fixed_leg_real_upper 用**逐调用实测比例**折算 (非拍常数); behavior 腿按定义取残差",
        },
        "prompt_completion_split": {
            "T2_prompt": rep["data"]["T2"]["real_prompt_tokens"],
            "T2_completion": rep["data"]["T2"]["real_completion_tokens"],
            "T1_prompt": rep["data"]["T1"]["real_prompt_tokens"],
            "T1_completion": rep["data"]["T1"]["real_completion_tokens"],
            "prompt_delta": rep["data"]["T1"]["real_prompt_tokens"] - rep["data"]["T2"]["real_prompt_tokens"],
            "completion_delta": rep["data"]["T1"]["real_completion_tokens"] - rep["data"]["T2"]["real_completion_tokens"],
        },
        "cache_split": {
            "T2_hit": rep["data"]["T2"]["cache_hit_tokens"], "T2_miss": rep["data"]["T2"]["cache_miss_tokens"],
            "T1_hit": rep["data"]["T1"]["cache_hit_tokens"], "T1_miss": rep["data"]["T1"]["cache_miss_tokens"],
        },
    }

    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "mount-attrib-r498.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: rep[k] for k in ("data", "checks", "attribution")}, ensure_ascii=False, indent=1))
    print("[mount-block] chars/call=%.1f est/call=%.2f" % (
        rep["mount_block"]["chars_per_call"], rep["mount_block"]["est_delta_per_call"]))
    print("[out]", p)


if __name__ == "__main__":
    main()
