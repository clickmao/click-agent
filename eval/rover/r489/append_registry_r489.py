#!/usr/bin/env python3
"""R489 登记表追加 (机取, 幂等, 逐字节保格式)。

- 读 docs/verification-registry.json (utf-8-sig) → rows + updated_round=R489
- 追加 5 行 (全 L2, owner_round=R489), 每行 evidence_generated_with 由**运行时哈希**机算
- 幂等: 目标 id 已存在 ⇒ 直接判红 (rc=3) 不改文件
- 保格式: json.dumps(..., indent=1, ensure_ascii=False) + 单个尾 LF (R481 已定「有 LF」约定)
- 写前断言: 原 rows 的序列化 == 现盘对应片段 (防静默改行)
"""
import hashlib, io, json, os, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
REG = os.path.join(REPO, "docs", "verification-registry.json")


def sha12(p):
    fp = os.path.join(REPO, p)
    if not os.path.exists(fp):
        sys.exit("缺证据文件 (fail-closed): %s" % p)
    return hashlib.sha256(io.open(fp, "rb").read()).hexdigest()[:12]


EV = {
    1: ("eval/rover/r489/verdict-r489.json", "eval/rover/r489/analyze_r489.py"),
    2: ("eval/rover/r489/attribution-r489.json", "eval/rover/r489/attribute_r489.py"),
    3: ("eval/rover/r489/posthoc-quality-r489.json", "eval/rover/r489/posthoc_quality_r489.py"),
    4: ("eval/rover/r489/teardown-selftest.json", "eval/rover/r489/teardown_assert.py"),
    5: ("eval/rover/r489/verdict-loop-r489.json", "eval/rover/r489/check_loop_r489.py"),
}


def egw(i):
    art, instr = EV[i]
    return {"evidence_kind": "artifact", "pin_status": "frozen", "pin_reason": "archived-per-round",
            "artifact_sha12": sha12(art), "instrument": instr, "instrument_sha12": sha12(instr),
            "binding": "audit-pin", "audited_by_round": "R489"}


