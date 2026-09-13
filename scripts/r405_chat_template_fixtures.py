#!/usr/bin/env python3
"""R405 / P0-2 夹具: 从 GGUF 抽 tokenizer.chat_template, 用 jinja2(transformers 同引擎) 渲染金标。

判据预注册 (本文件头部):
  1. 抽取的模板必须与 GGUF KV 中 tokenizer.chat_template 逐字节相等 (长度 + sha256 记录)。
  2. 金标文本由 jinja2 渲染产生; C# 渲染器的验收 = 与金标逐字节相等 (100%), 不允许近似。
  3. 模板用到的变量必须被显式记录 (供 C# 侧对齐上下文); 渲染失败必须记录 error 而非静默跳过。
  4. 不支持的构造必须在 C# 侧显式抛, 不得静默降级 —— 本脚本只产金标, 不做兼容性猜测。

用法: python3 scripts/r405_chat_template_fixtures.py <model.gguf> <tag>
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

KV_SIZES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}


def read_gguf_strings(path: str) -> dict:
    """只解析 KV 段, 返回 {key: value}; 数组值返回实际列表 (仅 str 数组)。"""
    out = {}
    with open(path, "rb") as f:
        assert f.read(4) == b"GGUF", "not a GGUF file"
        struct.unpack("<I", f.read(4))[0]           # version
        n_tensors = struct.unpack("<Q", f.read(8))[0]
        n_kv = struct.unpack("<Q", f.read(8))[0]

        def rstr() -> str:
            n = struct.unpack("<Q", f.read(8))[0]
            return f.read(n).decode("utf-8")

        for _ in range(n_kv):
            k = rstr()
            t = struct.unpack("<I", f.read(4))[0]
            if t == 8:
                out[k] = rstr()
            elif t == 9:
                et = struct.unpack("<I", f.read(4))[0]
                n = struct.unpack("<Q", f.read(8))[0]
                if et == 8:
                    out[k] = [rstr() for _ in range(n)]
                else:
                    f.read(n * KV_SIZES.get(et, 4))
                    out[k] = f"<t{et}[{n}]>"
            else:
                raw = f.read(KV_SIZES[t])
                if t == 6:
                    out[k] = struct.unpack("<f", raw)[0]
                else:
                    out[k] = int.from_bytes(raw, "little", signed=(t in (1, 3, 5)))
    return out


CASES = [
    ("user-single-nogen", [{"role": "user", "content": "What is 12*12? Answer with the number."}], False),
    ("user-single-gen", [{"role": "user", "content": "What is 12*12? Answer with the number."}], True),
    ("system-user-gen", [{"role": "system", "content": "You are a helpful assistant."},
                         {"role": "user", "content": "What is 12*12?"}], True),
    ("multi-turn-gen", [{"role": "user", "content": "What is 12*12?"},
                        {"role": "assistant", "content": "144"},
                        {"role": "user", "content": "Now double it."}], True),
    ("multi-turn-assistant-end", [{"role": "user", "content": "What is 12*12?"},
                                  {"role": "assistant", "content": "144"}], False),
    ("multiline-gen", [{"role": "user", "content": "Line1\nLine2\n\nLine4"}], True),
    ("special-chars-gen", [{"role": "user", "content": "a<|end_of_sentence|>b {{x}} c%}"}], True),
    ("empty-content-gen", [{"role": "user", "content": ""}], True),
    ("padded-whitespace-gen", [{"role": "user", "content": "  padded  "}], True),
    ("reasoning-field-gen", [{"role": "user", "content": "1+1?"},
                             {"role": "assistant", "content": "2",
                              "reasoning_content": "one plus one is two"}], True),
]

CONSTRUCTS = ("namespace(", "is defined", "is none", "{%-", "-%}", "loop.",
              "|length", "|join", "|trim", "raise_exception", "tool_calls", "tools",
              "bos_token", "eos_token", "add_generation_prompt", "reasoning_content",
              "{% set ", "{% for ", "{% if ")


def main() -> int:
    gguf, tag = sys.argv[1], sys.argv[2]
    import jinja2

    kv = read_gguf_strings(gguf)
    tpl = kv.get("tokenizer.chat_template")
    if not tpl:
        print(f"FAIL no tokenizer.chat_template in {gguf}")
        return 1
    raw = tpl.encode("utf-8")
    sha = hashlib.sha256(raw).hexdigest()

    print(f"model={gguf}")
    print(f"  template_len={len(tpl)} chars / {len(raw)} bytes sha256={sha[:16]}")
    toks = kv.get("tokenizer.ggml.tokens")
    if isinstance(toks, list):
        bos_id = kv.get("tokenizer.ggml.bos_token_id")
        eos_id = kv.get("tokenizer.ggml.eos_token_id")
        bos = toks[bos_id] if isinstance(bos_id, int) and 0 <= bos_id < len(toks) else ""
        eos = toks[eos_id] if isinstance(eos_id, int) and 0 <= eos_id < len(toks) else ""
        print(f"  vocab={len(toks)} bos={bos!r} eos={eos!r} "
              f"add_bos={kv.get('tokenizer.ggml.add_bos_token')} "
              f"add_eos={kv.get('tokenizer.ggml.add_eos_token')}")
    else:
        bos = eos = ""

    hit = [c for c in CONSTRUCTS if c in tpl]
    print(f"  constructs_used={hit}")

    env = jinja2.Environment(trim_blocks=False, lstrip_blocks=False, keep_trailing_newline=True)
    tmpl = env.from_string(tpl)
    out_dir = Path("eval/rover/tokref")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{tag}_chat_template.jinja").write_text(tpl, encoding="utf-8")

    ctx_base = {"bos_token": bos, "eos_token": eos, "tools": None, "documents": None}
    rows, used_vars = [], set()
    for name, messages, gen in CASES:
        # 变量发现: 未定义变量在输出中使用会抛 UndefinedError ⇒ 追加空值重试 (记录名字)
        ctx: dict = dict(ctx_base, messages=messages, add_generation_prompt=gen)
        text, error = None, None
        for _ in range(12):
            try:
                text = tmpl.render(**ctx)
                break
            except jinja2.UndefinedError as e:
                msg = str(e)
                missing = None
                for cand in ("tools", "documents", "reasoning_content", "add_generation_prompt",
                             "bos_token", "eos_token", "pad_token", "enable_thinking"):
                    if f"'{cand}'" in msg and cand not in ctx:
                        missing = cand
                        break
                if missing is None:
                    text, error = None, f"UndefinedError: {msg[:200]}"
                    break
                used_vars.add(missing)
                ctx[missing] = None
        else:
            text, error = None, "variable discovery exceeded 12 rounds"
        rec = {"name": name, "messages": messages, "add_generation_prompt": gen,
               "rendered": text, "expected_len": len(text) if text else 0,
               "error": None if text is not None else error}
        rows.append(rec)
        shown = "" if text is None else text.replace("\n", "\\n")[:110]
        print(f"  [{name}] len={rec['expected_len']:5d} {shown}")

    with open(out_dir / f"{tag}_chat_golden.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  wrote {out_dir / (tag + '_chat_golden.jsonl')} rows={len(rows)} "
          f"errors={sum(1 for r in rows if r['error'])} extra_vars_discovered={sorted(used_vars)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
