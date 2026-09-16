#!/usr/bin/env python3
"""EXP1-Q29: 台账追加 (kpi.jsonl) + 计划文档附录 AD —— 幂等 + 前缀不变 + 读回校验.

纪律 (承 R409/R418/共享台账):
  - 新行**键集与键序**必须与既有同族行完全一致 (先 dump 最后一条取形状);
  - 追加式写入必须证明「原有字节是前缀」(不重排/不改写历史); 重复运行不重复追加 (按 round 去重);
  - 写后读回: 逐行可解析 + 新行 round 正确 + 键序一致。
"""
import json, os, sys, time

ROOT = "/home/agentuser/AgentFramework"
KPI = os.path.join(ROOT, "eval/capability/kpi.jsonl")
DOC = os.path.join(ROOT, "docs/plans/v0.22.0-exp1-local-index-and-code-graph.md")
ROUND = "EXP1-Q29"

TS = time.strftime("%Y-%m-%dT%H:%M+0800")

ROW = {
    "round": ROUND,
    "ts": TS,
    "kind": "self-check / 器具修复: 登记表整文件序列化通路的尾换行仲裁与形态容忍(通路不再被形态差异静默禁用) + 自引用器具行重审",
    "artifact": "eval/capability/exp1-q29/{prereg_q29.json,prereg_q29_amendmentA1.json,verify_q29.py,verify_q29_verdict.json,posthoc_q29.py,posthoc_q29_verdict.json,posthoc2_q29.py,posthoc2_q29_verdict.json,posthoc2_q29_verdict.run1.json,apply_repin_q29.py,scratch/}; eval/capability/bind_evidence.py; docs/verification-registry.json (r476.evidence-binding-round-param); docs/plans/v0.22.0-exp1-local-index-and-code-graph.md (附录 AD)",
    "change": "① 前提核验(先测后改): Q28 的「registry 尾换行被 R479 移除 ⇒ 断言 fail-closed ⇒ 程序化改写通路禁用」在现盘**为假** —— 尾字节沿革 5576e72(LF) → 058bc77/R479(无LF) → dcaff6f/Q28(无LF) → e3f7a44/R481(LF 恢复) → c4055ba/R481-F(LF) → HEAD(LF); 主线台账 docs/reports/r480-recall-test-ledger.md「尾部换行 1 B 修复」已按器具自身契约补回 ⇒ **仲裁已由主线完成(约定=有 LF)**, 本轮只需解决「通路不得因风格差异静默禁用」; ② bind_evidence.py 断言: 尾形态二态容忍(ser 或 ser+LF) + 回写规范化到 LF 并把「补 1 B」显式打进 stdout(白盒), 缩进/转义/行尾漂移照旧 rc=3; ③ 自引用行重审(设计要求): artifact_sha12/instrument_sha12 262cdd978d1c→5127b5c0592b, audited_by_round R478→EXP1-Q29 (块级替换, 3 行)",
    "readings": {
        "前提证伪的直接读数": "真实文件上 ser+'\\n' == raw ⇒ True (旧断言今天本就过) ; 尾 4 字节 xxd = 220a7d0a",
        "修后器具(真实副本端到端)": "asis: rc=0 SER_ASSERT=OK(tail=LF) WRITE_READBACK=OK; nolf: **修前** rc=3 拒写且零字节改动(复现 Q28) → **修后** rc=0 tail=NONE->LF, 回写后确带 LF (补 1 B 已显式报告)",
        "非空心(格式漂移面)": "CRLF 变体 rc=3、ensure_ascii=True 变体 rc=3、indent=2 变体 rc=3; 三者 fail 时均一个字节都不写 (fail-closed)",
        "churn 面(逐行变更键集直方图)": "touched 104 = 103 行 {audited_by_round} + 1 行 {artifact_sha12,audited_by_round,instrument_sha12,pin_status,pin_reason}=自引用行重审; 除设计内重审外纯度 = 103/104",
        "粒度定位": "--apply 的粒度 = 全表 needs_field 重审 (TOUCHED=104) ⇒ 单行重审仍须块级文本插入; 通路恢复解决「可写」, 未解决「可定向」",
        "连带重审阳性对照": "器具改动后 --check **恰好**报 2 条 VIOLATION (r476.* 冻结 pin 与现盘字节不符 / 器具绑定与现盘不符, 声明 262cdd978d1c 实际 5127b5c0592b) ⇒ 「器具一改引用它的证据须重审」是活闸非装饰; 重审后 R2E_R2F_EXIT=0 (104 行同分布)",
        "零副作用": "真登记表在器具跑动前后 sha 逐位相同 (dcd65b6caeb4); 全部写入落在 scratch 副本",
        "幂等": "重审脚本二次运行 IDEMPOTENT=OK; 台账/附录追加脚本按 round 去重",
        "零回归": "git diff --numstat = 3/3 (限该行 3 个键); 行数 151→151; ser+LF==raw 仍成立(尾形态保留)",
        "形式门禁": "dotnet test --filter VerificationForm|SkillGeneralization|DevPlanDocRef ⇒ Failed 0 / Passed 14 / rc=0 (过滤器命中 14 个测试, 非 0 命中假绿)",
    },
    "honest_boundaries": [
        "首跑 2 处红照原样保留, 归因均为**我方控制设计缺陷**(非产品/器具缺陷): (a) reorder 负控**结构性不可判别** —— 断言语义是 load→dump 逐字节复现, 键序由解析顺序自带 ⇒ 任何键序重排都被忠实复现, 该控制恒绿; 真正可判别面 = 序列化格式漂移(CRLF/转义/缩进), 已用替代控制实测。(b) P4p「修前器具应得纯度 1.0」错误 —— derive() 读**现盘文件**, 与工具版本无关 ⇒ 该控制无法隔离重审行。",
        "posthoc2 run1 期望键集写漏(只写 3 键, 实测 5 键): 多出的 pin_status/pin_reason 是派生语义 —— derive() 把「已改未提交」的器具判 live/worktree-only ⇒ 冻结 pin 只能在**提交后**成立(run1 verdict 另存 posthoc2_q29_verdict.run1.json, 未覆盖)。",
        "AC.6① 原文「(并保留『禁重排』意图)」措辞**不准确**: 该断言结构上不承担「禁重排」; 真实保护面 = 序列化格式漂移。已按实测收窄该宣称。",
        "尾部 1 B 的契约归属属主线(R481 已修复并登记); 本轮只做「不再因形态差异禁用通路 + 规范化显式化」, 未改约定、未擅动主线行以外字节。",
        "本轮只推进一步: 候选②③④⑤⑥⑦ 未动; 新识别候选①-b(--only 定向重审)未实现。",
    ],
    "next": "候选①-b: bind_evidence 加 --only <id> 定向重审(把 TOUCHED 从 104 收窄到目标行), 判据=同一行用 --only 与块级插入得到逐字节相同的登记表; 候选② worktree-only 6 条陈旧声明清理; 候选③ 9 行未派生器具; 候选④ L2 全量面复跑(需 dotnet 窗口)",
    "owner_round": ROUND,
}