ROWS = [
    {
        "id": "r489.arm-stability-repeat3",
        "level": "L2",
        "capability": "**主臂同窗三跑稳定性 (否定单次读数)**: 同一 AOT `e9b86fc9…` / 同一夹具 p12 / 同一 role / 同一窗口, 分母取同窗 B 臂。B=17 调用 85,028 tok; R1=10/49,775 (−41.46%); R2=16/85,718 (**+0.81%**); R3=8/34,726 (−59.16%) ⇒ 三跑极差/中位 **102.45%**。预注册判据: **H1 FAIL** (min ≥30% 不成立, 最差 −0.81%) · **H2 FAIL** (≤0.15 摆动) · **H4 FAIL** (调用极差 8 ≤2 不成立) · **H0 FAIL** (锚漂移 +19.85% vs R488 B) · **H3 PASS** (类别感知质量, 非法模板 0/12, 模板字符数绑源码常量)。⇒ R488 的 −33.28% **降级为单次读数**, 本轮下界 = **−0.81%**, 跨轮一律不相减。",
        "evidence_cmd": "python3 eval/rover/r489/analyze_r489.py --json eval/rover/r489/verdict-r489.json",
        "evidence_path": "eval/rover/r489/verdict-r489.json",
        "negative_control": "`--force-swap` (B 与 R1 的 total 互换) ⇒ H1 必翻红 (实测 rc=1); `--force-degrade` (注入 template_chars_ok=False) ⇒ H3 必翻红 (实测 rc=1); 缺任一 usage 列 ⇒ fail-closed rc=3 (不产半读数)。",
        "covers": ["eval/rover/r489/prereg_r489.json", "eval/rover/r489/analyze_r489.py",
                   "eval/rover/r489/verdict-r489.json", "eval/rover/r489/usage-Aroleb.jsonl",
                   "eval/rover/r489/usage-R1.jsonl", "eval/rover/r489/usage-R2.jsonl",
                   "eval/rover/r489/usage-R3.jsonl"],
        "owner_round": "R489",
        "evidence_generated_with": egw(1),
    },
    {
        "id": "r489.upstream-empty-body-variance",
        "level": "L2",
        "capability": "**方差归因 (post-hoc 单列)**: 调用数 = 远端轮 + **上游空正文(带 tool_calls)调用**。空正文调用 4/4/10/2, 其 token 占比 22.8%/29.4%/**58.8%**/18.8%, `retry_skipped=True` 全真 (R478 修复在位)。本地闸决策**三跑完全一致** (每臂 `local_turn_gate` 12 行, Skip 6 = `gate:skip→local` 4 + `mechanical:repeat→local` 2) ⇒ 摆动**不来自本地通道**。剔除上游空正文后同窗降幅稳定: −46.46% / −46.21% / −57.05%, 调用数三跑同为 **6** (vs B 13, −53.85%) ⇒ 本地通道增益稳定达线, 总口径不稳由上游行为面造成。",
        "evidence_cmd": "python3 eval/rover/r489/attribute_r489.py",
        "evidence_path": "eval/rover/r489/attribution-r489.json",
        "negative_control": "本地闸 Skip 决策三跑一致 (逐臂 6 = 4 ack + 2 复述) 作「非臂内噪声」阳性对照; 空正文计数与 usage 行 `empty_body` 字段**双源交叉** (遥测事件数 == usage 行数); 缺 usage 或 telemetry ⇒ fail-closed。",
        "covers": ["eval/rover/r489/attribute_r489.py", "eval/rover/r489/attribution-r489.json",
                   "eval/rover/r489/tel-Aroleb/host.jsonl", "eval/rover/r489/tel-R1/host.jsonl",
                   "eval/rover/r489/tel-R2/host.jsonl", "eval/rover/r489/tel-R3/host.jsonl"],
        "owner_round": "R489",
        "evidence_generated_with": egw(2),
    },
    {
        "id": "r489.local-skip-template-reword",
        "level": "L2",
        "capability": "**本地确认语文案裁决 + 遥测绑源码**: `ModelQueueRouter.LocalSkipFallback` 由 `收到，继续按当前方向推进，本轮不重新规划。` (21 字, 含**未被任何工作背书的动作声明**) 改为 **`收到。`** (3 字纯确认)。机检: SRC1 模板每字符 ⊂ `LocalGenerationPort.AckFamilyChars` (R434 认可族); SRC2 无动作/承诺词; 四臂 `local_gate_skip_reply.chars` == **源码常量长度** (3) ⇒ 遥测↔源码绑定 (证明被测二进制即此源码)。类别感知质量面: 非法模板 **0/12** (R 臂 4 轮模板全落确认类), 全部 PASS。",
        "evidence_cmd": "python3 eval/rover/r489/posthoc_quality_r489.py",
        "evidence_path": "eval/rover/r489/posthoc-quality-r489.json",
        "negative_control": "类别归属取**产品自身遥测** `local_turn_gate.basis` (非手抄关键词表, R488 版为关键词匹配); `kind=template` 与 `basis=gate:skip→local` 的**配对错位**即判红; 模板字符数 != 源码常量长度即判红 (证明二进制与源码不一致)。",
        "covers": ["eval/rover/r489/posthoc_quality_r489.py", "eval/rover/r489/posthoc-quality-r489.json",
                   "eval/rover/r489/tel-Aroleb/host.jsonl", "eval/rover/r489/tel-R1/host.jsonl",
                   "eval/rover/r489/tel-R2/host.jsonl", "eval/rover/r489/tel-R3/host.jsonl"],
        "owner_round": "R489",
        "evidence_generated_with": egw(3),
    },
    {
        "id": "r489.fixture-teardown-reap",
        "level": "L2",
        "capability": "**夹具 teardown 先收口再断言**: 首跑即捕获真泄漏 —— B 臂 `llama-server` pid 1676110 / RSS **1,781.8 MB** / cwd `rundata-Aroleb`, **非 host 直接子进程** ⇒ 既有 `pkill -P $HOST_PID` 漏杀 (与 R488 收尾泄漏同族)。修法 = 断言前按**命名空间**收口 (`/proc` 逐 pid, 排除自身+全祖先链, TERM→8s→KILL): R1/R2/R3 teardown 全 **clean (procs=0 listeners=0)**; `--selftest` 三例全过 (端口负控 residual / 命名空间负控 residual / 收口端到端 clean+reaped)。",
        "evidence_cmd": "python3 eval/rover/r489/teardown_assert.py --selftest --out eval/rover/r489/teardown-selftest.json",
        "evidence_path": "eval/rover/r489/teardown-selftest.json",
        "negative_control": "`--nc-listener` (占住本臂 api 端口) 与 `--nc-proc` (造带臂名的残留进程) 两例**必红** (实测 verdict=residual); 收口端到端例 = 造真残留 → `--reap` → 复断言 clean 且复检目标进程**非活体** (排除僵尸 Z/X 误判); 一律 `/proc` 扫描, 不用 `pgrep -f` (禁自匹配自杀)。",
        "covers": ["eval/rover/r489/teardown_assert.py", "eval/rover/r489/teardown-selftest.json",
                   "eval/rover/r489/teardown-Aroleb.json", "eval/rover/r489/teardown-R1.json",
                   "eval/rover/r489/teardown-R2.json", "eval/rover/r489/teardown-R3.json"],
        "owner_round": "R489",
        "evidence_generated_with": egw(4),
    },
    {
        "id": "r489.action-loop-empty-body-diff",
        "level": "L2",
        "capability": "**R486 差分夹具在 `ACTION_LOOP=on` 下重跑** (R488 只测了 off 形态): 桩请求数 pre-empty **7** vs post-empty **7** (差 0) ⇒ 预注册 H1「pre 比 post 多 1 次请求」**被证伪**; 阴性对照 plain 模式 pre=post=**1** ✔; post 侧 `llm_call_empty_body` **7/7** `retry_skipped=True`。⇒ 「空正文(带 tool_calls) ⇒ 浪费重试」的差分在 **off 与 on 两种形态下均不复现**, 宣称收窄为「本夹具下两二进制无差异」; 覆盖度由 off-only 扩为 off∧on。",
        "evidence_cmd": "python3 eval/rover/r489/check_loop_r489.py",
        "evidence_path": "eval/rover/r489/verdict-loop-r489.json",
        "negative_control": "plain 模式两二进制同值 (1=1) 作夹具噪声阴性对照 (不同值即判夹具不可信); 判据只用**桩侧真实请求条数** (宿主自述不作判据); 夹具由 `derive_loop_r489.py` 机派生 (8 处替换逐条计数断言 + 残留扫描), 缺任一桩请求文件 ⇒ fail-closed。",
        "covers": ["eval/rover/r489/derive_loop_r489.py", "eval/rover/r489/run_diff_loop_r489.sh",
                   "eval/rover/r489/check_loop_r489.py", "eval/rover/r489/verdict-loop-r489.json",
                   "eval/rover/r489/stub-requests-pre-empty.jsonl", "eval/rover/r489/stub-requests-post-empty.jsonl",
                   "eval/rover/r489/stub-requests-pre-plain.jsonl", "eval/rover/r489/stub-requests-post-plain.jsonl"],
        "owner_round": "R489",
        "evidence_generated_with": egw(5),
    },
]


