#!/usr/bin/env python3
"""R409 预备实验: r1 的「模板化 vs 裸文本」同题 A/B。
判据预注册:
  - 同 gguf / 同 greedy(temp0) / 同 n_predict=24 / 同线程=1 / 同 KV=f32 / flash-attn off / 关全部采样过滤
  - 自变量只有一个: prompt 字节 (裸文本 vs 出厂模板包装)
  - 读法: 文本是否连贯 + 是否给出正确答案 144 + 生成 token 数
诚实边界: n=1 题 × 1 采样; 只作方向性证据, 不是能力分数。
"""
import json
import urllib.request

URL = "http://127.0.0.1:8931/completion"
BASE = {
    "n_predict": 24,
    "temperature": 0.0,
    "top_k": 1,
    "top_p": 1.0,
    "min_p": 0.0,
    "repeat_penalty": 1.0,
    "seed": 12345,
    "cache_prompt": False,
    "n_keep": 0,
}


def post(prompt: str) -> dict:
    body = dict(BASE, prompt=prompt)
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


arms = [
    ("A_裸文本(无模板)", open("/tmp/probe-r408/ab-template/prompt_raw.txt", encoding="utf-8").read()),
    ("B_出厂模板(96B)", open("/tmp/probe-r408/prompt.txt", encoding="utf-8").read()),
]

for name, prompt in arms:
    d = post(prompt)
    txt = d.get("content", "")
    tm = d.get("timings", {})
    print(f"### {name}")
    print(f"  prompt_bytes = {len(prompt.encode('utf-8'))}")
    print(f"  prompt_tokens= {d.get('tokens_evaluated')}")
    print(f"  pred_tokens  = {d.get('tokens_predicted')}")
    print(f"  has_144      = {'144' in txt}")
    print(f"  tps          = {tm.get('predicted_per_second')}")
    print(f"  stop_type    = {d.get('stop_type')}")
    print(f"  text         = {txt!r}")
    print()
