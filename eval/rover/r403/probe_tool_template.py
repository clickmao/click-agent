#!/usr/bin/env python3
"""R403 裁定取证: llama.cpp 工具调用模板行为 (两臂 + 负控), 自包含可复跑.

臂 default  = 模型自带模板 (GGUF 元数据, --jinja)
臂 control  = 合成的最小 tools-支持模板 (--chat-template-file)  <- 探针判别力负控

每臂读数: /props 的 chat_template_caps + 模板源统计 + apply-template 的 ±tools prompt md5
          + /v1/chat/completions 的 ±tools prompt_tokens (同 messages, max_tokens=1)
退出码: 0 = 全部读数取到; 3 = 有臂读数为空 (measure-failure, 与断言失败分码)

用法: python3 eval/rover/r403/probe_tool_template.py [--json <out>]
"""
import argparse
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import urllib.request

BIN = os.environ.get(
    "AGENTFRAMEWORK_LLAMA_BIN",
    "/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server",
)
MODEL = os.environ.get("R403_MODEL", "/tmp/models/r1-distill-qwen-1.5b-q4km.gguf")
HERE = pathlib.Path(__file__).resolve().parent
TOOLS = [{"type": "function", "function": {"name": "get_weather", "description": "w",
          "parameters": {"type": "object", "properties": {"city": {"type": "string"}}}}}]
MESSAGES = [{"role": "system", "content": "S"}, {"role": "user", "content": "hi"}]
COMPLETION_MESSAGES = [{"role": "user", "content": "hi"}]

# 合成负控模板: 只有 ASCII (避免写入通道改写特殊标记), 且带 tools 分支
CONTROL_TEMPLATE = (
    "{%- if tools %}[TOOLSDEF]{% for tool in tools %}{{ tool['function']['name'] }};{% endfor %}"
    "[/TOOLSDEF]{% endif %}\n"
    "{%- for message in messages %}{{ message['role'] }}: {{ message['content'] }}\n{% endfor -%}\n"
    "{%- if add_generation_prompt %}assistant:{% endif %}"
)


def post(url, payload, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def get(url, timeout=15):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()


def run_arm(name, port, extra_args, log):
    proc = subprocess.Popen([BIN, "-m", MODEL, "-c", "512", "-t", "1", "-np", "1", "--jinja",
                             "--cache-type-k", "f32", "--cache-type-v", "f32", "--flash-attn", "off",
                             "--port", str(port)] + extra_args,
                            stdout=open(log, "wb"), stderr=subprocess.STDOUT, start_new_session=True)
    try:
        base = f"http://127.0.0.1:{port}"
        t0 = time.time()
        ready = False
        while time.time() - t0 < 120:
            if proc.poll() is not None:
                return {"arm": name, "error": f"server exited early rc={proc.returncode}", "log": log}
            try:
                if get(base + "/health", 3).get("status") == "ok":
                    ready = True
                    break
            except Exception:
                time.sleep(1)
        if not ready:
            return {"arm": name, "error": "readiness timeout 120s", "log": log}
        ready_s = round(time.time() - t0, 1)

        props = get(base + "/props")
        tpl = props.get("chat_template") or ""
        a_no = post(base + "/apply-template", {"messages": MESSAGES})["prompt"]
        a_yes = post(base + "/apply-template", {"messages": MESSAGES, "tools": TOOLS})["prompt"]
        c_no = post(base + "/v1/chat/completions",
                    {"messages": COMPLETION_MESSAGES, "max_tokens": 1, "temperature": 0})
        c_yes = post(base + "/v1/chat/completions",
                     {"messages": COMPLETION_MESSAGES, "tools": TOOLS, "max_tokens": 1, "temperature": 0})
        return {
            "arm": name,
            "port": port,
            "ready_after_s": ready_s,
            "chat_template_caps": props.get("chat_template_caps"),
            "template": {"chars": len(tpl), "utf8_bytes": len(tpl.encode()),
                         "count_tools_var": tpl.count("tools"),
                         "count_tool_definitions": tpl.count("definitions"),
                         "count_tool_calls_ref": tpl.count("tool_calls"),
                         "count_role_tool_ref": tpl.count("== 'tool'")},
            "apply_template": {"without_tools_md5": md5(a_no), "with_tools_md5": md5(a_yes),
                               "identical": a_no == a_yes,
                               "without_tools_len": len(a_no), "with_tools_len": len(a_yes)},
            "completions_prompt_tokens": {"without_tools": c_no["usage"]["prompt_tokens"],
                                          "with_tools": c_yes["usage"]["prompt_tokens"],
                                          "delta": c_yes["usage"]["prompt_tokens"] - c_no["usage"]["prompt_tokens"]},
            "http_status_with_tools": 200,
            "server_rc": proc.returncode,
        }
    except Exception as e:  # 测量失败要出声, 不静默
        return {"arm": name, "error": f"{type(e).__name__}: {e}", "log": log}
    finally:
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                proc.wait(timeout=10)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "tool-template-behavior.json"))
    a = ap.parse_args()

    ctrl = HERE / "control-template.jinja"
    ctrl.write_text(CONTROL_TEMPLATE, encoding="utf-8")
    raw = ctrl.read_bytes()

    out = {
        "round": "R403-scope",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "question": "工具调用模板是否改口径为「验证 llama.cpp tool 模板行为」(backlog R403 待定项)",
        "engine": {"binary": BIN, "model": MODEL,
                   "build_info": None, "context": 512, "flags": "--jinja, f32 KV, flash-attn off"},
        "control_template": {"file": str(ctrl), "bytes": len(raw),
                             "non_ascii_bytes": sum(1 for b in raw if b > 127)},
        "arms": [],
        "product_side_consumers": None,
    }
    out["arms"].append(run_arm("default_gguf_template", 41998, [], "/tmp/r403-default-server.log"))
    out["arms"].append(run_arm("control_synthetic_tools_template", 41999,
                               ["--chat-template-file", str(ctrl)], "/tmp/r403-control-server.log"))

    try:
        out["engine"]["build_info"] = get("http://127.0.0.1:41998/props", 2).get("build_info")
    except Exception:
        pass

    # 产品侧消费方计数 (0 = 无消费者), 排除同名目录字符串
    try:
        g = subprocess.run(["grep", "-rn", "-E", "tool_choice|ToolCall|tool_calls|\"tools\"",
                            "src/", "--include=*.cs"], capture_output=True, text=True, cwd=str(HERE.parents[3]))
        hits = [l for l in g.stdout.splitlines()
                if "/obj/" not in l and "/bin/" not in l and 'Combine(root, "tools"' not in l]
        out["product_side_consumers"] = {"count": len(hits), "hits": hits[:10]}
    except Exception as e:
        out["product_side_consumers"] = {"error": str(e)}

    pathlib.Path(a.json).write_text(json.dumps(out, ensure_ascii=True, indent=2), encoding="utf-8")
    errs = [x for x in out["arms"] if "error" in x]
    print(json.dumps(out, ensure_ascii=True, indent=2))
    print(f"\nR403_PROBE_EXIT={3 if errs else 0} arms_ok={len(out['arms'])-len(errs)}/{len(out['arms'])}"
          f" written={a.json}")
    return 3 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
