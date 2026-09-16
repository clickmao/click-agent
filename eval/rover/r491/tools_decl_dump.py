#!/usr/bin/env python3
"""从产品源码**机取**工具声明面正文（中继不落 tools 正文 ⇒ 用源码常量 + 同名合成规则复现）。

规则源: src/agent.modelqueue/ActionToolSpec.cs:48-71 `Compose(flatten)`
  · chat (flatten=False): {"type":"function","function":{"name":…,"description":…,"parameters":<json>}}
  · responses(flatten=True ): {"type":"function","name":…,"description":…,"parameters":<json>}
分隔符: 条目间 ",\n"; 外层 '[' ']'。常量三元组从 ActionToolSpec.cs:32-39 机取。
"""
import io, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC = os.path.join(ROOT, "src", "agent.modelqueue", "ActionToolSpec.cs")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paid-plaintext")
TRI = re.compile(r'new\(ActionToolDecl\.(\w+),\s*"((?:[^"\\]|\\.)*)",\s*"((?:[^"\\]|\\.)*)"\)')


def unesc(s):
    return json.loads('"' + s + '"')


def compose(items, flatten):
    parts = []
    for name, desc, params in items:
        if flatten:
            parts.append('{"type":"function","name":"%s","description":"%s","parameters":%s}' % (name, desc, params))
        else:
            parts.append('{"type":"function","function":{"name":"%s","description":"%s","parameters":%s}}' % (name, desc, params))
    return "[" + ",\n".join(parts) + "]"


def main():
    src = io.open(SRC, encoding="utf-8").read()
    items = [(n, unesc(d), unesc(p)) for n, d, p in TRI.findall(src)]
    if len(items) != 4:
        raise SystemExit("FAIL: 期望 4 个工具常量, 实得 %d" % len(items))
    chat, resp = compose(items, False), compose(items, True)
    os.makedirs(OUT, exist_ok=True)
    io.open(os.path.join(OUT, "tools-declaration-removed.chat.json"), "w", encoding="utf-8").write(chat)
    io.open(os.path.join(OUT, "tools-declaration-removed.responses.json"), "w", encoding="utf-8").write(resp)
    lines = ["# B 臂每次请求**附带**、T 臂**去掉**的工具声明正文（从源码常量机取）", "",
             "| 名称 | 描述 | parameters(JSON) |", "|---|---|---|"]
    for n, d, p in items:
        lines.append(f"| `{n}` | {d} | `{p}` |")
    lines += ["", f"- Chat 线格式字符数 = **{len(chat)}**；Responses 平铺版 = **{len(resp)}**",
              "", "```json", chat, "```"]
    io.open(os.path.join(OUT, "tools-declaration-removed.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("tools=%d chat_chars=%d resp_chars=%d" % (len(items), len(chat), len(resp)))
    print("chat/4 = %.0f chars per tool" % (len(chat) / 4))


if __name__ == "__main__":
    main()
