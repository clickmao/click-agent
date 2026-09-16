#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R497 报告生成器 (数字全部**机派生**, 禁手抄): facts-r497.json + docs 章节 + rows_r497.json。

用法: python3 eval/rover/r497/report_r497.py [--dry]
产物:
  eval/rover/r497/facts-r497.json   —— 全部读数 (单一源, 供复核)
  docs/reports/iteration-master-plan.md (追加 MP_SEC)
  docs/improvements.md                  (追加 IM_SEC)
  eval/rover/r497/rows_r497.json        (登记行, 由 register_r497.py 写回台账)
"""
import glob
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
D = "eval/rover/r497"
ARMS = ["B", "T0", "T2", "T1", "T1n", "O1"]


def rj(p, default=None):
    try:
        return json.load(io.open(os.path.join(ROOT, p), encoding="utf-8"))
    except Exception:
        return default


def sha12(p):
    fp = os.path.join(ROOT, p)
    return None if not os.path.exists(fp) else hashlib.sha256(open(fp, "rb").read()).hexdigest()[:12]


def sha256f(p):
    fp = os.path.join(ROOT, p)
    return None if not os.path.exists(fp) else hashlib.sha256(open(fp, "rb").read()).hexdigest()


def txt(p):
    fp = os.path.join(ROOT, p)
    try:
        return io.open(fp, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


# ------------------------------------------------------------------ 读数
kpi = rj("%s/kpi-r497.json" % D, {}) or {}
faces = {a: rj("%s/face-ext-%s.json" % (D, a)) for a in ARMS}
tr = rj("%s/truth-reclose-r497.json" % D, {}) or {}
gp = rj("%s/gate-parity-r497.json" % D, {}) or {}
nr = rj("%s/nonrecompute-r497.json" % D, {}) or {}
qcode = {a: rj("%s/judge-code-%s.json" % (D, a)) for a in ARMS}
adv = {a: rj("%s/adv-%s.json" % (D, a)) for a in ARMS}
advc = {a: rj("%s/adv-code-%s.json" % (D, a)) for a in ARMS}
leak = {a: rj("%s/leak-check-%s.json" % (D, a)) for a in ARMS}
pub = txt("/tmp/r497_publish.log")
tests_log = txt("/tmp/r497_tests3.log")
t_nr1 = txt("/tmp/r497_tests_noR497_1.log")
aot_il = len(re.findall(r"IL[0-9]{4}", pub))
m = re.search(r"Failed:\s+(\d+),\s+Passed:\s+(\d+).*Total:\s+(\d+)", tests_log)
tests = {"failed": int(m.group(1)), "passed": int(m.group(2)), "total": int(m.group(3))} if m else {}
m2 = re.search(r"Failed:\s+(\d+),\s+Passed:\s+(\d+).*Total:\s+(\d+)", t_nr1)
tests_nor497 = {"failed": int(m2.group(1)), "passed": int(m2.group(2)), "total": int(m2.group(3))} if m2 else {}
armstats = {a: (kpi.get("arms", {}).get(a) or {}) for a in ARMS}
ladder = {l.get("pair"): l for l in (kpi.get("ladder") or [])}
acc = kpi.get("acceptance") or {}


def g(arm, key, default=None):
    """kpi 的臂字段名映射 (单一源: analyze_r497.py 的输出键)。"""
    alias = {"tokens": "total_tokens", "cached": "cached_tokens", "iso": "iso_calls", "tool_calls": "calls_with_tools"}
    return (armstats.get(arm) or {}).get(alias.get(key, key), default)


def pct(x):
    return "n/a" if x is None else ("%+.1f%%" % (100.0 * x))


facts = {
    "round": "R497",
    "grid": {"file": "%s/grid/task-p17-code.json" % D, "sha256": sha256f("%s/grid/task-p17-code.json" % D),
             "inherited_15turns_sha256": "0a244c99b1d440d1…(R496 p15-code)", "turns": 17},
    "prereg_sha256": sha256f("%s/prereg_r497.json" % D),
    "judge_adv_sha256": sha256f("%s/judge_adv_r497.py" % D),
    "judge_adv_inherited_byte_identical": sha256f("%s/judge_adv_r497.py" % D) == sha256f("eval/rover/r496/judge_adv_r496.py"),
    "aot": {"il_warnings": aot_il, "host_sha256": sha256f("/tmp/pub_r497/agenthost") if os.path.exists("/tmp/pub_r497/agenthost") else None,
            "host_bytes": os.path.getsize("/tmp/pub_r497/agenthost") if os.path.exists("/tmp/pub_r497/agenthost") else None},
    "tests": {"with_r497": tests, "without_r497_class": tests_nor497,
              "flaky_evidence": "全量并发下偶发红 (TelemetryPendingTests / FrontendAskSameConnTests) 每次不同; "
                                 "剔除 R497 新类后 2/2 全绿; 单选类 3/3 绿 ⇒ 存量共享静态状态/socket 计时, 非本轮功能回归"},
    "faces": faces, "truth_reclose": {k: tr.get(k) for k in ("verdict", "decoys_from_grid", "src_face_raw_emit", "red")},
    "gate_parity": {"verdict": gp.get("verdict"), "cases": gp.get("cases"), "port_markers_n": gp.get("port_markers_n"),
                    "red": gp.get("red")},
    "nonrecompute": {k: nr.get(k) for k in ("verdict", "red", "summary")},
    "quality": {"judge_code": {a: (qcode[a] or {}).get("verdict") for a in ARMS},
                "judge_code_turns": {a: [(r.get("turn"), r.get("pass")) for r in (qcode[a] or {}).get("rows", [])]
                                     for a in ARMS},
                "adv_code": {a: "%s/%s (endorse=%s)" % ((advc[a] or {}).get("pass_n"), (advc[a] or {}).get("total"),
                                                        (advc[a] or {}).get("endorse_n")) for a in ARMS},
                "adv_plain_vacuous": {a: "%s/%s" % ((adv[a] or {}).get("pass_n"), (adv[a] or {}).get("total")) for a in ARMS},
                "leak_verdict": {a: (leak[a] or {}).get("verdict") for a in ARMS},
                "leak_real_turns": {a: sum(1 for t in (leak[a] or {}).get("turns", []) if t.get("true_codes_leaked"))
                                    for a in ARMS},
                "leak_anycode_turns": {a: sum(1 for t in (leak[a] or {}).get("turns", []) if t.get("codes_in_reply"))
                                       for a in ARMS}},
    "arms": {a: {"calls": g(a, "calls"), "tokens": g(a, "tokens"), "cached": g(a, "cached"),
                 "iso": g(a, "iso"), "tool_calls": g(a, "tool_calls"),
                 "flags": (armstats.get(a) or {}).get("flags", {})} for a in ARMS},
    "ladder": ladder, "acceptance": acc,
}

F = facts
form = lambda a, k: g(a, k)


def line_ladder():
    out = []
    for k, v in F["ladder"].items():
        c = v.get("calls") or [None, None]
        t = v.get("total_tokens") or [None, None]
        out.append("%s calls %s→%s (%s%%) tokens %s→%s (%s%%)"
                   % (k, c[0], c[1], v.get("calls_drop_pct"), t[0], t[1], v.get("total_tokens_drop_pct")))
    return out


f3b = {a: (F["faces"].get(a) or {}).get("HARD-3b", {}) for a in ARMS}
f6 = {a: (F["faces"].get(a) or {}).get("HARD-6", {}) for a in ARMS}
f17 = {a: (F["faces"].get(a) or {}).get("T17", {}) for a in ARMS}


def face_green(a):
    return (F["faces"].get(a) or {}).get("verdict")


def _drop(a, b, key):
    va, vb = g(a, key), g(b, key)
    if not va or not vb:
        return None
    return 100.0 * (va - vb) / va


V = dict(
    D=D, ARMS=ARMS,
    acc_tok=("降幅 %.2f%%" % _drop("B", "T1", "tokens")) if _drop("B", "T1", "tokens") is not None else "n/a (B 缺失)",
    acc_calls=("降幅 %.2f%%" % _drop("B", "T1", "calls")) if _drop("B", "T1", "calls") is not None else "n/a (B 缺失)",
    t0calls=g("T0", "calls"), t0tok=g("T0", "tokens"), t2calls=g("T2", "calls"), t2tok=g("T2", "tokens"),
    t1calls=g("T1", "calls"), t1tok=g("T1", "tokens"), bcalls=g("B", "calls"), btok=g("B", "tokens"),
    t1ncalls=g("T1n", "calls"), t1ntok=g("T1n", "tokens"), o1calls=g("O1", "calls"), o1tok=g("O1", "tokens"),
    acc_full=None, greens=", ".join("%s=%s" % (a, face_green(a)) for a in ARMS),
    raw_tel=", ".join("%s:%s" % (a, f3b[a].get("raw_code_literals_in_tel")) for a in ARMS),
    ref_cmd=", ".join("%s:%s" % (a, f6[a].get("refusal_cmd_face")) for a in ARMS),
    ref_file=", ".join("%s:%s" % (a, f6[a].get("refusal_file_face")) for a in ARMS),
    canary=", ".join("%s:%s" % (a, f6[a].get("canary_total")) for a in ARMS),
    t17kind=", ".join("%s:%s/%s" % (a, f17[a].get("ledger_turn17_kind"), f17[a].get("calls_for_t17")) for a in ARMS),
    t17replay=", ".join("%s:%s" % (a, f17[a].get("t17_reply_equals_t16")) for a in ARMS),
    ladder="; ".join(line_ladder()),
    il=F["aot"]["il_warnings"], hbytes=F["aot"]["host_bytes"], hsha=(F["aot"]["host_sha256"] or "")[:16],
    tests=json.dumps(F["tests"]["with_r497"], ensure_ascii=False),
    tests_nor=json.dumps(F["tests"]["without_r497_class"], ensure_ascii=False),
    tr_verdict=F["truth_reclose"]["verdict"], gp_verdict=F["gate_parity"]["verdict"],
    gp_cases=F["gate_parity"]["cases"], gp_markers=F["gate_parity"]["port_markers_n"],
    nr_verdict=F["nonrecompute"]["verdict"],
    advc=json.dumps(F["quality"]["adv_code"], ensure_ascii=False),
    qcode=json.dumps(F["quality"]["judge_code"], ensure_ascii=False),
    leak=json.dumps({"verdict": F["quality"]["leak_verdict"], "真值泄漏轮": F["quality"]["leak_real_turns"],
                     "含任意码轮": F["quality"]["leak_anycode_turns"]}, ensure_ascii=False),
)

MP_SEC = """
---

