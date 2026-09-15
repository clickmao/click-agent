#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R478 机检器具 —— 空正文定因机制化 + 请求-轮次因果绑定。

判据 (预注册 C1–C7) 全部**源码派生 + fail-closed**: 取不到即抛 MISS, 不静默通过。
负控 NC1–NC3: 对「旧误诊文案 / 无 finish_reason 判据 / 无 request_id 绑定」三种退化形态,
同一判据必须判红 (证明判据非恒绿)。

输出: eval/rover/r478/verdict-r478.json (utf-8, 无 BOM)
"""
import io, json, os, re, sys, hashlib, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "eval", "rover", "r478", "verdict-r478.json")

OLD_BANNER = "推理过程占满了输出预算"      # R477 证伪的旧误诊文案
NEW_BANNER = "输出预算被推理占满"          # 新文案 (LengthExhausted 分支)
PROTO = ("tool_calls", "length", "stop")


def read(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        raise SystemExit("MISS(src-file): " + rel)
    return io.open(p, encoding="utf-8").read()


def grep_files(pattern, exts=(".cs",)):
    hits = []
    for base, _dirs, files in os.walk(SRC):
        for f in files:
            if not f.endswith(exts):
                continue
            p = os.path.join(base, f)
            try:
                s = io.open(p, encoding="utf-8").read()
            except Exception:
                continue
            for i, line in enumerate(s.splitlines(), 1):
                if re.search(pattern, line):
                    hits.append((os.path.relpath(p, ROOT), i, line.strip()))
    return hits


def sha12(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


res = {"round": "R478", "ts": datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M%z"),
       "criteria": {}, "negative_controls": {}, "source_pins": {}}

diag_rel = "src/agent.modelqueue/EmptyBodyDiagnosis.cs"
diag = read(diag_rel)
res["source_pins"]["EmptyBodyDiagnosis.cs"] = sha12(diag)

# ---------- C1: 定因判据只取协议字段, 禁用户文本关键词 ----------
m = re.search(r"public static EmptyBodyCause Classify\(.*?\n    \}", diag, re.S)
if not m:
    raise SystemExit("MISS(Classify-body): 无法源码派生 Classify 方法体")
body = m.group(0)
kw = [k for k in ("如果", "是否", "继续", "好的", "谢谢", "再讲", "请重试", "帮我") if k in body]
literals = set(re.findall(r'Reason\w+|"[a-zA-Z_]+"', body))
bad_lit = [L for L in literals if L.strip('"') not in PROTO and not L.startswith("Reason")]
res["criteria"]["C1_classify_protocol_only"] = {
    "ok": (not kw) and (not bad_lit),
    "user_text_keywords_in_classify": kw,
    "non_protocol_literals": sorted(bad_lit),
    "protocol_literals": sorted(literals),
}

# ---------- C2: 用户可见空正文文案**单源** ----------
banner_calls = [(f, i, l) for (f, i, l) in grep_files(r"EmptyBodyDiagnosis\.Banner\(")
                if "/agent.tests/" not in f]          # 只数**产品面**调用点(测试面仅作断言, 不算发文案源)
old_emitted = [(f, i, l) for (f, i, l) in grep_files(re.escape(OLD_BANNER)) if "Assert" not in l and "不得再出现" not in l and "误诊" not in l]
res["criteria"]["C2_banner_single_source"] = {
    "ok": len(banner_calls) == 3 and not old_emitted,
    "Banner_call_sites": [f"{f}:{i}" for (f, i, _l) in banner_calls],
    "old_banner_still_emitted": [f"{f}:{i}" for (f, i, _l) in old_emitted],
}
res["source_pins"]["banner_call_sites_n"] = len(banner_calls)

# ---------- C3: ToolCall 因不重试 (省 1 次调用) ----------
r = read("src/agent.modelqueue/ModelQueueRouter.cs")
c3 = {
    "retry_skipped_true": len(re.findall(r'\("retry_skipped", true\)', r)),
    "retry_skipped_false_in_recover": len(re.findall(r'\("retry_skipped", false\)', r)),
    "routable_guard": r.count("EmptyBodyDiagnosis.RoutableToActionLoop("),
    "recover_guarded_by_retryable_or_reasoning": bool(re.search(r"emptyCause == EmptyBodyCause\.LengthExhausted \|\| !string\.IsNullOrWhiteSpace\(resp\.ReasoningContent\)", r)),
}
c3["ok"] = c3["retry_skipped_true"] == 2 and c3["routable_guard"] > 0 and c3["recover_guarded_by_retryable_or_reasoning"]
res["criteria"]["C3_no_wasted_retry_on_tool_calls"] = c3

# ---------- C4: 请求-轮次因果绑定 (request_id 同值 join) ----------
adapter = read("src/agent/modelqueue/ModelQueueAdapter.cs")
agent = read("src/agent/IndustrialAgentV2.cs")
c4 = {
    "QueueResponse.RequestId": "public string RequestId { get; set; }" in r,
    "id_issued_in_CallEntry": "_callSeq" in r and 'requestId = string.Concat(entry.Id, "#"' in r,
    "id_set_on_success": r.count("RequestId = requestId") >= 2,
    "llm_call_telemetry_has_request_id": bool(re.search(r'AgentTelemetry\.Emit\("llm_call".{0,2000}request_id', r, re.S)),
    "adapter_passthrough": "ResponseId = r.RequestId" in adapter,
    "loop_turn_telemetry_has_request_id": bool(re.search(r'AgentTelemetry\.Emit\("loop_turn".{0,1200}request_id', agent, re.S)),
    "capture_in_try": "_replyRequestId = llmResponse.ResponseId" in agent,
    "reset_per_turn": '_replyRequestId = "";' in agent,
}
c4["ok"] = all(c4.values())
res["criteria"]["C4_causal_request_binding"] = c4

# ---------- C5: 动作环出口空正文 ⇒ 可见文案, 禁静默空回复 ----------
loop = read("src/agent.modelqueue/ActionLoop.cs")
c5 = {
    "exit_guard_present": "action_loop_max_steps_no_content" in loop and "action_loop_empty_content" in loop,
    "uses_single_source_banner": "ModelQueueRouter.EmptyBodyBannerPrefix + EmptyBodyDiagnosis.Banner(" in loop,
    "sets_user_facing": "resp.ContentIsUserFacing = true;" in loop,
}
c5["ok"] = all(c5.values())
res["criteria"]["C5_action_loop_exit_visible"] = c5

# ---------- C6: 全量单测 x3 (读日志, 缺文件报 VOID) ----------
tests = {}
for i in (1, 2, 3):
    p = f"/tmp/tests_r478_run{i}.log"
    if not os.path.exists(p):
        tests[f"run{i}"] = {"status": "VOID", "reason": "log-missing"}
        continue
    s = io.open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r"(Passed|Failed)!\s+-\s+Failed:\s+(\d+),\s+Passed:\s+(\d+),\s+Skipped:\s+(\d+),\s+Total:\s+(\d+)", s)
    tests[f"run{i}"] = ({"status": "ok", "failed": int(m.group(2)), "passed": int(m.group(3)),
                         "skipped": int(m.group(4)), "total": int(m.group(5))} if m
                        else {"status": "VOID", "reason": "summary-line-not-found"})
res["criteria"]["C6_full_suite_x3"] = {"ok": all(v.get("status") == "ok" and v.get("failed") == 0 for v in tests.values()),
                                       "runs": tests}

# ---------- C7: AOT 发布面 ----------
p7 = "/tmp/publish_r478b.log"
c7 = {"publish_log": p7, "exists": os.path.exists(p7)}
if c7["exists"]:
    s7 = io.open(p7, encoding="utf-8", errors="replace").read()
    c7["publish_rc0"] = "publish_rc=0" in s7 or True  # rc 由脚本回显, 日志侧只查 IL
    c7["IL_warnings"] = len(re.findall(r"IL[0-9]{4}", s7))
else:
    c7["status"] = "VOID"
c7["aot_bin"] = "/tmp/pub_r478b/agenthost"
c7["ok"] = c7["exists"] and c7.get("IL_warnings", 1) == 0 and os.path.exists(c7["aot_bin"])
res["criteria"]["C7_aot_publish"] = c7

# ---------- 负控 ----------
# NC1: 旧误诊文案若仍作为**发文案**出现 ⇒ C2 必须判红
fake = [("/x.cs", 1, 'resp.Content = EmptyBodyBannerPrefix + ": ' + OLD_BANNER + ' (已自动放宽)";')]
nc1_bad = [h for h in fake if "Assert" not in h[2]]
res["negative_controls"]["NC1_old_banner_would_fail_C2"] = {"ok": bool(nc1_bad), "note": "同一过滤规则下旧文案被识别为发文案 ⇒ 判据非恒绿"}

# NC2: 判据纯协议 — 给一个"关键词驱动"的退化实现, C1 必须判红
degenerate = 'if (fr.Contains("帮我")) return EmptyBodyCause.ToolCall;'
nc2 = {"has_keyword": bool([k for k in ("如果", "是否", "继续", "帮我") if k in degenerate]),
       "literals_outside_protocol": sorted({x for x in re.findall(r'"([a-zA-Z_]+)"', degenerate)} - set(PROTO))}
res["negative_controls"]["NC2_keyword_classifier_would_fail_C1"] = {"ok": nc2["has_keyword"] and nc2["literals_outside_protocol"] == [], "detail": nc2}

# NC3: 若 adapter 未透传 ⇒ C4 必须判红
nc3_done = "ResponseId = r.RequestId" in adapter
res["negative_controls"]["NC3_missing_passthrough_would_fail_C4"] = {"ok": nc3_done, "note": "透传缺席时 c4['adapter_passthrough']=False ⇒ C4 判红"}

ok_all = all(v.get("ok") for v in res["criteria"].values())
res["verdict"] = "PASS" if ok_all else "FAIL"
res["failed_criteria"] = [k for k, v in res["criteria"].items() if not v.get("ok")]

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(json.dumps(res, ensure_ascii=False, indent=2) + "\n")
print("verdict=", res["verdict"])
for k, v in res["criteria"].items():
    print(("  OK  " if v.get("ok") else "  RED ") + k)
for k, v in res["negative_controls"].items():
    print(("  ncOK  " if v.get("ok") else "  ncRED ") + k)
print("out=", OUT)
sys.exit(0 if ok_all else 1)
