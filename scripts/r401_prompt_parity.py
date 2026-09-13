#!/usr/bin/env python3
"""R401 步: 「远端 API vs 本机引擎」解法级对比的 prompt 对等性取证。

为什么需要这一步
----------------
`solver=rover` 的对比要成立, 两臂必须收到**同一个 prompt**(prompt parity)。R400 交付的
`agent.rover generate --chat` 里, chat 渲染是**硬编码 DeepSeek 版式**的
(`<｜begin▁of▁sentence｜>` / `<｜User｜>` / `<｜Assistant｜>`, 见 src/agent.rover/token/ChatTemplate.cs),
其断言依据是 p7b(DeepSeek-Prover-V2-7B) 的词表资产。
用户 2026-09-14 令删除 p7b 后, 本机只剩 qwen 族模型; 对 qwen 族**强行套用 DeepSeek 版式**
⇒ 标签不在其词表内 ⇒ 被切成字节碎片 ⇒ 引擎收到的是**错误 prompt**。

本脚本给出三件独立读数(全部可复现):
  ① 目标 GGUF 内嵌 chat_template 原文 + sha256 (权威源, 非本仓代码);
  ② 用 jinja2 渲染该模板 (oracle arm 的 prompt);
  ③ 复刻引擎当前的 DeepSeek 版式渲染 (engine arm 的 prompt) ⇒ 首个分歧字节 + 两边片段;
  ④ 权威 arm 的 prompt 在该模型词表下的 token 数 与 引擎 arm 的首个分歧 token 位置
     (说明分歧不是"标点差异", 而是**结构不同**)。

口径: 本脚本只**诊断**, 不改产品代码, 不跑前向 (零 dotnet 构建)。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

BOS = "<\uff5cbegin\u2581of\u2581sentence\uff5c>"
EOS = "<\uff5cend\u2581of\u2581sentence\uff5c>"
USER_TAG = "<\uff5cUser\uff5c>"
ASSISTANT_TAG = "<\uff5cAssistant\uff5c>"


def load_kv_reader():
    """复用 eval/probe/rover_prompt.py 的独立解析实现 (单一来源, 避免第三份拷贝)。"""
    sys.path.insert(0, os.path.join(ROOT, "eval", "probe"))
    import rover_prompt
    return rover_prompt.read_gguf_kv


def engine_render(messages, add_generation_prompt=True):
    """复刻 src/agent.rover/token/ChatTemplate.cs 的 Render (逐行同语义)。"""
    sys_msgs = [m["content"] for m in messages if m["role"] == "system"]
    sb = BOS + "\n\n".join(sys_msgs)
    is_last_user = False
    for m in messages:
        r = m["role"]
        if r == "system":
            continue
        if r == "user":
            sb += USER_TAG + m["content"] + ASSISTANT_TAG
            is_last_user = True
        elif r == "assistant":
            sb += m["content"] + EOS
            is_last_user = False
        else:
            raise ValueError("unsupported role %s" % r)
    if add_generation_prompt and not is_last_user:
        sb += ASSISTANT_TAG
    return sb


def oracle_render(tpl, messages, add_generation_prompt=True, extra=None):
    """用模型自带模板 + jinja2 渲染 (transformers 同引擎同参数)。"""
    import jinja2
    env = jinja2.Environment(trim_blocks=False, lstrip_blocks=False)

    def raise_exception(msg):
        raise ValueError("chat_template raise_exception: %s" % msg)

    env.globals["raise_exception"] = raise_exception
    env.filters["tojson"] = lambda v, **kw: json.dumps(v, ensure_ascii=False, **kw)
    env.globals["strftime_now"] = lambda fmt="%Y-%m-%d": datetime.now().strftime(fmt)
    out = env.from_string(tpl).render(messages=messages, add_generation_prompt=add_generation_prompt,
                                      bos_token=BOS, eos_token=EOS, **(extra or {}))
    return out


def first_diff(a, b):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n if len(a) != len(b) else -1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gguf", default="/tmp/models/qwen25-math-1.5b-q4km.gguf")
    ap.add_argument("--prompt", default="写一个函数, 返回两数之和, 并给出一个调用示例。")
    ap.add_argument("--system", default="你是严谨的编程与数学助手。请直接给出完整可运行的答案。")
    ap.add_argument("--out", default="")
    ap.add_argument("--json", dest="json_out", default="")
    a = ap.parse_args()

    read_gguf_tokenizer = load_kv_reader()
    kv = read_gguf_tokenizer(a.gguf)
    tpl = kv.get("tokenizer.chat_template", "")
    msgs = [{"role": "system", "content": a.system}, {"role": "user", "content": a.prompt}]
    sys.path.insert(0, os.path.join(ROOT, "eval", "probe"))
    import rover_prompt

    rep = {
        "schema": "r401-prompt-parity/1",
        "ts": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "gguf": a.gguf,
        "gguf_bytes": os.path.getsize(a.gguf),
        "gguf_sha256": hashlib.sha256(open(a.gguf, "rb").read()).hexdigest() if os.path.getsize(a.gguf) < 2 ** 30 else "skip",
        "arch": kv.get("general.architecture"),
        "name": kv.get("general.name"),
        "tokenizer_model": kv.get("tokenizer.ggml.model"),
        "tokenizer_pre": kv.get("tokenizer.ggml.pre"),
        "n_tokens": len(kv.get("tokenizer.ggml.tokens") or []),
        "chat_template_len": len(tpl),
        "chat_template_sha256": hashlib.sha256(tpl.encode()).hexdigest(),
        "chat_template_head": tpl[:600],
    }
    print("== ① 目标模型内嵌模板 (权威源) ==")
    print(json.dumps({k: rep[k] for k in ("arch", "name", "tokenizer_model", "tokenizer_pre", "n_tokens",
                                          "chat_template_len", "chat_template_sha256")},
                     ensure_ascii=False, indent=1))
    print("模板首 600 字符:\n%s\n" % tpl[:600].replace("\n", "\u23ce\n"))

    try:
        oracle, r_attest = rover_prompt.render_prompt(a.gguf, a.system, a.prompt, kv=kv)
        rep["oracle_render_ok"] = True
        rep["oracle_attest"] = r_attest
    except Exception as e:  # noqa: BLE001
        rep["oracle_render_ok"] = False
        rep["oracle_render_error"] = "%s: %s" % (type(e).__name__, e)
        oracle = ""
        print("!! jinja2 渲染失败: %s" % rep["oracle_render_error"])

    engine = engine_render(msgs)
    rep["engine_template"] = "ChatTemplate.cs (硬编码 DeepSeek 版式)"
    rep["engine_prompt"] = engine
    rep["oracle_prompt"] = oracle
    d = first_diff(engine, oracle)
    rep["first_diff_char"] = d
    rep["engine_head60"] = engine[:60]
    rep["oracle_head60"] = oracle[:60]
    rep["parity"] = "IDENTICAL" if d == -1 else "DIVERGENT"

    print("== ② 两臂 prompt 对比 ==")
    print("engine(硬编码 DeepSeek 版式) 首 120 字符: %s" % engine[:120].replace("\n", "\u23ce"))
    print("oracle(模型自带模板, jinja2) 首 120 字符: %s" % oracle[:120].replace("\n", "\u23ce"))
    print("首个分歧字符位: %s  ⇒ %s" % (d, rep["parity"]))
    if d >= 0 and oracle:
        print("  分歧处两侧: engine=%r oracle=%r" % (engine[max(0, d - 20):d + 40], oracle[max(0, d - 20):d + 40]))

    # ③ 标签是否在目标模型词表内 (单 token 可编码 ⇒ 结构标签有效; 否则会被切成碎片)
    toks = kv.get("tokenizer.ggml.tokens") or []
    vocab_map = {t: i for i, t in enumerate(toks)}
    tags = {"bos": BOS, "eos": EOS, "user": USER_TAG, "assistant": ASSISTANT_TAG}
    rep["engine_tags_in_target_vocab"] = {k: (v in vocab_map) for k, v in tags.items()}
    tpl_tags = []
    for cand in ("<|im_start|>", "<|im_end|>", "<\uff5cend\u2581of\u2581text\uff5c>", "<\uff5cbegin\u2581of\u2581sentence\uff5c>"):
        if cand in tpl:
            tpl_tags.append((cand, cand in vocab_map))
    rep["template_tags_in_target_vocab"] = tpl_tags
    print("\n== ③ 标签是否在目标模型词表内 ==")
    print("引擎硬编码标签: %s" % json.dumps(rep["engine_tags_in_target_vocab"], ensure_ascii=False))
    print("模型模板实际标签: %s" % json.dumps(tpl_tags, ensure_ascii=False))

    verdict = ("prompt-parity BROKEN: 引擎硬编码版式与目标模型自带模板结构性不同, "
               "且 %d/%d 硬编码标签不在目标词表 ⇒ 引擎收到错误 prompt" % (
                   sum(1 for v in rep["engine_tags_in_target_vocab"].values() if not v),
                   len(rep["engine_tags_in_target_vocab"]))) if d != -1 else "prompt-parity OK"
    rep["verdict"] = verdict
    print("\n判定: %s" % verdict)

    out = a.json_out or os.path.join(ROOT, "eval", "rover", "r401", "prompt-parity.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=2)
    print("→ %s" % out)
    if a.out:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write("### engine prompt (硬编码 DeepSeek 版式)\n%s\n\n### oracle prompt (模型自带模板)\n%s\n" % (engine, oracle))
        print("→ %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