APPENDIX = """

## 附录 AD — EXP1-Q29: 登记表尾换行仲裁 + 整文件序列化通路恢复 (60m 自检作业, 不占主线轮号)

**命题**: 承 AC.6① —— 「仲裁 registry 尾换行约定; 修 `bind_evidence` 的整文件断言以接受实际形态」。

### AD.1 前提核验门 (先测后改): AC.5② 的前提**在现盘为假**
| 提交 | 尾 4 字节 | 尾换行 | 说明 |
|---|---|---|---|
| `5576e72` | `220a7d0a` | 有 | Q28 之前的形态 |
| `058bc77` (R479) | `29220a7d` | **无** | AC.5② 所述「被移除」 |
| `dcaff6f` (EXP1-Q28) | `29220a7d` | **无** | Q28 断言 fail-closed ⇒ 走文本插入 fallback |
| `e3f7a44` (R481) | `220a7d0a` | 有 | 「96 行纯归属漂移回退」整份重写时带回 LF |
| `c4055ba` (R481-F) / `HEAD` | `220a7d0a` | 有 | 现盘状态 |

⇒ **Q28 的记录当时为真**(有直接字节证据), 但**断言今天本就通过**: 现盘实测 `dumps(doc, indent=1, ensure_ascii=False) + "\\n" == raw` → `True`。
⇒ 仲裁问题**已由主线回答**(`docs/reports/r480-recall-test-ledger.md` §「尾部换行 1 B 修复」: 原文件缺尾换行 ⇒ `SER_ASSERT` fail-closed ⇒ **按其自身契约补 1 B, 语义零变化**) ⇒ 约定 = **有 LF**。
⇒ 故本轮命题收窄为: **通路不得因尾字节风格差异被静默禁用**, 且规范化必须白盒可见。

### AD.2 器具修复 (bind_evidence.py)
断言由「严格绑定 LF 存在」改为**尾形态二态容忍** + 回写**规范化到 LF**并把「补 1 B」显式打进 stdout; 缩进漂移/转义漂移/行尾(CRLF)漂移照旧 `rc=3` 且零字节写入。

### AD.3 读数 (真机, 全部落在 scratch 副本)
| 用例 | 器具 | 读数 |
|---|---|---|
| `asis` | 修后 | `rc=0` `SER_ASSERT=OK (tail=LF)` `WRITE_READBACK=OK` |
| `nolf` | **修前** | `rc=3` 拒写 ∧ 文件字节不变 ⇒ **复现 Q28 阻塞** |
| `nolf` | 修后 | `rc=0` `tail=NONE->LF 补 1 B 承 R481 契约` ∧ 回写后确带 LF |
| `indent2` / CRLF / `ensure_ascii=True` | 修后 | `rc=3` ∧ 零字节写入 (断言非空心) |
| churn 直方图 | 修后 | `touched 104 = 103×{audited_by_round} + 1×{artifact_sha12,audited_by_round,instrument_sha12,pin_status,pin_reason}` |
| 零副作用 | — | 真登记表 sha 前后逐位相同 (`dcd65b6caeb4`) |

**连带重审 (阳性对照)**: 器具一改, `--check` **恰好**报 2 条 VIOLATION(`r476.evidence-binding-round-param`: 冻结 pin 与现盘字节不符 / 器具绑定与现盘不符) ⇒ 「器具一改, 引用它的证据必须重审」是**活闸**; 重审后 `R2E_R2F_EXIT=0`(104 行, 分布不变)。
**重审明细**: `artifact_sha12`/`instrument_sha12` `262cdd978d1c` → `5127b5c0592b`, `audited_by_round` `R478` → `EXP1-Q29`; 块级替换, `git diff --numstat = 3/3`, 行数 151→151, 尾形态保留, 二次运行 `IDEMPOTENT=OK`。
**形式门禁**: `VerificationForm|SkillGeneralization|DevPlanDocRef` ⇒ Failed 0 / Passed 14 / rc=0。

### AD.4 诚实边界
1. **首跑 2 处红均是我方控制设计缺陷**(照原样入档): ① `reorder` 负控**结构性不可判别** —— 断言语义是 load→dump 逐字节复现, 键序由解析顺序自带 ⇒ 键序重排必被忠实复现, 该控制恒绿; 真正可判别面是**序列化格式漂移**。② `P4p` 误以为换工具版本能隔离重审行 —— `derive()` 读的是**现盘文件**。⇒ 已用替代控制(CRLF / 转义 / 缩进)与**逐行变更键集直方图**取证, run1 verdict 另存不覆盖。
2. **AC.6① 原文「(并保留『禁重排』意图)」措辞不准确**: 该断言结构上不承担「禁重排」; 真实保护面 = 序列化格式漂移。收窄后以此为准。
3. **粒度缺口(新识别, 下轮靶点)**: `--apply` 的粒度为**全表 needs_field 重审**(`TOUCHED=104`) ⇒ 单行重审仍必须走块级文本插入; 通路恢复解决的是「**可写**」, 未解决「**可定向**」(候选①-b)。
4. **提交时序语义**: `derive()` 把「已改未提交」的器具判 `live/worktree-only` ⇒ 冻结 pin 只在**提交后**成立; 本轮重审脚本按**文件字节**算 pin(提交后该字节即冻结态)。
5. 本轮只推进一步: 候选②③④⑤⑥⑦ 未动。

### AD.5 下轮候选
1. **候选①-b**: `bind_evidence` 加 `--only <id>` 定向重审(把 TOUCHED 从 104 收窄到目标行); 判据 = 同一行用 `--only` 与块级插入得到**逐字节相同**的登记表。
2. **候选②**: `worktree-only` 6 条陈旧声明清理(零在飞风险、纯 pin 更新)。
3. 候选③ 9 行未派生器具 / 候选④ L2 全量面复跑(需 dotnet 窗口) / 候选⑤⑥ 检查器按面分区 + 新器具进 L2 / 候选⑦ 跨写者提交纪律。
"""


