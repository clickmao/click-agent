#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deepseek-probe — click-agent 内部用例测试探针 (v0.21.0+)

目的: 在不依赖 NativeAOT 构建的前提下, 用真实 DeepSeek API 验证
      src/agent.modelqueue 发出的 OpenAI 兼容 chat/completions 请求契约,
      并捕获项目当前 DTO (OpenAIChatResponseDtos.cs) 未解析的字段
      (例如 reasoning_content), 为模型队列 + 推理模型接入提供依据。

被测契约 (来自 ModelQueueRouter.CallEntryAsync + models.yaml):
  - POST {request_address}  (https://api.deepseek.com/v1/chat/completions)
  - Authorization: Bearer <AGENTFRAMEWORK_KEYS_DEEPSEEK>
  - body: { model: <catalog name>, messages:[...], max_tokens, temperature, reasoning_effort? }
  - balance: GET https://api.deepseek.com/user/balance

用法:
  export DEEPSEEK_API_KEY=sk-xxx
  python3 deepseek_probe.py            # 跑全部用例, 输出 JSON 摘要到 stdout
  python3 deepseek_probe.py --quiet     # 仅输出 PASS/FAIL 结论

凭据铁律: 本脚本绝不硬编码 key; 仅从环境变量读取; 输出中的 key 一律脱敏。
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

API_BASE = "https://api.deepseek.com"
CHAT = f"{API_BASE}/v1/chat/completions"
BALANCE = f"{API_BASE}/user/balance"

# 项目 models.yaml 当前首选模型名 (catalog name == 实际发送的 model 字段)
PROJECT_MODEL = "deepseek-flash"


def _redact(key: str) -> str:
    if not key:
        return "<empty>"
    return key[:6] + "…" + key[-4:] if len(key) > 12 else "***"


def _post(model: str, messages, *, max_tokens=64, temperature=0.7,
          reasoning_effort=None, api_key="", retries=3):
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if reasoning_effort is not None:
        body["reasoning_effort"] = reasoning_effort
    data = json.dumps(body).encode("utf-8")
    last_err = None
    for attempt in range(retries):
        _sleep()
        req = urllib.request.Request(CHAT, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {api_key}")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "click-agent-deepseek-probe/1.0")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8")), None
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            # 瞬态: DeepSeek 对该 IP 偶发 401/429 窗口 — 退避重试 (对齐项目 OnTransientFailure 精神)
            if e.code in (401, 429, 500, 502, 503):
                try:
                    payload = json.loads(e.read().decode("utf-8"))
                except Exception:
                    payload = e.read().decode("utf-8", "replace")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt * 3 + 2)
                    continue
                return e.code, payload, last_err
            try:
                payload = json.loads(e.read().decode("utf-8"))
            except Exception:
                payload = e.read().decode("utf-8", "replace")
            return e.code, payload, last_err
        except Exception as e:  # 网络/超时
            last_err = f"{type(e).__name__}: {e}"
            if attempt < retries - 1:
                time.sleep(2 ** attempt * 3 + 2)
                continue
            return None, None, last_err
    return None, None, last_err


def _sleep():
    # 避免触发 DeepSeek 速率窗口 (实测连续请求偶发 401/429)
    time.sleep(1.5)


