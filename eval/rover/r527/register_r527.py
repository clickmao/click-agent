#!/usr/bin/env python3
"""R527 登记: 把本轮结构性收口 (候选①②③④⑤ + 竞态修因) 落成 docs/verification-registry.json 行。

口径:
  - `covers` 为纯仓内路径 (文件或目录, 目录以 `/` 结尾);
  - `evidence_path` 指向本轮落盘证据 (eval/rover/r527/evidence/*);
  - `evidence_generated_with`: 冻结行 (`frozen`) 的 `artifact_sha12` 取证据文件现盘 `sha256[:12]`,
    器具行给出 `instrument`/`instrument_sha12` (现盘字节), 故 R2e 三条硬闸可在提交面重算;
  - 幂等: 已存在同 id 行时只报错不重复追加 (除非 --rebind 重钉字节).
"""
import hashlib
import io
import json
import os
import subprocess
import sys

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
REG = os.path.join(ROOT, "docs/verification-registry.json")
EV = "eval/rover/r527/evidence"


def sha12(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return None
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12]


def pin(evidence_rel, instrument_rel=None, kind="artifact", status="frozen", reason=None, binding="audit-pin"):
    if reason is None:
        reason = "archived-per-round" if status == "frozen" else "worktree-only"
    return {
        "evidence_kind": kind,
        "pin_status": status,
        "pin_reason": reason,
        "artifact_sha12": sha12(evidence_rel) if status == "frozen" else None,
        "instrument": instrument_rel,
        "instrument_sha12": sha12(instrument_rel) if instrument_rel else None,
        "binding": binding,
        "audited_by_round": "R527",
    }