def main():
    # ---- kpi.jsonl ----
    with open(KPI, encoding="utf-8-sig", newline="") as f:
        raw = f.read()
    lines = raw.splitlines()
    last = json.loads(lines[-1])
    if list(ROW.keys()) != list(last.keys()):
        print("SHAPE_MISMATCH old=%s new=%s" % (list(last.keys()), list(ROW.keys()))); return 2
    if any(json.loads(l).get("round") == ROUND for l in lines):
        print("KPI_IDEMPOTENT=OK (round %s 已在台账)" % ROUND)
    else:
        new_line = json.dumps(ROW, ensure_ascii=False)
        out = raw + new_line + "\n"
        with open(KPI, "w", encoding="utf-8", newline="") as f:
            f.write(out)
        back = open(KPI, encoding="utf-8-sig", newline="").read()
        ok_prefix = back.startswith(raw)
        ok_lines = len(back.splitlines()) == len(lines) + 1
        ok_parse = all(json.loads(l) for l in back.splitlines())
        ok_round = json.loads(back.splitlines()[-1]).get("round") == ROUND
        ok_keys = list(json.loads(back.splitlines()[-1]).keys()) == list(last.keys())
        print("KPI_PREFIX_UNCHANGED=%s LINES %d->%d PARSE=%s ROUND=%s KEYS=%s"
              % (ok_prefix, len(lines), len(back.splitlines()), ok_parse, ok_round, ok_keys))
        if not (ok_prefix and ok_lines and ok_parse and ok_round and ok_keys):
            return 2

    # ---- 计划文档附录 AD ----
    doc = open(DOC, encoding="utf-8", newline="").read()
    if "## 附录 AD — EXP1-Q29" in doc:
        print("DOC_IDEMPOTENT=OK (附录 AD 已存在)")
    else:
        with open(DOC, "a", encoding="utf-8", newline="") as f:
            f.write(APPENDIX)
        back = open(DOC, encoding="utf-8", newline="").read()
        print("DOC_APPENDED bytes=%d->%d prefix_unchanged=%s has_AD=%s"
              % (len(doc.encode()), len(back.encode()), back.startswith(doc), "附录 AD" in back))
        if not (back.startswith(doc) and "附录 AD — EXP1-Q29" in back):
            return 2
    print("Q29_APPEND_EXIT=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
