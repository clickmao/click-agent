#!/usr/bin/env python3
"""R409 预备实验 (长窗版): 400 token 内是否落到正确答案 144。
与 ab_template.py 同口径, 只把 n_predict 24→400。
"""
import json
import urllib.request

URL = "http://127.0.0.1:8931/completion"
BASE = {
    "n_predict": 400,
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
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.loads(r.read().decode("utf-8"))


arms = [
    ("A_裸文本(无模板)", open("/tmp/probe-r408/ab-template/prompt_raw.txt", encoding="utf-8").read()),
    ("B_出厂模板(96B)", open("/tmp/probe-r408/prompt.txt", encoding="utf-8").read()),
]
out = {}
for name, prompt in arms:
    d = post(prompt)
    txt = d.get("content", "")
    tm = d.get("timings", {})
    out[name] = {"text": txt, "tps": tm.get("predicted_per_second"),
                 "pred": d.get("tokens_predicted"), "stop": d.get("stop_type")}
    head = txt.replace("\n", "\\n")[:260]
    print(f"### {name}")
    print(f"  pred_tokens={d.get('tokens_predicted')} stop={d.get('stop_type')} "
          f"tps={tm.get('predicted_per_second')}")
    print(f"  has_144={'144' in txt}  has_end_token={d.get('stop_type') == 'eos'}")
    print(f"  head={head!r}")
    print()
with open("/tmp/probe-r408/ab-template/long-run.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("saved /tmp/probe-r408/ab-template/long-run.json")