def rows():
    ev_tests = f"{EV}/tests-full-r527.txt"
    ev_aot = f"{EV}/aot-r527.txt"
    ev_equiv = f"{EV}/equiv-post-compare.txt"
    ev_gate = f"{EV}/new-file-gate.txt"
    ev_cpm = f"{EV}/cpm-central-package-versions.txt"
    ev_inv = f"{EV}/invariant-check.txt"
    return [
        {
            "id": "internal.partial-aware-source-pins-r527",
            "level": "L2",
            "capability": "**源级钉死 partial-aware (R527)**: R526 把「单类型单文件」放宽为「主文件 + 同类型分片 `<Type>.<Suffix>.cs`」后, 27 处按 `<File>.cs` 单文件读源码的钉死断言会漏读分片 (断言假绿风险)。本轮新增 `src/agent.tests/SourcePin.cs` (`Text(rel)` / `TextParts(rel)`: 按类型读**全部** partial 分片并拼接) 并由 `tools/refactor/r527_partial_aware_source_pins.py` 机械改写 27 处 `File.ReadAllText(Path.Combine(root!, rel))` → `SourcePin.Text(rel)`。断言强度不降: 分片内容同样进入断言文本。",
            "covers": [
                "src/agent.tests/SourcePin.cs",
                "tools/refactor/r527_partial_aware_source_pins.py",
            ],
            "evidence_cmd": "env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR $HOME/.dotnet/dotnet test src/agent.tests/agentframework.tests.csproj -c Debug --nologo",
            "evidence_path": ev_tests,
            "evidence_generated_with": pin(ev_tests, "tools/refactor/r527_partial_aware_source_pins.py"),
            "negative_control": "`SourcePin.Text` 只读主文件时, 被拆出分片的断言文本必缺片段 ⇒ 钉死断言应红 (改写前该 27 处正是此形态, 故列为负控)。另: 全量 1755 项含 `RefactorStructureTests` 结构不变式, 拆分后仍全绿 = 结构闸未被我方改写松动。",
            "owner_round": "R527",
        },
        {
            "id": "internal.giant-class-partial-split-2-r527",
            "level": "L2",
            "capability": "**第二批巨类 partial 拆分 (R527)**: `agent.modelqueue/ModelQueueRouter.cs` → 主文件 + `.Catalog`/`.Call`/`.Failure`/`.Recovery`/`.LocalChannel` 5 分片; `agent/contextassembler/ContextAssembler.cs` → 主文件 + `.Assemble`/`.Prompt`/`.Recall`/`.Compress`/`.Support` 5 分片 (共 10 个新分片)。切分由 reftool 成员边界驱动, 并新增 `RebalanceRegions`: partial 拆分把收尾花括号前导 trivia 留主文件、开头 `#region` 随成员移出 ⇒ 逐文件 `#region/#endregion` 失配 (R526 只处理跨文件失配, 本轮补「单文件内配对」)。不变式机检新增 **I4 (region 逐文件配对)** 与准入闸同口径。",
            "covers": [
                "src/agent.modelqueue/ModelQueueRouter.cs",
                "src/agent.modelqueue/ModelQueueRouter.Catalog.cs",
                "src/agent.modelqueue/ModelQueueRouter.Call.cs",
                "src/agent.modelqueue/ModelQueueRouter.Failure.cs",
                "src/agent.modelqueue/ModelQueueRouter.Recovery.cs",
                "src/agent.modelqueue/ModelQueueRouter.LocalChannel.cs",
                "src/agent/contextassembler/ContextAssembler.cs",
                "src/agent/contextassembler/ContextAssembler.Assemble.cs",
                "src/agent/contextassembler/ContextAssembler.Prompt.cs",
                "src/agent/contextassembler/ContextAssembler.Recall.cs",
                "src/agent/contextassembler/ContextAssembler.Compress.cs",
                "src/agent/contextassembler/ContextAssembler.Support.cs",
                "tools/refactor/invariant_check.py",
                "tools/refactor/reftool/Program.cs",
            ],
            "evidence_cmd": "python3 tools/refactor/invariant_check.py",
            "evidence_path": ev_inv,
            "evidence_generated_with": pin(ev_inv, "tools/refactor/invariant_check.py"),
            "negative_control": "I4 负控: 拆分中途实测 `ContextAssembler.Assemble.cs:382` 的 `#region Private Methods` 与 `ContextAssembler.cs:92` 的 `#endregion` 跨文件失配 (未加 RebalanceRegions 前的真实读数) ⇒ 机检必红; 修后 I4 = 0。",
            "owner_round": "R527",
        },
        {
            "id": "internal.central-package-versions-r527",
            "level": "L2",
            "capability": "**包版本集中化 (CPM, R527)**: 新增 `src/Directory.Packages.props` (24 条 `PackageVersion`), `src/*/*.csproj` 内 `Version=` 属性残留 **0**; 同一包 id 出现两个不同版本 ⇒ fail-closed 拒收 (机检负控)。`--apply` 幂等: 复跑命中 0 变更, 且保留既有 props 条目 (不覆盖已在册版本)。",
            "covers": [
                "src/Directory.Packages.props",
                "tools/refactor/pipeline/08_central_package_versions.py",
            ],
            "evidence_cmd": "python3 tools/refactor/pipeline/08_central_package_versions.py --selfcheck",
            "evidence_path": ev_cpm,
            "evidence_generated_with": pin(ev_cpm, "tools/refactor/pipeline/08_central_package_versions.py", status="live", reason="self-derived"),
            "negative_control": "`--selfcheck` 在临时目录造「同包两版本」 ⇒ 必拒 (输出 `conflict_rejected=True`); 「同包同版本」不得误报。构建面: CPM 落地后 `dotnet build agent.sln` = 0 Error / 76 Warning。",
            "owner_round": "R527",
        },
        {
            "id": "internal.new-file-structure-gate-r527",
            "level": "L4",
            "capability": "**新增 .cs 文件结构前置闸 (R527)**: `tools/refactor/new_file_gate.py` 对 `git status` 新增 (untracked) 的 `.cs` 逐文件判 G1 单类型单文件 / G2 命名空间存在 / G3 目录-命名空间一致 (同目录 sibling 逐文件扫描) / G5 文件级声明唯一 / G6 花括号配对 (**去字面量后**计数, 规避字符串内花括号误判) / G7 登记表 covers 命中 (**partial-aware**: 覆盖 `a/B.cs` 的行同时覆盖 `a/B.Suffix.cs`) 并扩 `RX_TYPE` 覆盖 `partial`/`record struct` 等修饰。`tools/hooks/pre-commit` (core.hooksPath 指向) 末尾追加本闸段, 开关 `AGENTFRAMEWORK_NEW_FILE_GATE=0` 可关。",
            "covers": [
                "tools/refactor/new_file_gate.py",
                "tools/hooks/pre-commit",
                "tools/refactor/install_new_file_gate_hook.sh",
            ],
            "evidence_cmd": "python3 tools/refactor/new_file_gate.py --selfcheck && bash tools/hooks/pre-commit",
            "evidence_path": ev_gate,
            "evidence_generated_with": pin(ev_gate, "tools/refactor/new_file_gate.py", status="live", reason="worktree-only"),
            "negative_control": "两级负控: ①`--selfcheck` 内置 RED 判据负控 (含 G7 covers 正/负控: 覆盖命中 = 不告警 / 空 covers = 不告警 / 未覆盖 = 告警); ②提交面注入违规新文件 (`src/agent.core/R527GateProbeB.cs`, 文件名≠类型名) ⇒ `bash tools/hooks/pre-commit` rc=**1** 且点名该文件; 撤除后洁净树 rc=**0**。",
            "owner_round": "R527",
        },
        {
            "id": "internal.namespace-convergence-r527",
            "level": "L2",
            "capability": "**命名空间收敛 + 撤豁免 (R527)**: R526 的 I3b (同目录唯一命名空间) 曾对 `src/agent.core/{userinteraction,subagent}` 开两条豁免 —— 因其中文件声明 `agent.userinteraction`/`agent.subagent` (与 `src/agent/` 下同名目录跨程序集共享命名空间, 类型同名两处)。本轮把这两个目录内文件改声明 `agent.core`, 并**删除两条豁免** (机检与 `RefactorStructureTests` 同口径), 由 `tools/refactor/pipeline/09_converge_namespace.py` 机械改写 + `10_fix_moved_type_usings.py` 编译器驱动收口 (CS0246 补 using / CS0234 修正全限定名 / CS0103 补 using), 全过程以「构建 0 Error」为收敛判据。",
            "covers": [
                "src/agent.core/userinteraction/",
                "src/agent.core/subagent/",
                "src/agent.tests/RefactorStructureTests.cs",
                "tools/refactor/pipeline/09_converge_namespace.py",
                "tools/refactor/pipeline/10_fix_moved_type_usings.py",
            ],
            "evidence_cmd": "python3 tools/refactor/invariant_check.py && python3 tools/refactor/pipeline/10_fix_moved_type_usings.py",
            "evidence_path": ev_inv,
            "evidence_generated_with": pin(ev_inv, "tools/refactor/pipeline/10_fix_moved_type_usings.py"),
            "negative_control": "撤豁免后 I3b = 0 (收敛前该两目录若仍多命名空间 ⇒ I3b 必红)。语义面: 收敛第一次全量跑暴露 `FrontendAskFlowTests.问询信封抵达客户端_回复后调用方拿到答案` 红 (Expected 1 / Actual 2), 单类隔离复现 ⇒ 归因 ctor 就绪探针连接的服务端异步注销竞态 (非语义回归), 以有界收敛等待修因; 修后该类 6/6、全量 1755/1755。",
            "owner_round": "R527",
        },
        {
            "id": "internal.onprocess-bounded-extraction-r527",
            "level": "L2",
            "capability": "**`OnProcessAsync` 有界抽取 (R527, 铁律 13)**: 自 1662 行巨方法原位搬出两段**顺序不变**的自包含块 —— ① 轮起始状态清零 + 活动心跳 → `private DateTime BeginTurn(Message message)` (11 行 → 1 行调用); ② 回复因果绑定 + 偏题计数/牵引/澄清状态推进 → `private (bool SteeringPending, bool ClarifyPending) BindReplyAndAdvanceTopicState(LLMResponse, bool, string, TopicRelevanceVerdict?)` (44 行 → 2 行调用)。抽取只做「整段搬运 + 返回原局部变量」, 不重排语句、不改判据。等价性由既有夹具背书: `eval/rover/r527/equiv_local_commands.py` 对 AOT 二进制喂确定性本地命令族, 逐臂比对 stdout 文本与 sha256。",
            "covers": [
                "src/agent/IndustrialAgentV2.cs",
                "eval/rover/r527/equiv_local_commands.py",
            ],
            "evidence_cmd": "python3 eval/rover/r527/equiv_local_commands.py --binary /tmp/pub_r527/agenthost --sandbox /tmp/r527/eq_post --out eval/rover/r527/golden-post.json",
            "evidence_path": ev_equiv,
            "evidence_generated_with": pin(ev_equiv, "eval/rover/r527/equiv_local_commands.py"),
            "negative_control": "抽取前 (R526 AOT `/tmp/pub_r526/agenthost`) 与抽取后 (R527 AOT `/tmp/pub_r527/agenthost`) 跑同一夹具同一命令族, 逐臂 `out_sha256`/`err_sha256` 必须逐字节相同; 任一臂不同 ⇒ 抽取判为语义漂移 (不接受)。**夹具只覆盖确定性本地命令族** (进入 LLM 前的本地路由/早退分支), 不覆盖真实 LLM 路径 ⇒ 见诚实边界。",
            "owner_round": "R527",
        },
    ]


