#!/usr/bin/env python3
"""R409 探针3: 模板来源对账 —— GGUF 内嵌 jinja(经 llama-server /apply-template) vs 归档 r1_chat_template.jinja。
K2b 相关: 两来源若对同一 messages 渲染出不同字节 => 同一会话里「本地 llama.cpp 路径」与「归档/远端路径」
的可复用前缀不一致 => 缓存命中率被结构性削掉。
判据预注册:
  - 逐字节相同 => 归档模板可信, 漂移为潜在(未激活)
  - 不同 => 量化差异字节数 + token 级影响, 归档模板标记 stale
"""
import json
import subprocess
import sys
import urllib.request

sys.path.insert(0, "/tmp/tokvenv/lib/python3.11/site-packages")
from jinja2 import Environment  # noqa: E402

BASE = "http://127.0.0.1:8932"
ENV = Environment(trim_blocks=True, lstrip_blocks=False, autoescape=False)

ARCHIVED = open("/home/agentuser/AgentFramework/eval/rover/tokref/r1_chat_template.jinja",
                encoding="utf-8").read()
GGUF = open("/tmp/probe-r408/gguf_chat_template.jinja", encoding="utf-8").read()

SHAPES = {
    "U": [{"role": "user", "content": "What is 12*12? Answer with the number."}],
    "S+U": [{"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is 12*12? Answer with the number."}],
    "U/A/U": [{"role": "user", "content": "What is 12*12?"},
              {"role": "assistant", "content": "144"},
              {"role": "user", "content": "And 13*13?"}],
}


def served(messages: list) -> str:
    req = urllib.request.Request(BASE + "/apply-template",
                                data=json.dumps({"messages": messages}).encode(),
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())["prompt"]


def jinja_render(tpl: str, messages: list, add_gen: bool) -> str:
    return ENV.from_string(tpl).render(messages=messages, add_generation_prompt=add_gen,
                                       tools=None, bos_token="", eos_token="")


def ntokens(text: str) -> int:
    req = urllib.request.Request(BASE + "/tokenize",
                                data=json.dumps({"content": text, "add_special": True}).encode(),
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return len(json.loads(r.read().decode())["tokens"])


print(f"GGUF内嵌={len(GGUF.encode())} B  归档={len(ARCHIVED.encode())} B  差={len(ARCHIVED.encode())-len(GGUF.encode())} B\n")
all_same = True
for name, msgs in SHAPES.items():
    s = served(msgs)
    j = jinja_render(ARCHIVED, msgs, True)
    g = jinja_render(GGUF, msgs, True)
    same_sj = s == j
    same_sg = s == g
    all_same &= same_sj
    print(f"[{name}] served={len(s.encode())}B  archived_jinja={len(j.encode())}B  gguf_jinja={len(g.encode())}B")
    print(f"     served == archived ? {same_sj}      served == gguf_inline ? {same_sg}"
          f"      archived == gguf_inline ? {j == g}")
    print(f"     tokens: served={ntokens(s)} archived={ntokens(j)}")
    if not same_sj:
        n = min(len(s), len(j))
        k = next((i for i in range(n) if s[i] != j[i]), n)
        print(f"     首个差异 @char {k}: served={s[max(0,k-30):k+40]!r}")
        print(f"                            arch  ={j[max(0,k-30):k+40]!r}")
    print()

print(f"=== 裁决: 全部形状逐字节相同 ? {all_same} ===")
