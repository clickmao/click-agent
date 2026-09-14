#!/usr/bin/env python3
"""R409 可行性探针: /apply-template 渲染的字节是否与 R407 权威 96B 串逐字节相同。
判据预注册:
  - 若 sha256(prompt_from_apply_template) == sha256(权威 prompt.txt)  => 闸门可用「结构性阻断」方案
  - 若不等 => 只能退化为「启发式骨架校验」, 必须如实记录
另取 /props 的 chat_template 长度, 证明模板来源确实是 GGUF 元数据。
"""
import hashlib
import json
import urllib.request

BASE = "http://127.0.0.1:8932"
AUTH = "/tmp/probe-r408/prompt.txt"


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


auth_bytes = open(AUTH, "rb").read()
auth_sha = hashlib.sha256(auth_bytes).hexdigest()
print(f"权威串 : {len(auth_bytes)} B  sha256={auth_sha[:24]}")
print(f"        {auth_bytes.decode('utf-8')!r}")

msgs = [{"role": "user", "content": "What is 12*12? Answer with the number."}]
for extra in ({}, {"add_assistant": True}, {"add_generation_prompt": True}):
    try:
        d = post("/apply-template", dict(messages=msgs, **extra))
    except Exception as e:  # noqa: BLE001
        print(f"extra={extra} -> 失败: {e}")
        continue
    p = d.get("prompt", "")
    pb = p.encode("utf-8")
    print(f"extra={extra} -> {len(pb)} B  sha256={hashlib.sha256(pb).hexdigest()[:24]}  "
          f"逐字节相同={pb == auth_bytes}")
    print(f"        {p!r}")

props = get("/props")
ct = props.get("chat_template") or props.get("default_generation_settings", {}).get("chat_template") or ""
print(f"/props chat_template = {len(ct)} B  (来源=GGUF 元数据)")
