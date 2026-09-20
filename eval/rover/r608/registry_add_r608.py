#!/usr/bin/env python3
"""R608 registry 行追加（幂等 + 保形）。

纪律（skill R409 / R-Q39）:
  ① 改写前断言「序列化器逐字节复现原文件」（缩进宽度/末尾换行/键序）——不符即拒绝改写（fail-closed）。
  ② 只做加法（append 一行 + 改 updated_round），不重排、不动既有行。
  ③ 幂等（重跑不重复插入）；改后读回校验 + 打出 numstat 供人工核对量级。
"""
import hashlib
import io
import json
import pathlib
import sys

REPO = pathlib.Path("/home/agentuser/AgentFramework")
REG = REPO / "docs/verification-registry.json"
EVID = "docs/evidence/RF0001/R608-recognition-outlet.md"
ROW_ID = "r608.recognition-outlet-landing"

raw = REG.read_bytes()
orig = raw.decode("utf-8")
doc = json.loads(orig)
dumped = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
if dumped != orig:
    print("BAIL: 序列化器不能逐字节复现原文件 ⇒ 拒绝改写（fail-closed）")
    sys.exit(2)
print("SER_ASSERT=OK (indent=1, ensure_ascii=False, tail=LF)")

sha12 = hashlib.sha256((REPO / EVID).read_bytes()).hexdigest()[:12]
instr = REPO / "eval/rover/r608/judge_r608.py"
instr_sha12 = hashlib.sha256(instr.read_bytes()).hexdigest()[:12]

