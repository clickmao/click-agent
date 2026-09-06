#!/usr/bin/env python3
"""多 LLM 交叉校验 — 同一事实问题问 glm-5.3-flash + deepseek-v4-flash, 归一化后比对一致性。
用途: 为搜溯数据校验建立双模型管线; 验证多端点真实调度。
用法: python3 eval/cross_validate.py "问题" [n_norm]
输出: JSON {q, a_glm, a_ds, agree, norm_glm, norm_ds}
"""
import json, os, re, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_env():
    env = {}
    p = os.path.join(ROOT, ".env.local")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def chat(url, key, model, q, max_tokens=800):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": q}],
                       "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    m = d["choices"][0]["message"]
    return (m.get("content") or "").strip() or (m.get("reasoning_content") or "").strip()

def norm(t):
    """归一化: 数字统一 (万→0000), 去空白标点, 小写"""
    t = t.strip()
    t = re.sub(r"(\d+(?:\.\d+)?)\s*万", lambda m: str(int(float(m.group(1)) * 10000)), t)
    t = re.sub(r"[\s,，。;；:：\"'()（）\[\]【】]", "", t)
    t = t.replace("\u2082", "2").replace("\u2083", "3")  # 下标数字统一
    t = re.sub(r"[*.]", "", t)
    return t.lower()

def extract_numbers(t):
    return sorted(set(re.findall(r"\d+(?:\.\d+)?", t)))

def main():
    q = sys.argv[1]
    env = load_env()
    a_glm = chat("https://open.bigmodel.cn/api/coding/paas/v4/chat/completions",
                 env["AGENTFRAMEWORK_KEYS_BIGMODEL"], "glm-5.3-flash", q)
    a_ds = chat("https://api.deepseek.com/v1/chat/completions",
                env["AGENTFRAMEWORK_KEYS_DEEPSEEK"], "deepseek-v4-flash", q)
    ng, nd = norm(a_glm), norm(a_ds)
    numg, numd = extract_numbers(ng), extract_numbers(nd)
    if numg and numd:
        agree = numg == numd
    else:
        agree = ng == nd or ng[:40] == nd[:40]
    out = {"q": q, "a_glm": a_glm, "a_ds": a_ds,
           "norm_glm": ng[:120], "norm_ds": nd[:120],
           "numbers_glm": extract_numbers(a_glm), "numbers_ds": extract_numbers(a_ds),
           "agree": agree}
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