def main():
    raw = io.open(REG, encoding="utf-8-sig").read()
    doc = json.loads(raw)
    ids = {r["id"] for r in doc["rows"]}
    dup = [r["id"] for r in ROWS if r["id"] in ids]
    if dup:
        sys.exit("ABORT (幂等闸): 已存在 id %s ⇒ 不改文件" % dup)
    # 保格式前置断言: 现盘文本必须能被本序列化器**逐字节复现** (否则改文件会引入无关 churn)
    if raw != json.dumps(doc, ensure_ascii=False, indent=1) + "\n":
        sys.exit("ABORT: 现盘序列化复现不一致 (序列化器与文件不同源) ⇒ 拒写")
    old_rows = doc["rows"]
    doc["rows"] = old_rows + ROWS
    doc["updated_round"] = "R489"
    text = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
    io.open(REG, "w", encoding="utf-8").write(text)
    back = json.loads(io.open(REG, encoding="utf-8-sig").read())
    assert back["updated_round"] == "R489" and len(back["rows"]) == len(old_rows) + len(ROWS)
    assert [r["id"] for r in back["rows"][:len(old_rows)]] == [r["id"] for r in old_rows]
    assert text.endswith("}\n") and not text.startswith("\ufeff")
    print("[registry] rows %d → %d; updated_round=%s; 前置行逐 id 相同 ✔" % (len(old_rows), len(back["rows"]), back["updated_round"]))
    for r in ROWS:
        print("   +", r["id"], r["level"], r["evidence_generated_with"]["artifact_sha12"])


if __name__ == "__main__":
    main()