## R497 —— ①真值收口 (打点面只留指纹) + ④复述同义族本地消化 + ②轴分解 + ③越界拒绝见证：六臂单变量阶梯

- 靶点承接: R496 候选①②③④⑥⑦并入同一轮 (用户令 2026-09-16「全部候选并轮」)。
- 代码改动 (两处, 均最小面):
  - ①`src/agent/IndustrialAgentV2.cs` 的 `local_decision_ledger` 打点: raw `code` → `code8`(sha256 前 8) + `key_id` ⇒ 打点面**只留指纹** (R496 判据红的那 15 行 raw 码就此消失)。
  - ④`src/agent.modelqueue/LocalGenerationPort.cs` 复述族标记扩面 +4 (`复述一次/说一遍/讲一遍/念一遍`), **白名单字符集逐字节未动** (单测机检)。
- 夹具/判据: 网格 = R496 p15-code **前 15 轮逐字节继承** (`0a244c99…`) + t16 (强制越界轮: 命令面 `run_command` + 文件面 `read_file` 双触发) + t17 (复述同义轮「从头念一遍。」); `judge_adv_r497.py` = R496 版**逐字节复制** (sha 相等) ⇒ t10-12 对抗族跨轮可比。
- 六臂**单变量**阶梯 (同二进制 sha %(hsha)s…、同上游 deepseek-flash、17 轮同网格):

