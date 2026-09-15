#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R469 器具: 主调用 prompt 的**前缀稳定性**测量 (离线, 无 llama-server)。

口径:
  seq_k   = 该臂第 k 次远端主调用的 messages 数组 (桩侧落盘 = 外部真值)
  flat_k  = 按 messages 顺序拼接的 (role, content) 文本
  prefix_k= flat_k 与 flat_{k-1} 的**逐字节公共前缀长度**
  new_k   = len(flat_k) - prefix_k  (新增/变化部分字符数)
  tok_est = prompt_tokens_est (桩侧估算; 真实计费另有 k=1.221 与 cache 命中, 见 R465/R467)
判据:
  P1 前缀占比 = prefix_k / len(flat_{k-1})   (可缓存比例)
  P2 新增 ≤ 93.5 tok 等价字符 ≤ 93.5*CPS_中文字符/tok  (97% 红线)
  P3 首差异**位置** = 尾部追加 (prefix_k == len(flat_{k-1}) 且只追加) ∧ 前缀内无动态字段
用法: python3 prefix_stability.py [arm ...]   (默认扫描 eval/rover/r467/calls-*.jsonl)
"""
import io
import json
import glob
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
R467 = os.path.join(HERE, "..", "r467")


def flat(messages):
    parts = []
    for m in messages or []:
        role = m.get("role") or m.get("Role") or "?"
        c = m.get("content") or m.get("Content") or ""
        parts.append("%s\u0001%s\u0002" % (role, c))
    return "".join(parts)


def common_prefix_len(a, b):
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def load(path):
    return [json.loads(l) for l in io.open(path, encoding="utf-8") if l.strip()]


def analyze(path):
    rows = load(path)
    fl = [flat(r.get("messages")) for r in rows]
    tok = [r.get("prompt_tokens_est") for r in rows]
    out = {"file": os.path.basename(path), "calls": len(rows), "tok": tok, "rows": []}
    for k in range(1, len(fl)):
        p = common_prefix_len(fl[k - 1], fl[k])
        prev = len(fl[k - 1])
        new_chars = len(fl[k]) - p
        out["rows"].append({
            "call": k + 1,
            "prev_chars": prev,
            "chars": len(fl[k]),
            "prefix_chars": p,
            "prefix_share": round(p / prev, 6) if prev else None,
            "new_chars": new_chars,
            "tail_only": p == prev,
            "new_tok_est": round(new_chars / max(len(fl[k]), 1) * (tok[k] or 0), 1),
        })
    return out


def neg_control():
    """负控: 同一历史, 只在 system 首行注入动态字段 (时间戳) ⇒ 前缀必须崩塌;
    正控: 纯尾部追加 ⇒ 前缀占比必须 = 1.0。"""
    hist = [{"role": "system", "content": "S" * 400}, {"role": "user", "content": "u1" * 50}]
    pos = hist + [{"role": "assistant", "content": "a1"}, {"role": "user", "content": "u2"}]
    nc1 = [{"role": "system", "content": "S" * 400 + "\u0001ts=1712"},
           {"role": "user", "content": "u1" * 50}] + [{"role": "assistant", "content": "a1"}, {"role": "user", "content": "u2"}]
    fh, fp, fn = flat(hist), flat(pos), flat(nc1)
    p_pos, p_nc = common_prefix_len(fh, fp), common_prefix_len(fh, fn)
    res = {
        "positive_control_tail_append_share": round(p_pos / len(fh), 6),
        "positive_control_tail_only": p_pos == len(fh),
        "negative_control_dynamic_system_prefix_chars": p_nc,
        "negative_control_note": "\u52a8\u6001\u5b57\u6bb5\u843d\u5728 system \u9996\u6bb5 \u21d2 \u5206\u6b67\u4f4d\u7f6e\u9760\u524d \u21d2 \u547d\u4e2d\u4e0a\u9650\u5d29\u5854 (\u4ec5\u9760\u540e\u5c3e\u53ef\u7f13\u5b58)",
        "negative_control_share": round(p_nc / len(fh), 6),
        "verdict": "PASS" if (p_pos == len(fh) and p_nc < 0.9 * p_pos) else "FAIL",
    }
    return res


def main():
    arms = sys.argv[1:] or [os.path.basename(p) for p in sorted(glob.glob(os.path.join(R467, "calls-*.jsonl")))]
    res = [{"neg_control": neg_control()}] if "--neg-control" in sys.argv else []
    for a in arms:
        if a == "--neg-control":
            continue
        p = a if os.path.isabs(a) or os.path.exists(a) else os.path.join(R467, a)
        if not os.path.exists(p):
            res.append({"file": a, "missing": True})
            continue
        res.append(analyze(p))
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
