#!/usr/bin/env python3
"""R409 探针2: BOS 归属 —— 「字面 96B 串」与「/apply-template 渲染 + tokenizer 自动 BOS」的 token 流是否相同。
这一步决定闸门契约, 不能靠推断。
判据预注册:
  - 若 ids(96B字面) 与 ids(67B渲染, add_special=true) 相同 => 两条路径等价, 闸门可任选
  - 若前者多一个 BOS => 字面串一直是「双 BOS」, 权威串需修正 (如实记录并回改)
"""
import hashlib
import json
import urllib.request

BASE = "http://127.0.0.1:8932"


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


auth = open("/tmp/probe-r408/prompt.txt", encoding="utf-8").read()          # 96 B 含 BOS 字面
rendered = post("/apply-template", {"messages": [
    {"role": "user", "content": "What is 12*12? Answer with the number."}]})["prompt"]  # 67 B 无 BOS
raw = open("/tmp/probe-r408/ab-template/prompt_raw.txt", encoding="utf-8").read()        # 38 B 裸文本

BOS_ID, EOS_ID = 151646, 151643


def ids(text: str, add_special: bool) -> list:
    return post("/tokenize", {"content": text, "add_special": add_special})["tokens"]


cases = [
    ("96B 字面(含BOS文本)", auth, True),
    ("96B 字面", auth, False),
    ("67B 渲染", rendered, True),
    ("67B 渲染", rendered, False),
    ("38B 裸文本", raw, True),
]

print(f"{'case':<22} {'add_spec':<9} {'n':<4} 前4个id                          BOS个数  含<｜User｜>")
for name, text, sp in cases:
    t = ids(text, sp)
    print(f"{name:<22} {str(sp):<9} {len(t):<4} {str(t[:4]):<32} {t.count(BOS_ID):<8} {151648 in t}")

print()
a_true = ids(auth, True)
r_true = ids(rendered, True)
r_nosp = ids(rendered, False)
print(f"裁决: ids(96B字面,add_special=T) == ids(67B渲染,add_special=T) ? {a_true == r_true}")
print(f"      ids(96B字面,add_special=T) == [BOS] + ids(67B渲染,add_special=F) ? {a_true == [BOS_ID] + r_nosp}")
print(f"      96B字面 BOS个数={a_true.count(BOS_ID)}  67B渲染前缀={r_true[:2]}")
print(f"  sha256(96B)={hashlib.sha256(auth.encode()).hexdigest()[:16]}  "
      f"sha256(67B)={hashlib.sha256(rendered.encode()).hexdigest()[:16]}")
