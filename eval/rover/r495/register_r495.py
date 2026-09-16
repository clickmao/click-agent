#!/usr/bin/env python3
# R495 登记: 把本轮证据写入 docs/verification-registry.json (写入后立刻跑形式门禁)。
# 用法: python3 eval/rover/r495/register_r495.py [--dry]
import hashlib, json, os, sys

ROOT = "/home/agentuser/AgentFramework"
REG = os.path.join(ROOT, "docs/verification-registry.json")
D = "eval/rover/r495"


def sha12(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return None
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def row(id_, level, cap, cmd, path, instrument, covers, neg, audited="R496"):
    return {
        "id": id_, "level": level, "owner_round": "R495", "capability": cap,
        "evidence_cmd": cmd, "evidence_path": path,
        "evidence_generated_with": {
            "evidence_kind": "artifact", "pin_status": "frozen",
            "pin_reason": "archived-per-round", "artifact_sha12": sha12(path),
            "instrument": instrument, "instrument_sha12": sha12(instrument),
            "binding": "audit-pin", "audited_by_round": audited},
        "covers": covers, "negative_control": neg,
    }


def main(dry=False):
    reg = json.load(open(REG, encoding="utf-8"))
    ids = {r["id"] for r in reg["rows"]}
    kpi = json.load(open(os.path.join(ROOT, D, "kpi-r495.json"), encoding="utf-8")) if os.path.exists(
        os.path.join(ROOT, D, "kpi-r495.json")) else {}
    adv = json.load(open(os.path.join(ROOT, D, "adv-code-T1r495.json"), encoding="utf-8")) if os.path.exists(
        os.path.join(ROOT, D, "adv-code-T1r495.json")) else {}
    leak = json.load(open(os.path.join(ROOT, D, "leak-check-Br495.json"), encoding="utf-8")) if os.path.exists(
        os.path.join(ROOT, D, "leak-check-Br495.json")) else {}

    r1 = row("r495.local-decision-ledger-mount", "L2",
             "**本地决策台账落盘 + 尾部挂载 (第二类本地真值)**: 每轮闸判定单点落盘 "
             "(`turn|kind|chars|n|code|canon` JSONL) + 远端调用前把「链自持核对码」以**尾部** system 块挂载 "
             "(前缀面 system/context/history/user 逐字节不变)。三源一致机检: 实发面 (中继归档请求体) / "
             "落盘面 (JSONL) / 打点面 (`tool_decl_gate.kv.ledger_*`) —— 核对码可用 `canon` 独立复算。"
             "**判别力宣称已收窄**: 预注册 H2「关轴臂结构上不可知真值」被 t14/t15 实证证伪 "
             "(关轴 B 臂读盘 + 公开配方复算, 命中台账 n=14/15)。",
             "python3 %s/assert_face_r495.py --arm T1r495 --dir %s --channel on --mount on; "
             "python3 %s/judge_code_r495.py --arm T1r495 --mount on --turns %s/turns-T1r495.jsonl "
             "--calls %s/calls-T1r495.jsonl --tel %s/tel-T1r495/host.jsonl --ledger %s/ledger-T1r495.jsonl "
             "--grid %s/grid/task-p15-code.json" % (D, D, D, D, D, D, D, D),
             "%s/assert-face-T1r495.json" % D, "%s/assert_face_r495.py" % D,
             ["%s/prereg_r495.json" % D, "%s/grid/task-p15-code.json" % D, "%s/run_arm_real_r495.sh" % D,
              "src/agent.modelqueue/LocalDecisionLedger.cs",
              "src/agent.modelqueue/ModelQueueRouter.cs", "src/agent/IndustrialAgentV2.cs",
              "%s/judge_code_r495.py" % D, "%s/leak-check-Br495.json" % D,
              "src/agent.tests/R495LocalDecisionMountTests.cs"],
             "① 必错族**证伪** (不是「通过」): 关轴 B 臂 t14/t15 回复给出真实台账码 %s / %s "
             "(见 `leak-check-Br495.json`, 与台账 n=14/15 逐字命中) ⇒ 真值另有可达通道 (盘上台账 + 源码公开配方), "
             "判别力不能建立在「不可知」上。② 判据器两处修订 (挂载块须 system 角色 + 结构行; 打点字段落在 "
             "`tool_decl_gate` 而非 `llm_call`), 均带正/负控 (selftest 3/3 与 6/6) 证「未放松真挂载检出」。"
             "③ 旁路观察: 夹具「命题核验」工具把**越界被拒**的源文件行原样回显进 tool 消息 (B 臂 5 条请求) "
             "—— 不含真值, 但属独立泄漏通道。" % (
                 ", ".join(leak.get("turns", [{}])[1].get("true_codes_leaked", []) or ["?"]),
                 ", ".join(leak.get("turns", [{}, {}, {}])[2].get("true_codes_leaked", []) or ["?"])),
             audited="R496")

    r2 = row("r495.same-window-ladder-mount-axis", "L2",
             "**同窗三臂真机阶梯 (挂载轴单变量)**: 网格 = R494 12 轮逐字节继承 + 3 轮链自持台账必错族 (p15code); "
             "B 全关 / T0 = R494-T1 逐位复现 / T1 = T0 + 挂载轴。读数见 `kpi-r495.json`: %s"
             % json.dumps(kpi.get("ladder") or kpi.get("arms") or {}, ensure_ascii=False)[:400],
             "python3 %s/analyze_r495.py; python3 %s/judge_code_r495.py --arm T1r495 --mount on ..." % (D, D),
             "%s/kpi-r495.json" % D, "%s/analyze_r495.py" % D,
             ["%s/prereg_r495.json" % D, "%s/grid/task-p15-code.json" % D, "%s/run_arm_real_r495.sh" % D,
              "%s/calls-Br495.jsonl" % D, "%s/calls-T0r495.jsonl" % D, "%s/calls-T1r495.jsonl" % D,
              "%s/usage-Br495.jsonl" % D, "%s/usage-T0r495.jsonl" % D, "%s/usage-T1r495.jsonl" % D,
              "%s/assert-face-Br495.json" % D, "%s/assert-face-T0r495.json" % D,
              "%s/pin-r495.json" % D, "%s/adv-code-Br495.json" % D, "%s/adv-code-T0r495.json" % D],
             "① 与 R494 非同窗 (网格多 3 轮) ⇒ **禁跨窗相减**, 只作参照。② 起手闸内存门 (2650MB) 首跑即红 "
             "(MemAvailable 2473) ⇒ 按纪律让行 (preflight-Br495.json 为证), 收口 build-server + drop_caches 后重跑通过。"
             "③ quiesce 环以 `correction_judge` 计数稳定为准, 该计数**缓滴增长** (11→15 行/2 min) ⇒ 每臂 "
             "固定等待 ~510 s (夹具自身行为, 非本轮改动)。④ 通道轴 (R494 的 T0↔T1) 本轮未复测; 定长腿只用 "
             "t13/t15 (固定格式短答) 作长度受控观测。",
             audited="R496")

    r3 = row("r495.capability-face-reaudit-pin-idempotence", "L2",
             "**能力自检面只读复核 + 冻结 pin 幂等化**: 5 红复核结论 —— (a) `bind_evidence --check` rc=2 系本轮"
             "**重跑只读复核器**改写了 `audit-capability-face.json` (原写侧每次刷新 `audited_at_epoch` ⇒ 冻结 pin 每跑必红); "
             "已把写侧改为**幂等落盘** (语义未变不重写) 并重钉 (连跑两次字节恒定 `63161c7ec8a4`)。"
             "(b) `committed-state` 与 `only-equivalence` 现跑 rc=0 (9/9) ⇒ 面文件里的 rc=2 是**旧读数**; "
             "A3 `manifest_sha12` 声明 `ad97f379503a` vs 现盘 `976b9d0d059c` ⇒ 该面处于**并发会话线改写中**。"
             "(c) `exp1q17.archive-field-provenance` scoped 面 rc=2 vs declared cmd rc=0 ⇒ **口径差未闭合** (两条不同调用面)。",
             "python3 eval/rover/r494/audit_capability_face_r494.py; "
             "python3 eval/capability/exp1-q31/instruments/only_equivalence_guard.py; "
             "python3 eval/capability/exp1-q17/archive_field_provenance.py --selftest --out /tmp/v.json "
             "--fixtures-out /tmp/s.json",
             "eval/rover/r494/audit-capability-face.json", "eval/rover/r494/audit_capability_face_r494.py",
             ["eval/capability/instruments.json", "eval/rover/r494/audit-capability-face.json",
              "eval/capability/exp1-q31/instruments/only_equivalence_guard.py",
              "eval/capability/exp1-q17/archive_field_provenance.py"],
             "重钉后形式门禁 (`VerificationFormTests`) 7/7 绿; 只读重跑审计器不改字节 (幂等自证); "
             "未闭合项 (exp1q17 口径差 + 面文件并发改写) 显式留在 R496 候选, 不以遮蔽换绿。",
             audited="R496")

    new = [r for r in (r1, r2, r3) if r["id"] not in ids]
    if dry:
        print(json.dumps(new, ensure_ascii=False, indent=1)[:1500]); return 0
    reg["rows"].extend(new)
    reg["updated_round"] = "R495"
    json.dump(reg, open(REG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[register] +%d 行 (updated_round=R495) → %s" % (len(new), REG))
    for r in new:
        print("  ", r["id"], r["level"], "artifact_sha12=%s inst=%s" % (
            r["evidence_generated_with"]["artifact_sha12"], r["evidence_generated_with"]["instrument_sha12"]))
    return 0


if __name__ == "__main__":
    sys.exit(main("--dry" in sys.argv))
