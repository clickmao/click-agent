#!/usr/bin/env python3
"""rover 臂的 prompt 对等 (prompt parity) 渲染 — R401。

问题 (已取证, 见 eval/rover/r401/prompt-parity.json)
---------------------------------------------------
引擎内建 `--chat` 是**硬编码 DeepSeek 版式** (`src/agent.rover/token/ChatTemplate.cs`:
`<｜begin▁of▁sentence｜>` / `<｜User｜>` / `<｜Assistant｜>`, 断言依据是 DeepSeek-Prover 词表资产)。
对 qwen2/qwen3 等族模型实机实测: **4/4 硬编码标签不在目标词表**, 首个分歧在字符 1 (结构性不同);
标签会退化成字节碎片 ⇒ 引擎收到的是**错误 prompt** (不是"措辞差异")。

本模块的作用
------------
让「远端 API vs 本机引擎」的解法级对比满足 prompt 对等:
  * 模板**取自目标 GGUF 自身** (`tokenizer.chat_template`, 权威源, 记 sha256);
  * 用 jinja2 渲染 (与 transformers 同引擎同参数), 支持 system/user 两类消息 + add_generation_prompt;
  * 渲染结果以**非 chat 路径** (`--prompt`) 原样送入引擎, 因此不受引擎硬编码版式影响;
  * 引擎回报的 `prompt_sha256` 用于**原样送达**对账 (见 attest_verbatim)。

口径: 引擎侧的硬编码 chat 渲染是 R403 (chat template 全量) 的靶点;
本模块不掩盖该缺陷, 只让 R401 的对比**可执行且对等**。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read_gguf_kv(gguf: str) -> dict:
    """独立解析实现 (与 C# GgufReader 非共享代码): 读 GGUF KV。"""
    spec = importlib.util.spec_from_file_location(
        "rover_build_tokenizer_fixtures", os.path.join(ROOT, "scripts", "rover_build_tokenizer_fixtures.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.read_gguf_tokenizer(gguf)


def resolve_special(kv: dict, key: str) -> str:
    """特殊符号 id → 文本 (与 transformers 的 `bos_token`/`eos_token` 语义一致: **传字符串, 不是 id**)。

    缺陷取证 (R401 步2, 2026-09-14): 本函数不存在时, render_prompt 直接把
    `kv["tokenizer.ggml.bos_token_id"]` (= 151646, int) 传给模板的 `bos_token` 变量 ⇒
    模板里 `{{bos_token}}` 渲染成**字面 6 字符 "151646"**, 而不是 BOS 特殊符号
    (`<｜begin▁of▁sentence｜>`) ⇒ 引擎收到的是**首位带垃圾前缀的错误 prompt**。
    该缺陷**不会被送达对账发现**: attest 比的是「我方 sha」与「引擎回显 sha」, 两者
    对同一串错误字节**恒等** (自证型断言)。唯一能发现它的是**跨实现对照**:
    引擎自身 chat 路径 (读同一 GGUF 模板) 渲染 sha256 —— 见 eval/probe/r401_prompt_parity.py。
    """
    idx = kv.get(key)
    toks = kv.get("tokenizer.ggml.tokens")
    if isinstance(idx, int) and isinstance(toks, list) and 0 <= idx < len(toks):
        return toks[idx]
    return ""


def render_prompt(gguf: str, system: str, user: str, kv: dict = None) -> tuple:
    """按目标模型自带模板渲染对话 prompt。返回 (text, attest)。"""
    import jinja2

    kv = kv if kv is not None else read_gguf_kv(gguf)
    tpl = kv.get("tokenizer.chat_template", "")
    if not tpl:
        raise SystemExit("模型内嵌 chat_template 缺失: %s (无法保证 prompt 对等, 拒绝猜测)" % gguf)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})

    bos = resolve_special(kv, "tokenizer.ggml.bos_token_id")
    eos = resolve_special(kv, "tokenizer.ggml.eos_token_id")

    env = jinja2.Environment(trim_blocks=False, lstrip_blocks=False)
    env.globals["raise_exception"] = lambda msg: (_ for _ in ()).throw(ValueError("chat_template raise_exception: %s" % msg))
    env.filters["tojson"] = lambda v, **kw: json.dumps(v, ensure_ascii=False, **kw)
    env.globals["strftime_now"] = lambda fmt="%Y-%m-%d": ""
    text = env.from_string(tpl).render(
        messages=messages, add_generation_prompt=True, tools=None,
        bos_token=bos, eos_token=eos)

    attest = {
        "prompt_source": "gguf-embedded-chat_template+jinja2",
        "template_sha256": hashlib.sha256(tpl.encode("utf-8")).hexdigest(),
        "template_len": len(tpl),
        "jinja2": jinja2.__version__,
        "prompt_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "prompt_chars": len(text),
        "model_arch": kv.get("general.architecture"),
        "bos_token": bos,
        "eos_token": eos,
        "special_tokens_resolved": bool(bos),
    }
    return text, attest


def attest_verbatim(attest: dict, engine_reported_sha: str) -> bool:
    """引擎回报的 prompt_sha256 == 我方送出的 sha256 ⇒ 原样送达 (机制启用断言)。"""
    return bool(attest.get("prompt_sha256")) and attest["prompt_sha256"] == (engine_reported_sha or "")
