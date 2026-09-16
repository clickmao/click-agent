#!/usr/bin/env python3
"""R499 登记器: 把本轮三条能力写进 docs/verification-registry.json (幂等: 先删 r499.* 旧行再加)。

用法: python3 eval/rover/r499/register_r499.py [--apply]
不带 --apply 时只打印将要写入的行 (dry-run)。读入一律 utf-8-sig。

**R2e/R2f 契约**: `evidence_generated_with` 必须由 bind_evidence.py --only ... --round R499 --apply 派生,
本脚本不写该字段 (evidence_path 前缀 eval/ 的行交器具填)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_concurrent_touch import guard_or_die, verify_or_die  # noqa: E402

REG = Path("docs/verification-registry.json")

ROWS = [
    {
        "id": "r499.paraphrase-axis-judge",
        "level": "L2",
        "owner_round": "R499",
        "capability": (
            "**本地改写通道的判据面 (先于真机落盘)**: ①门态正控 —— C 臂 turn8 的 `local_turn_gate.kv.basis` "
            "必须不含 paraphrase 且该轮有远端调用; P 臂必须含 paraphrase (absorb 或 degrade 均算门生效), "
            "并据 basis 尾串区分 absorb_local / degrade_remote; ②改写质量结构不变量 —— 答复非空/非模板字面量/"
            "非上一条逐字复读/长度比 0.15..4.0/无动作宣称/无新增标识符 (标识符按字符类抽取, 语言无关); "
            "③成本面 —— 调用数按 `request_id` 去重 (含 `llm_call_continue`) + 付费 token 取 usage 求和 + 空正文数; "
            "④族回归 —— turn2..5 必须本地消化且 0 远端调用 (basis 允许机械/本地门两种载体)。"
            "仪器口径: `local_turn_gate` 行数必须恒等于 turns 统计数, 否则 fail-closed (rc=2, 禁当绿); "
            "任一输入文件缺席 ⇒ rc=2。"
        ),
        "evidence_cmd": "python3 eval/rover/r499/judge_paraphrase_r499.py --dir eval/rover/r497 --arm T1 --mode C",
        "evidence_path": "eval/rover/r499/judge-selftest-r499.txt",
        "covers": ["eval/rover/r499/judge_paraphrase_r499.py", "eval/rover/r499/analyze_r499.py",
                   "src/agent/IndustrialAgentV2.cs", "src/agent.modelqueue/LocalParaphraseChannel.cs",
                   "src/agent.modelqueue/LocalGenerationPort.cs"],
        "negative_control": (
            "三态负控 (注入扰动到 scratch 副本, 期望判红): `nc_c_absorb` (把 C 臂 turn8 basis 改成 mechanical:paraphrase) "
            "**已实测 rc=1 且 red=1**; `nc_drop_gate_row` (删 P 臂第 8 条门行 ⇒ 行数≠turns ⇒ rc=2) 与 "
            "`nc_template_reply` (把 P 臂 turn8 答复换成上一条逐字复读 ⇒ J2b 红) **待真机 P 臂落盘后补跑** "
            "—— 未跑前不得据负控宣称判据完备。干跑实证: 对 R497/T1 判据器 VERDICT=GREEN red=0 (无假红)。"
        ),
    },
    {
        "id": "r499.aot-string-presence-method",
        "level": "L4",
        "owner_round": "R499",
        "capability": (
            "**AOT 产物「特征存在性」判据的方法更正**: 环境变量**字面量**在 .NET NativeAOT 产物里既非 ASCII 明文, "
            "亦非 UTF-16LE 明文 (对 `/tmp/pub_r498` 与 `/tmp/pub_r499` 两种编码命中均为 0; 8 个字面量钥匙全 0) ⇒ "
            "`grep -ac AGENTFRAMEWORK_X <bin>` 这一存在性检查是**假阴性源**, 不得作拒跑依据 "
            "(R492 曾据此判「二进制缺剪裁闸」, 该结论的方法面不成立, 其行为面证据〔闸置 on 后遥测 pair_gate 恒 0〕独立保留)。"
            "可用的判据 = 元数据**类型/方法名表** (ASCII 明文): LocalParaphraseChannel / ReplayPairTrim / ToolDeclGate / "
            "LocalDecisionLedger / MicroStepIsolationGate / LocalGenerationPort / ActionLoop / IndustrialAgentV2 = 8/8 命中。"
            "发布检查器具已按此改写 (CLASS_MISSING 为空才放行)。"
        ),
        "evidence_cmd": "python3 eval/rover/r499/probe_aot_string_presence.py /tmp/pub_r498/agenthost /tmp/pub_r499/agenthost",
        "evidence_path": "eval/rover/r499/aot-string-presence-r499.txt",
        "covers": ["eval/rover/r499/probe_aot_string_presence.py", "eval/rover/r499/publish_and_il_check_r499.sh"],
        "negative_control": (
            "双侧对照: 同一把钥匙在**产品源码存在**的两个产物上均 0 命中 ⇒ 证伪「0 命中 = 代码缺席」这条推理; "
            "同一把二进制上类名表 8/8 命中 ⇒ 证明「存在性」可由另一条通道判定。"
            "诚实边界: 本方法只证**代码在场**, 不证**开关生效** —— 开关生效必须由真机遥测 (basis/打点) 取证。"
        ),
    },
    {
        "id": "r499.preflight-o5-attribution",
        "level": "L3",
        "owner_round": "R499",
        "capability": (
            "**起手闸 O5「本轮驱动器在世」在多会话共祖先链下的归属失真 (实测)**: 6 次采样中, "
            "`build_node_reap.refused[].reasons` 含 `O5_本轮驱动器在世` 的构建节点其驱动器**并非本会话** "
            "—— 同机并行的对侧会话与本会话共享 `self_ancestors` (同为 hermes 网关子进程) ⇒ 祖先 pid 集合无法区分「谁起的」。"
            "后果双向: 对侧构建可能被判成「本轮」(拒收而不收口), 本轮的构建也可能被对侧误判。"
            "同时记录事实: 内存阈值 2650 MB 在争用窗口内**反复穿越** (实测 2208 / 2315 / 2528 / 2544 / 2592 / 2654 MB, 6 次中 1 次 PASS)"
            " ⇒ 单次采样判定不可靠, 起手闸须给出「连续 n 次通过」或带沉降时间的置信面。"
            "本轮据此**让行**: 真机 4 臂 (C + P×3) 未起, 只落判据/器具/发布与让行证据。"
        ),
        "evidence_cmd": "bash eval/rover/r499/make_evidence_r499.sh",
        "evidence_path": "eval/rover/r499/gate-hold-r499.txt",
        "covers": ["eval/rover/r499/gate-hold-r499.txt", "eval/rover/r483/preflight_gate.py",
                   "eval/rover/r499/gate_retry_r499.sh"],
        "negative_control": (
            "六次采样并列 (同一器具、同一会话) ⇒ 结论不是单点读数; 且 PASS 的那一次其 `refused[]` 仍含 O5 判词 ⇒ "
            "「PASS 与 O5 判词可同时出现」这一矛盾本身即归属失真的直接证据。"
            "**修法候选 (未实施)**: 驱动器比对改用会话标识 (环境变量/会话 id) 而非祖先 pid 集合; 内存判据改「连续 3 次 ≥ 阈值」。"
        ),
    },
]


def main() -> int:
    apply = "--apply" in sys.argv
    tok = guard_or_die(REG, "R499")
    raw = REG.read_text(encoding="utf-8-sig")
    doc = json.loads(raw)
    rows = doc["rows"]
    before = len(rows)
    rows[:] = [r for r in rows if r.get("owner_round") != "R499"]
    removed = before - len(rows)
    rows.extend(ROWS)
    doc["updated_round"] = "R499"
    out = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
    print(f"[dry={not apply}] removed_old={removed} added={len(ROWS)} total={len(rows)}")
    if apply:
        REG.write_text(out, encoding="utf-8")
        back = json.loads(REG.read_text(encoding="utf-8-sig"))
        ids = [r["id"] for r in back["rows"] if r.get("owner_round") == "R499"]
        assert len(ids) == len(ROWS), f"读回条数不符: {ids}"
        assert back["updated_round"] == "R499"
        print("PASS 读回:", ", ".join(ids))
        verify_or_die(REG, "R499", tok)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