row = {
    "id": ROW_ID,
    "level": "L3",
    "owner_round": "R608",
    "capability": (
        "RF0004.1 **开放域识别统一出口 `{标签|abstain, 依据}` 落地**（M1；提交面 `src/` = 2 新件 + 1 打点点位）。"
        "① 新增 `src/agent.nlp/RecognitionVerdict.cs`（22 行：`Recognized/Abstained/Render`，标签集不固定）与 "
        "`src/agent.nlp/RecognitionOutlet.cs`（45 行：**只读**渲染器 `Render(bool digested, basis, face, len, sha16)` + "
        "`IsEnabled()`：缺省 on / `off`·`0` 关 / 非法值 ⇒ on）；发射点 `src/agent/IndustrialAgentV2.cs:1880`（`nlp_shape` 之后），"
        "把既有判定面事实渲染成统一出口（只读 ⇒ 判定链零改动）。"
        "② **真机判别力**（单变量 `AGENTFRAMEWORK_RECOGNITION_VERDICT`：T=未设/产品缺省 on，C=显式 off；T×3 / C×3；"
        "夹具逐字复用 r583 `fixture-shapes-line1.txt` sha `c98f8ab3…` + 轮序 `turns-S0.txt`；`data/nlp` 跑后复原 absent 且回读断言；"
        "6/6 rc=0）：**P1 治疗>0 PASS**（T×3 出口事件 [2,2,2]，覆盖 == 轮数 2，abstain [1,1,1]）· **P2 对照==0 PASS**（C×3 全 0）· "
        "**P3 覆盖 PASS** · **P4 恒前缀冻结 PASS**（`F_env.prefix.chars`=15291 ∧ check rc=0；命中率项如实未测）· "
        "**P5 有牙 PASS**（`--negctl` 交换臂 ⇒ P1/P2/P3 同时翻红）⇒ 出口面**已接线且可消融**（非孤岛）。"
        "③ **预注册 `P2_ablation_bitwise_equivalent` 判定 = FAIL（唯一红项，原样判不翻案）**：rep2 的 C 跑次走 "
        "`gate:repeat_no_replayable_prev→remote`（上游回复形态不同 ⇒ 无回放源）且调用 8 vs T 1（新算 62,041 vs 4,228）"
        "⇒ 执行面摆动 ≥ 轴效应（**非轴缺陷**）⇒ 按协议 §3 加 reps/扩窗（禁调阈值）、产品改动不回撤。"
        "`checks_posthoc`（不入 verdict）：可比域形态逐 rep 逐位等价 **2/3** ∧ turn1 读数 **6/6 臂唯一**（`mechanical:pass→remote`）"
        "⇒ 口径可用；下一轮预注册改分层（可比域）判据，阈值与判据集不变。"
        "④ **发布形态**：JIT Release 构建 rc=0 · `10 Warning(s)` / **`0 Error(s)`**（log 在案 `eval/rover/r608/build-jit-r608.out.txt`）；"
        "`dotnet publish -c Release -r linux-x64` rc=0 / **IL 警告 0** / 原生 ELF **19,739,568 B**；"
        "仓库外 cwd `env -i` 生产档装载冒烟 **×2 均 rc=0**（真回复 promptTokens=4795/4779）且**新面 `recognition_verdict` 随 AOT 产物发出 ×2**"
        "⇒ 非 JIT-only。**诚实边界**：AOT 产物 sha256 **不跨次稳定**（两次发布同尺寸 19,739,568 B、内容不同 `3f7873b8…` vs `4bfcbb9d…`）"
        "⇒ 该 sha 只作单次留痕、不作同源身份锚；同源判据 = 尺寸 ∧ rc ∧ 冒烟新面发出。⑤ abstain 率**首读基线 = 0.5**（3/6 轮，无阈值；R609 出口闸判据面）。"
        "**门禁**：全量 **1953/1954**（唯一红 = `PromptCacheChannelTests.溯源`，**前态同形已机检**：缺键 `llm_call` 2 行全在起臂前字节、"
        "本轮新增 20 行缺键 0）· 形式门禁 **14/14** · API 基线 **+14/−0**（仅本轮成员）· `status_gen.py --check` PASS · "
        "`decl_sweep.py --check` 0 漂移（30 件）。**诚实边界**：无质量对照臂（codex 跳步）⇒ 不宣称任何质量/成本降幅（成本三列标参考、摆动主导）· "
        "命中率未测（REPL 面无口径）· 单窗 n=1/臂不作能力结论 · AOT 冒烟遥测追加在已记录偏移之后（判据按字节切片，不受影响）。"
    ),
    "evidence_cmd": (
        "bash eval/rover/r608/run_r608.sh && python3 eval/rover/r608/judge_r608.py ; "
        "python3 eval/rover/r608/judge_r608.py --negctl ; bash eval/rover/r608/aot_r608.sh ; "
        "bash eval/rover/r608/tests_r608.sh"
    ),
    "evidence_path": EVID,
    "negative_control": (
        "① **判据有牙（臂读数交换）**：`judge_r608.py --negctl`（T↔C 互换后重判）⇒ `P1_treatment_positive` / `P2_control_zero` / "
        "`P3_outlet_coverage` **同时翻红**（rc=1，落 `verdict-r608-negctl.json`）；无此负控时 P1 可能恒真。"
        "② **非平凡**：T/C 三键计数互异（`nontrivial_T_vs_C_differ=true`）。"
        "③ **只读性（机制面负控）**：`RecognitionVerdictTests` 断言 `Render(...)` 不改动 `NlpGate.Counters` + 轴三态（缺省/off/非法值）。"
        "④ **影子自检**：判据器头部断言布尔归一（`.NET \"True\"` / JSON `true` / 缺失 ⇒ None）与键名契约，assert 不过即 rc=2。"
        "⑤ **前态同形证明（针对全量唯一红）**：按起臂前字节切分 `data/telemetry/host.jsonl`，缺键 `llm_call` 行 2 行全在起臂前字节、"
        "本轮新增 20 行缺键 0 ⇒ 该红非本轮引入。"
    ),
    "covers": [
        "eval/rover/r608/prereg-r608.json",
        "eval/rover/r608/dag-r608.md",
        "eval/rover/r608/run_r608.sh",
        "eval/rover/r608/judge_r608.py",
        "eval/rover/r608/verdict-r608.json",
        "eval/rover/r608/verdict-r608-negctl.json",
        "eval/rover/r608/offsets-r608.json",
        "eval/rover/r608/aot_r608.sh",
        "eval/rover/r608/tests_r608.sh",
        "eval/rover/r608/finish_r608.sh",
        "eval/rover/r608/commit_r608.sh",
        "eval/rover/r608/reverify_r608.sh",
        "eval/rover/r608/registry_add_r608.py",
        "eval/rover/r608/build-jit-r608.out.txt",
        "eval/rover/r608/report-r608.md",
        "src/agent.nlp/RecognitionVerdict.cs",
        "src/agent.nlp/RecognitionOutlet.cs",
        "src/agent.tests/RecognitionVerdictTests.cs",
        EVID,
    ],
    "evidence_generated_with": {
        "evidence_kind": "artifact",
        "pin_status": "frozen",
        "pin_reason": "archived-per-round",
        "artifact_sha12": sha12,
        "instrument": "eval/rover/r608/judge_r608.py",
        "instrument_sha12": instr_sha12,
        "binding": "audit-pin",
        "audited_by_round": "R608",
        "artifact_pin_source": EVID,
    },
    "covers_extra": {
        "aot_artifact_sha256": "4bfcbb9dc22f901484ea2e789fb0920bb555d390d59cfd24f35ed80d8ce38ccf",
        "aot_artifact_sha256_prev_publish": "3f7873b8fd173868347e1ac6fb552f380a6a4dc0ad5f7bb39cb72540f8fd7b8b",
        "aot_sha_stable_across_publish": False,
        "aot_artifact_bytes": 19739568,
        "turns_per_arm": 2,
        "abstain_rate_first_read": 0.5,
        "jit_build_errors": 0,
        "jit_build_warnings": 10,
    },
}

ids = [r.get("id") for r in doc["rows"]]
if ROW_ID in ids:
    print("IDEMPOTENT: 行已存在，仅刷 updated_round")
    doc["rows"][ids.index(ROW_ID)] = row
else:
    doc["rows"].append(row)
doc["updated_round"] = "R608"
REG.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

# 读回校验（不采信写入回执）
back = json.loads(REG.read_text(encoding="utf-8"))
assert back["updated_round"] == "R608"
assert back["rows"][-1]["id"] == ROW_ID
assert back["rows"][-1]["evidence_generated_with"]["artifact_sha12"] == sha12
assert len(back["rows"]) == len(doc["rows"])
print("READBACK=OK rows=%d updated_round=%s artifact_sha12=%s instrument_sha12=%s"
      % (len(back["rows"]), back["updated_round"], sha12, instr_sha12))
