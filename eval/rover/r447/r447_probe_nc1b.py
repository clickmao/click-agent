#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R447 补充器具（posthoc）：**真错配 prev** 负控 —— 修 NC1 的判定项设计缺陷。

为什么需要
──────────
预注册的 C4a（错配 prev 应与 J0 显著不一致）在**本语料上不可测**：prev 候选只有 2 个常量
（桩应答 15 字符 / 跳过应答 21 字符），而 NC1 取「i+1 的 prev」⇒ 8 条里有 5 条**换了个寂寞**
（前后 prev 本来就相同）。这是**判定项设计缺陷**（不是产品结论），如实登记为 C4a FAIL。

本补充臂把错配**做实**：orig prev 为 15 字符的 → 换成 26 字符**真实**上一轮回复
（`eval/rover/r435/judge-prompt-golden-v2.jsonl` 的 syn 案例原文）；orig 为 21 的 → 换成 15 字符桩应答。
逐条断言 `wrong_prev != orig_prev`，否则 fail-closed。
"""
import importlib.util
import json
import pathlib
import signal
import subprocess
import sys
import time
import urllib.request

R = pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r447")
ROOT = R.parents[2]
PORT = 47982
BASE = f"http://127.0.0.1:{PORT}"
MODEL = "/tmp/models/r1-distill-qwen-1.5b-q4km.gguf"
BIN = "/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server"
TAIL = ["-c", "4608", "-t", "1", "-np", "1", "--cache-type-k", "f32", "--cache-type-v", "f32",
        "--flash-attn", "off", "--jinja"]
REAL_PREV = "已把前置门接进链里，跳过轮的 token 已降下来。"
N = 8


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    corp = json.loads((R / "corpus.json").read_text(encoding="utf-8"))
    base = json.loads((R / "probe-r447.json").read_text(encoding="utf-8"))
    letters_mod = load_mod("r447_probe", R / "r447_probe.py")
    letters_mod.BASE = BASE          # 覆盖导入模块的端口（避免与主探针端口耦合）
    L = letters_mod.derive_literals()
    tpl = load_mod("r447_corpus", R / "r447_corpus.py").derive_prompt_template()
    J0 = {r["i"]: r for r in base["arms"]["J0"]}

    proc = subprocess.Popen([BIN, "-m", MODEL, "--host", "127.0.0.1", "--port", str(PORT)] + TAIL,
                            stdout=open("/tmp/r447_nc1b_server.log", "w"), stderr=subprocess.STDOUT)
    t0 = time.time()
    while time.time() - t0 < 300:
        try:
            with urllib.request.urlopen(BASE + "/health", timeout=2) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(2)
    else:
        raise SystemExit("[致命] server 未就绪")

    out = {"round": "R447", "instrument": "r447_nc1b", "note": "posthoc 真错配 prev 负控",
           "real_prev": REAL_PREV, "rows": []}
    try:
        for k in range(N):
            p = corp["pairs"][k]
            orig = p["prev"]
            wrong = REAL_PREV if len(orig) <= 20 else "桩应答: 收到, 已完成该步。"
            assert wrong != orig, f"[致命] 错配无效 i={k}"
            prompt = load_mod("r447_corpus", R / "r447_corpus.py").build_prompt(tpl, wrong, p["msg"])
            rendered = letters_mod.render(prompt, L)
            c = letters_mod.complete(rendered, 512, None)
            letter, reason = letters_mod.try_normalize(c.get("content"), L)
            row = {"i": k, "msg": p["msg"], "orig_prev": orig, "wrong_prev": wrong,
                   "letter_nc1b": letter, "parse_reason": reason, "gen": c.get("gen"),
                   "prompt_n": c.get("prompt_n"), "wall_s": c.get("wall_s"),
                   "letter_J0": J0.get(k, {}).get("letter"), "content": c.get("content")}
            out["rows"].append(row)
            (R / "probe-r447-nc1b.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[NC1b] i={k} {p['msg']!r} orig={orig[:8]!r} wrong={wrong[:8]!r} "
                  f"letter={letter} (J0={row['letter_J0']}) gen={c.get('gen')}", flush=True)
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=20)
        except Exception:
            proc.kill()

    rows = out["rows"]
    eq = sum(1 for r in rows if r["letter_nc1b"] is not None and r["letter_nc1b"] == r["letter_J0"])
    out["agree_NC1b_J0"] = round(eq / len(rows), 4)
    out["n"] = len(rows)
    (R / "probe-r447-nc1b.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[NC1b] agree={out['agree_NC1b_J0']} n={len(rows)} → {R/'probe-r447-nc1b.json'}")


if __name__ == "__main__":
    main()