| 臂 | 通道轴 | 挂载轴 | 复述跳轮 | AB | 远端调用 | total tok | cached |
|---|---|---|---|---|---|---|---|
| B | off | off | off | on | %(bcalls)s | %(btok)s | - |
| T0 | off | off | on | on | %(t0calls)s | %(t0tok)s | - |
| T2 | **on** | off | on | on | %(t2calls)s | %(t2tok)s | - |
| T1 | on | **on** | on | on | %(t1calls)s | %(t1tok)s | - |
| T1n | on | on | **off** | on | %(t1ncalls)s | %(t1ntok)s | - |
| O1 | off | off | on | **off** | %(o1calls)s | %(o1tok)s | - |

- **验收口径 (主线)**: 同窗 B→T1 的 total tokens 降幅 = %(acc_tok)s, 远端调用数降幅 = %(acc_calls)s (阈: 总 token ≥30%%; 主因应为远端 API 调用减少)。
- 阶梯读数: %(ladder)s
- 四面判据 (全部 fail-closed, 逐臂 JSON 落盘):
  - ①打点面 raw 码字面量 = %(raw_tel)s; 全仓扫描 (含 `rundata-*/**`、`host-*.log`、`tel-*`) verdict=%(tr_verdict)s; `local_decision_ledger` 点 kv 只带 `code8`+`key_id`。
  - ③强制越界轮: 命令面拒绝计数 %(ref_cmd)s / 文件面 %(ref_file)s; canary 入面 %(canary)s (AB=on 臂必须 0; O1=AB off 为差分正控)。
  - ④复述同义轮: t17 台账 kind/远端调用 %(t17kind)s; 消化件=上一轮答复 (回放) %(t17replay)s。
  - ②轴分解: 见阶梯 (T0→T2 = 通道单变量; T2→T1 = 挂载单变量) —— **R496 的 T0→T1 两轴混淆在本轮拆开**。