def _get_balance(api_key: str, retries=3):
    last_err = None
    for attempt in range(retries):
        _sleep()
        req = urllib.request.Request(BALANCE, method="GET")
        req.add_header("Authorization", f"Bearer {api_key}")
        req.add_header("User-Agent", "click-agent-deepseek-probe/1.0")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8")), None
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            if e.code in (401, 429, 500, 502, 503) and attempt < retries - 1:
                time.sleep(2 ** attempt * 3 + 2)
                continue
            try:
                payload = json.loads(e.read().decode("utf-8"))
            except Exception:
                payload = e.read().decode("utf-8", "replace")
            return e.code, payload, last_err
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            if attempt < retries - 1:
                time.sleep(2 ** attempt * 3 + 2)
                continue
            return None, None, last_err
    return None, None, last_err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("ERROR: 请先 export DEEPSEEK_API_KEY=sk-xxx", file=sys.stderr)
        return 2
    if not args.quiet:
        print(f"[deepseek-probe] key={_redact(api_key)} base={API_BASE}", flush=True)

    results = {"project_model": PROJECT_MODEL, "cases": [], "balance": None}

    def record(name, status, ok, note, extra=None):
        case = {"name": name, "http": status, "ok": ok, "note": note}
        if extra:
            case.update(extra)
        results["cases"].append(case)
        if not args.quiet:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {note}", flush=True)

    msgs = [{"role": "user", "content": "用一句话介绍北京"}]

    # 用例1: 项目当前实际发送 (model=deepseek-flash)
    st, body, err = _post(PROJECT_MODEL, msgs)
    has_rc = bool(body and body.get("choices") and
                  body["choices"][0]["message"].get("reasoning_content"))
    record("chat_deepseek_flash", st, st == 200,
           note=f"model 回显={body.get('model') if body else err}; 返回 reasoning_content={has_rc}",
           extra={"reasoning_content": has_rc,
                  "finish_reason": (body.get("choices", [{}])[0].get("finish_reason")
                                    if body else None)})

    # 用例2: deepseek-chat (非推理)
    st, body, err = _post("deepseek-chat", msgs)
    has_rc = bool(body and body.get("choices") and
                  body["choices"][0]["message"].get("reasoning_content"))
    record("chat_deepseek_chat", st, st == 200,
           note=f"返回 reasoning_content={has_rc}",
           extra={"reasoning_content": has_rc})

    # 用例3: 普通模型 + reasoning_effort (验证是否报错 — 项目对推理档透传给所有模型)
    st, body, err = _post("deepseek-chat", msgs, reasoning_effort="low")
    record("chat_deepseek_chat_with_reasoning_effort", st, st == 200,
           note=(f"reasoning_effort=low 被接受" if st == 200
                 else f"拒绝: {body if body else err}"))

    # 用例4: 推理模型 reasoning_effort 档位对比 (low vs high)
    rc_low = rc_high = None
    st_low, body_low, _ = _post(PROJECT_MODEL, msgs, reasoning_effort="low", max_tokens=512)
    if body_low and body_low.get("choices"):
        rc_low = len(body_low["choices"][0]["message"].get("reasoning_content") or "")
    st_high, body_high, _ = _post(PROJECT_MODEL, msgs, reasoning_effort="high", max_tokens=512)
    if body_high and body_high.get("choices"):
        rc_high = len(body_high["choices"][0]["message"].get("reasoning_content") or "")
    record("reasoning_effort_levels", (st_low if st_low == st_high else None),
           st_low == 200 and st_high == 200,
           note=f"deepseek-flash reasoning_content 长度 low={rc_low} high={rc_high}",
           extra={"rc_len_low": rc_low, "rc_len_high": rc_high})

    # 用例5: deepseek-reasoner (历史推理模型, 验证可用性/字段)
    st, body, err = _post("deepseek-reasoner", msgs, max_tokens=256)
    has_rc = bool(body and body.get("choices") and
                  body["choices"][0]["message"].get("reasoning_content"))
    record("chat_deepseek_reasoner", st, st == 200,
           note=(f"返回 reasoning_content={has_rc}" if st == 200
                 else f"不可用: {body if body else err}"),
           extra={"reasoning_content": has_rc})

    # 用例6: balance 端点 (models.yaml balance_schemes.deepseek)
    st, body, err = _get_balance(api_key)
    # 实测返回结构: { is_available, balance_infos:[{ currency, total_balance, granted_balance, topped_up_balance }] }
    # 注意: 实际币种为 CNY (models.yaml 注释写 "USD" 需校正)
    bal_cny = None
    if isinstance(body, dict):
        infos = body.get("balance_infos") or []
        cny = next((i for i in infos if i.get("currency") == "CNY"), None)
        if cny:
            bal_cny = cny.get("total_balance")
    results["balance"] = {"http": st, "raw": body if not isinstance(body, str) else err}
    record("user_balance", st, st == 200,
           note=(f"CNY 余额={bal_cny} (币种实测 CNY, 非 YAML 注释的 USD)"
                 if st == 200 else f"失败: {body if body else err}"),
           extra={"cny_balance": bal_cny})

    passed = sum(1 for c in results["cases"] if c["ok"])
    total = len(results["cases"])
    results["summary"] = {"passed": passed, "total": total}

    print(json.dumps(results, ensure_ascii=False, indent=2))
    if not args.quiet:
        print(f"\n[deepseek-probe] 结论: {passed}/{total} 用例通过", flush=True)
    # 关键可观测信号: 项目 DTO 是否遗漏 reasoning_content
    rc_models = [c["name"] for c in results["cases"]
                 if c.get("reasoning_content") is True]
    if rc_models:
        print(f"[deepseek-probe] 提示: 以下模型返回 reasoning_content, "
              f"但 OpenAIChatResponseDtos.cs 当前未解析该字段: {rc_models}",
              file=sys.stderr)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