def main():
    apply = "--apply" in sys.argv
    d = json.load(io.open(REG, encoding="utf-8"))
    have = {r["id"] for r in d["rows"]}
    add = [r for r in rows() if r["id"] not in have]
    miss = [r["id"] for r in rows() if r["id"] in have]
    print(f"登记表现有 {len(d['rows'])} 行; 待追加 {len(add)} 行; 已存在 {len(miss)} 行")
    for a in add:
        ew = a["evidence_generated_with"]
        if not os.path.exists(os.path.join(ROOT, a["evidence_path"])):
            print(f"FAIL 证据缺失: {a['evidence_path']}")
            return 3
        if ew["pin_status"] == "frozen" and not ew["artifact_sha12"]:
            print(f"FAIL 冻结行无 artifact_sha12: {a['id']}")
            return 3
        print(f"  + {a['id']:52s} {a['level']}  artifact={ew['artifact_sha12']} instrument={ew['instrument_sha12']}")
    if "--rebind" in sys.argv:
        fresh = {r["id"]: r for r in rows()}
        n = 0
        for r in d["rows"]:
            if r["id"] in fresh and "--rebind" in sys.argv:
                r["evidence_generated_with"] = fresh[r["id"]]["evidence_generated_with"]
                n += 1
        d["updated_round"] = "R527"
        io.open(REG, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
        print(f"重钉 {n} 行 (updated_round=R527)")
        return 0
    if not apply:
        print("DRY (加 --apply 落盘)")
        return 0
    d["rows"].extend(add)
    d["updated_round"] = "R527"
    io.open(REG, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
    print(f"写入完成: {len(d['rows'])} 行 (updated_round=R527)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