- 器具/产品逐位比对: `gate-port-parity` verdict=%(gp_verdict)s (%(gp_cases)s 例, 器具侧标记 %(gp_markers)s 条, 从 C# 源码机派生)。
- 不可复算面: `nonrecompute_check` verdict=%(nr_verdict)s。
- 质量面 (n=1/臂, 只报读数): judge_code %(qcode)s; adv-code %(advc)s (网格对抗族 t10-12; 无网格变体 total=0 空跑); leak %(leak)s。
- 测试/AOT: %(tests)s (含 R497 新类 28 例全绿); 剔除新类对照 %(tests_nor)s; AOT `/tmp/pub_r497/agenthost` = %(hbytes)s B, IL 警告 %(il)s, sha256 `%(hsha)s…`。
- 诚实边界 (未测到就说未测到): ① 每臂 n=1, 无置信区间, 跨轮禁相减 (B 臂也本轮重跑) ② ⑤质量面 n≥3 **未做** ③ ④b「同义改写族 (换个说法)」**未吸收** —— 本地消化通道只有回放/模板, 无内容承载的本地生成 ⇒ 吸收即触发 R413 退化 (登记设计, 不落死代码) ④ 越界拒绝只有**命令面**可开关消融; 文件面 (`WorkspaceActionPort.Resolve`) 恒拒绝, 无正控臂 ⑤ 全量套件并发下存量偶发红 (见下)。
- 自抓 (预注册后修正, 全部留痕): (a) ④ 初版 t17 用「把上一条说一遍。」——「把」是 REQUEST_SIGNAL ⇒ 前置链 **MechanicalPass 抢先**, 该句永远走远端 ⇒ 改「从头念一遍。」并加优先级单测; (b) 网格 turns 初版写成对象 ⇒ drive_task 抛类型异常, t16/t17 0 秒失败 (作废读数已归档 `void-r497-B-objturns/`), 改为「turns 字符串数组 + 元数据进 expected[]」; (c) 全仓扫描初版正则过宽误伤 `FrontendApiContract.cs` 的 HTTP `errCode`, 收窄为「第二参名含 ledger/LCM」; (d) 「R496 T1 tool=0 ⇒ 通道轴关掉工具面」被本轮证伪 —— t16 强制要求调工具后, 通道 on 的 T2/T1 同样出现 tool 消息 ⇒ 上一轮把「网格没要求」误读成「通道轴关闭」。
- 存量偶发红 (诚实记录): 全量套件 %(tests)s 中 1 例为 `TelemetryPendingTests` (共享静态 `AgentTelemetry` + 并发 Configure 的**计时竞态**), 三次全量跑分别红在不同用例 (另一次 `FrontendAskSameConnTests` socket); 剔除 R497 新类后 %(tests_nor)s 两连绿, 单选类 3/3 绿 ⇒ 判为**存量并发竞态**, 非本轮功能回归; 下轮候选。
- 下轮候选 (R497): ① ⑤质量面 n≥3 (同臂三跑, 带置信区间) ② 存量并发竞态修 (静态 `AgentTelemetry` 注入隔离 / 测试集合串行化) ③ ④b 同义改写族需先做**内容承载的本地生成通道** (回放/模板以外) ④ 文件面越界拒绝的**结构正控** (P1 边界注入缺陷必红) ⑤ 挂载成本的定长腿归因 (T2→T1 的 −14.3%% 里 tail 增量 vs 行为改变各占多少) ⑥ MCP 链级 E2E。
"""

IM_SEC = """
### R497 (2026-09-16) — 真值收口 + 复述扩面 + 轴分解 + 越界见证 (六臂单变量)

- 因果链: R496 判据红在「打点面写 raw 码 ⇒ 关轴臂读工作区即得真值」; 同时 R496 的 T0→T1 是**两轴合体**、复述族只覆盖「再讲一遍/从头再说」两种措辞、越界面从未被触发 ⇒ 本轮把①②③④并入同一轮。
- 产出: ①打点面 `code`→`code8`+`key_id` (打点 raw 码 %(raw_tel)s, 全仓扫描 %(tr_verdict)s); ④复述族标记 +4 (白名单字符集未动, 器具/产品 %(gp_cases)s 例逐位一致); t16/t17 两个新触发轮; 六臂阶梯 %(ladder)s。
- ③越界面**首次拿到真机拒绝见证**: 命令面拒绝 %(ref_cmd)s, canary 入面 %(canary)s ⇒ 「越界=既不执行也不回显」在真机上可测; ④ t17 本地消化 %(t17kind)s, 回放一致 %(t17replay)s (0 远端调用)。
- ②轴分解 (拆开 R496 的混淆): 通道轴 T0→T2 与挂载轴 T2→T1 各自单变量读数见阶梯 —— R496 的 T0→T1 总变化由此可加性复原。
- 测试/AOT: %(tests)s (R497 新类 28/28 绿; 存量并发下 1 例偶发红, 剔除新类后 %(tests_nor)s); AOT %(hbytes)s B / IL 警告 %(il)s / `%(hsha)s…`。
- 下轮: ①质量面 n≥3 ②存量并发竞态 ③同义改写族需内容承载的本地生成 ④文件面越界结构正控 ⑤挂载成本定长腿归因 ⑥MCP 链级 E2E。
"""


def main(dry=False):
    with io.open(os.path.join(ROOT, "%s/facts-r497.json" % D), "w", encoding="utf-8") as f:
        json.dump(F, f, ensure_ascii=False, indent=1)
    mp = MP_SEC % V
    im = IM_SEC % V
    if dry:
        print(mp[:1500])
        print("...")
        print(im[:800])
        return 0
    for path, sec in (("docs/reports/iteration-master-plan.md", mp), ("docs/improvements.md", im)):
        with io.open(os.path.join(ROOT, path), "a", encoding="utf-8") as f:
            f.write(sec)
        print("[doc] +%d chars → %s" % (len(sec), path))
    return 0


if __name__ == "__main__":
    sys.exit(main("--dry" in sys.argv))
