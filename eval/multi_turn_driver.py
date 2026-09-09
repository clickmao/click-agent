#!/usr/bin/env python3
"""v0.13.3 R268 — 多轮长对话 driver: 10 轮 repl 会话, 每轮注入材料, 观测压缩/上下文增长。
用法: python3 eval/multi_turn_driver.py <round_label>"""
import json, glob, os, subprocess, sys, time

ROUND_LABEL = sys.argv[1] if len(sys.argv) > 1 else "mt-test"
TURNS = 10

# 每轮材料 (递增注入 — 模拟长任务): 事实 + 填充
def turn_input(i):
    fact = f"第{i}轮关键事实: 项目{i}的负责人是{i}号工程师, 截止日期 2026-09-{10+i}, 数量 {100*i} 件, 编号 SN-{7000+i}。"
    filler = "相关背景: 例行巡检正常。班车时刻见公告栏。库存盘点顺利推进。" * 30
    return fact + filler + f"\n请记录以上第{i}轮要点并简短确认。"

env = dict(os.environ)
env["AGENTFRAMEWORK_LOCAL_DISABLED"] = "1"
env.setdefault("AGENTFRAMEWORK_BGE_MODEL", os.path.expanduser("~/.agentframework/models/bge-q8.gguf"))
bin_path = "./src/agent.host/bin/Release/net10.0/agenthost"
# R268 修正: 无参 = smoke 模式 (跑完即退 code 0) — repl 需至少一个非 smoke 参数 (--log 空路径不可, 用 --log 临时文件):
import tempfile
_log_tmp = tempfile.NamedTemporaryFile(suffix=".log", delete=False)
_log_tmp.close()
repl_args = [bin_path, "--log", _log_tmp.name]
p = subprocess.Popen(repl_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.DEVNULL, text=True, env=env, cwd=".")
# 跳过 banner (等首个提示输出超时保护 — 改为直接喂, 面板容错)
results = []
try:
    for i in range(1, TURNS + 1):
        msg = turn_input(i)
        p.stdin.write(msg + "\n")
        p.stdin.flush()
        time.sleep(1)
        # 读取到下一提示符 (简单策略: 3s 窗口收集)
        # R268 修正: 阻塞 readline 会卡死 (提示符后无更多输出时 readline 永等) —
        # 改时间窗 + 非阻塞轮询 (select):
        import select
        out = []
        deadline = time.time() + 90
        while time.time() < deadline:
            rl, _, _ = select.select([p.stdout], [], [], 2.0)
            if not rl:
                if out and time.time() > deadline - 88:  # 已有输出且 2s 无新行 → 本轮结束
                    break
                continue
            line = p.stdout.readline()
            if not line:
                break
            out.append(line)
        text = "".join(out)
        ok = f"第{i}轮" in text or f"项目{i}" in text or "已" in text
        results.append({"turn": i, "chars_in": len(msg), "ok_hint": ok, "out_head": text[:120]})
        print(f"turn {i}: chars_in={len(msg)} out={len(text)}ch ok_hint={ok}", flush=True)
finally:
    try:
        p.stdin.write("/exit\n"); p.stdin.flush()
        p.wait(timeout=10)
    except Exception:
        p.kill()

# R272: 压缩遥测聚合 — 会话 telemetry jsonl 里抓 compression/compression_sentinel/compression_error/compression_breaker 事件
tel_events = {"compression": 0, "compression_sentinel": 0, "compression_error": 0, "compression_breaker": 0}
tel_details = []
start_ts = time.time() - 3600  # 1h 窗口内的会话文件都扫
for tf in sorted(glob.glob("data/telemetry/*.jsonl"), key=os.path.getmtime)[-3:]:
    if os.path.getmtime(tf) < start_ts:
        continue
    for line in open(tf, encoding="utf-8-sig", errors="replace"):
        try:
            ev = json.loads(line)
        except Exception:
            continue
        name = ev.get("point") or ev.get("event") or ev.get("name") or ""
        if name in tel_events:
            tel_events[name] += 1
            kv = ev.get("kv") or {}
            if name != "compression" or len(tel_details) < 12:
                tel_details.append({k: kv.get(k) for k in ("level", "drift_ok", "semantic", "chars", "state", "reason", "losses") if kv.get(k) is not None})

out_path = f"eval/results/multi-turn-{ROUND_LABEL}.json"
json.dump({"round": ROUND_LABEL, "turns": results, "compression_telemetry": {"events": tel_events, "details": tel_details}}, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"saved → {out_path}")
print("compression telemetry:", tel_events)
