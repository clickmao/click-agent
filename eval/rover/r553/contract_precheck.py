#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R553 起手闸 C —— 契约面健康预检 (R552 §8 候选①(a), **只改器具**)。

动机: R552 实测 24 窗里 15 窗(62%) 死在**上游/模型侧契约面**(`rc=4 stage=contract`,
或中继 dump 的 `response.text` 不可解析率 >0.25) ⇒ 臂被环境抖动吃掉, 有效窗数不足,
J2(质量)不可判。本闸在**每次起臂前**打 1 次**最小契约调用**(1 次远端请求, max_tokens 小),
不可解析 ⇒ 不起臂 ⇒ 该窗不消耗整轮的远端调用。

口径(先定义后执行):
  PASS    ⇔ 响应 `content` 去空白后 `json.loads` 成功**且是 dict**;
  BLOCKED ⇔ 否则(实测退化形态: ①JSON 后跟续写的第二个对象 ②复读指令/散文 ③截断)。
  rc: 0=PASS / 2=BLOCKED / 3=环境不可用(缺 .env.local key 或网络异常, fail-closed)。

自检(`--selfcheck`, 机件有牙的负向控制; 铁律 9: 无负控=未验证):
  P1 合法单对象 → 必须 PASS
  N1 JSON 后跟第二个对象(`{...}{...}`) → 必须 BLOCKED   ← R552 退化形态①
  N2 复读指令散文(无 JSON) → 必须 BLOCKED            ← R552 退化形态②
  N3 截断 JSON(缺右花括号) → 必须 BLOCKED
  P2 实时上游 1 次最小契约调用 → 记录判决(不计入 has_teeth, 网络不可用时不伪造)

用法:
  python3 eval/rover/r553/contract_precheck.py --out /tmp/precheck-60.json          # 起臂前预检
  python3 eval/rover/r553/contract_precheck.py --selfcheck --out <dir>/precheck-selfcheck.json
"""
import io
import json
import os
import sys
import time
import urllib.request

REPO = "/home/agentuser/AgentFramework"
UPSTREAM = os.environ.get("R553_PRECHECK_UPSTREAM", "https://api.deepseek.com/v1/chat/completions")
MODEL = os.environ.get("R553_PRECHECK_MODEL", "deepseek-chat")
SYS = "You are a contract endpoint. Reply with EXACTLY one JSON object and nothing else. No prose, no code fence."
USR = 'Return {"ok": true, "n": 1}'


def classify(text):
    """契约面判决: 唯一判据 = 去空白后能否解析出 dict。"""
    s = (text or "").strip()
    rec = {"len_chars": len(s), "parses_json": False, "is_dict": False, "verdict": "BLOCKED"}
    try:
        obj = json.loads(s)
        rec["parses_json"] = True
        rec["is_dict"] = isinstance(obj, dict)
    except Exception as e:
        rec["err"] = str(e)[:80]
    # hygiene 单列(不进判决): 去代码围栏后是否可解析
    body = s
    if body.startswith("```"):
        body = body.split("\n", 1)[-1]
        body = body.rsplit("```", 1)[0]
    try:
        json.loads(body.strip())
        rec["parses_after_fence_strip"] = True
    except Exception:
        rec["parses_after_fence_strip"] = False
    if rec["parses_json"] and rec["is_dict"]:
        rec["verdict"] = "PASS"
    return rec


def api_key():
    for k in ("AGENTFRAMEWORK_KEYS_DEEPSEEK", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"):
        v = os.environ.get(k)
        if v:
            return v
    p = os.path.join(REPO, ".env.local")
    if os.path.isfile(p):
        for line in io.open(p, encoding="utf-8"):
            line = line.strip()
            if line.startswith("AGENTFRAMEWORK_KEYS_DEEPSEEK="):
                return line.split("=", 1)[1].strip()
    return None


def live_probe(timeout=60):
    key = api_key()
    if not key:
        return {"ok": False, "why": "no_key", "rc": 3}
    body = {"model": MODEL, "messages": [{"role": "system", "content": SYS},
                                         {"role": "user", "content": USR}], "max_tokens": 40}
    req = urllib.request.Request(UPSTREAM, data=json.dumps(body).encode("utf-8"),
                                headers={"Content-Type": "application/json",
                                         "Authorization": "Bearer " + key})
    t0 = time.time()
    try:
        raw = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "why": "%s: %s" % (type(e).__name__, str(e)[:120]), "rc": 3}
    ch = (raw.get("choices") or [{}])[0]
    text = (ch.get("message") or {}).get("content") or ""
    cls = classify(text)
    cls.update({"ok": True, "elapsed_s": round(time.time() - t0, 2), "model": raw.get("model") or MODEL,
                "usage": raw.get("usage"), "finish_reason": ch.get("finish_reason"),
                "content_head": text[:160]})
    cls["rc"] = 0 if cls["verdict"] == "PASS" else 2
    return cls


def selftest(out):
    controls = [
        ("P1_legal_object", '{"ok": true, "n": 1}', "PASS"),
        ("N1_json_then_second_object", '{"ok": true, "n": 1}\n{"ok": true, "n": 2}', "BLOCKED"),
        ("N2_echo_instruction", "You are a contract endpoint. Reply with EXACTLY one JSON object and nothing else.", "BLOCKED"),
        ("N3_truncated_json", '{"ok": true, "n":', "BLOCKED"),
    ]
    res = {}
    teeth = True
    for name, text, want in controls:
        got = classify(text)["verdict"]
        ok = got == want
        teeth = teeth and ok
        res[name] = {"want": want, "got": got, "ok": ok}
    live = live_probe()
    res["P2_live_upstream"] = {"verdict": live.get("verdict"), "rc": live.get("rc"),
                               "note": "实时, 不计入 has_teeth"}
    rep = {"tool": "contract_precheck.py", "round": "R553",
           "rule": "PASS ⇔ content 去空白后 json.loads 成功且为 dict",
           "controls": res, "negative_controls_n": 3, "positive_controls_n": 2,
           "HAS_TEETH": bool(teeth),
           "verdict_counts_against_old_rule": {
               "N1": "旧规则(仅判能否解析整段)同样红 ⇒ 本闸的判别力来自『整段单对象』而非宽松解析"}}
    io.open(out, "w", encoding="utf-8").write(json.dumps(rep, ensure_ascii=False, indent=1))
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    print("PRECHECK_SELFCHECK_OK=%s" % teeth)
    return 0 if teeth else 1


def main(argv):
    out = None
    selfcheck = False
    i = 1
    while i < len(argv):
        if argv[i] == "--out":
            out = argv[i + 1]; i += 2
        elif argv[i] == "--selfcheck":
            selfcheck = True; i += 1
        else:
            print("[致命] 未知参数 %s" % argv[i]); return 3
    if not out:
        print("[致命] 缺 --out"); return 3
    if selfcheck:
        return selftest(out)
    r = live_probe()
    r["tool"] = "contract_precheck.py"
    r["rule"] = "PASS ⇔ content 去空白后 json.loads 成功且为 dict; 不可解析 ⇒ 不起臂"
    io.open(out, "w", encoding="utf-8").write(json.dumps(r, ensure_ascii=False, indent=1))
    print("PRECHECK %s rc=%s verdict=%s len=%s elapsed=%ss" % (
        r.get("verdict"), r.get("rc"), r.get("verdict"), r.get("len_chars"), r.get("elapsed_s")))
    return r.get("rc", 3)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
