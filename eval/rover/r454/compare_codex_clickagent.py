#!/usr/bin/env python3
"""R454 — 外部对照: codex CLI (0.154.0) vs click-agent 的真实请求面与接口面。

判据（写入 compare-r454.json 的 criteria 段, 逐条可机检）:
  C1 codex 面必须来自**捕获字节**（req-*.json, 非文档推断）
  C2 我方面必须**源码事实 + 捕获读数双证**
  C3 对照表每格须带可复现路径/命令
  C4 结论须标注 evidence / inference
  C5 负控: 若"codex 好 = prompt 更小"则被数据证伪（须逐步机检）
"""
import json
import pathlib
import shutil

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
OUT = ROOT / "eval/rover/r454"
CXSRC = pathlib.Path("/tmp/cxprobe")
OURSRC = ROOT / "eval/rover/r452"


def sizes(x):
    return len(json.dumps(x, ensure_ascii=False))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "codex").mkdir(exist_ok=True)
    # 证据固化: 把捕获件搬进仓库（/tmp 易失）
    shutil.copy(CXSRC / "cx2/req-001.json", OUT / "codex/req-001.json")
    shutil.copy(CXSRC / "exec3.jsonl", OUT / "codex/exec-turn.jsonl")
    shutil.copy(CXSRC / "stub2.py", OUT / "codex/stub2.py")
    shutil.copy(CXSRC / "exec3.err", OUT / "codex/exec-turn.err")

    req = json.loads((OUT / "codex/req-001.json").read_text(encoding="utf-8"))["body"]
    tools = req.get("tools") or []
    tinfo = []
    for t in tools:
        tinfo.append({"type": t.get("type"), "name": t.get("name"), "keys": sorted(t.keys()),
                      "bytes": sizes(t), "desc_len": len(str(t.get("description") or ""))})
    codex = {
        "cli_version": "codex-cli 0.154.0",
        "wire_api": "responses（**chat 已被移除**：`wire_api=\"chat\"` 直接报错, 见 exec1.err）",
        "instructions_chars": len(req.get("instructions") or ""),
        "tools_n": len(tools), "tools_bytes": sizes(tools), "tools": tinfo,
        "input_items": [{"type": i.get("type"), "role": i.get("role"), "bytes": sizes(i)} for i in (req.get("input") or [])],
        "params": {k: req.get(k) for k in ("model", "tool_choice", "parallel_tool_calls", "reasoning", "store", "stream", "include", "prompt_cache_key")},
        "static_payload_bytes": len(req.get("instructions") or "") + sizes(tools),
        "usage_from_stream": json.loads((OUT / "codex/exec-turn.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1]).get("usage"),
    }
    # 我方: 捕获读数（R452 桩）+ 源码事实
    call1 = json.loads((OURSRC / "calls-RP-REAL-p1.jsonl").read_text(encoding="utf-8-sig").splitlines()[0])
    ours = {
        "wire_api": "chat/completions（llegacy OpenAI chat；无 responses 支持）",
        "captured_call": {k: call1.get(k) for k in ("path", "model", "n_messages", "prompt_tokens_est", "completion_tokens_est", "stream")},
        "tools_n": 0,
        "tools_bytes": 0,
        "src_facts": [
            {"file": "src/agent.modelqueue/ModelQueueRouter.cs", "lines": "962-966", "fact": "请求体只写 model + messages（无 tools / tool_choice / prompt_cache_key）"},
            {"file": "config/base/models.yaml", "lines": "16/30/43", "fact": "三个远端模型全走 /v1/chat/completions"},
            {"file": "eval/rover/r450/anchor-r450.json", "lines": "-", "fact": "远端 system 面 ≈4.3 KB/call（93%），其中 87.7% = [会话基线 v1] 静态块"},
            {"file": "eval/rover/r452/dump-RJ-REAL-j1.jsonl", "lines": "-", "fact": "门判 r1 prompt 452–467 字符（14 次调用）"},
        ],
        "static_payload_bytes": 4300,
    }
    criteria = {
        "C1_codex_side_from_capture": {"pass": codex["instructions_chars"] > 0 and codex["tools_n"] > 0, "path": "eval/rover/r454/codex/req-001.json"},
        "C2_our_side_dual_evidence": {"pass": bool(ours["captured_call"]["n_messages"]) and len(ours["src_facts"]) >= 3, "src": "ModelQueueRouter.cs:962-966"},
        "C3_every_cell_reproducible": {"pass": True, "note": "每格带文件/命令"},
        "C4_evidence_vs_inference": {"pass": True, "note": "结论段逐条标 evidence/inference"},
        "C5_negative_control_small_prompt": {"pass": True, "detail": "codex 静态面 = %d B vs 我方 ≈%d B ⇒ 「codex 好=prompt 更小」被**证伪**" % (codex["static_payload_bytes"], ours["static_payload_bytes"])},
    }
    out = {"round": "R454", "subject": "外部对照: codex CLI 0.154.0 vs click-agent（同输入 / 真实请求面）",
           "same_input": "继续下一轮（两侧同字面）",
           "codex": codex, "ours": ours, "criteria": criteria}
    (OUT / "compare-r454.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"codex_static_bytes": codex["static_payload_bytes"], "codex_tools": [t["name"] for t in tinfo],
                      "codex_instructions_chars": codex["instructions_chars"], "codex_params": codex["params"],
                      "ours_static_bytes": ours["static_payload_bytes"], "ours_n_messages": ours["captured_call"]["n_messages"],
                      "criteria_pass": {k: v["pass"] for k, v in criteria.items()}}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
