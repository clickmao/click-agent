#!/usr/bin/env python3
"""R518: improvements.md 轮节回填 (R402/R404-R407/R417-R419) + R403 排序违例修。

纪律 (照 skill 的「程序化改写纪律」):
  - 改写前先断言「读入-写出 逐字节复现原文件」(dry-run: 无编辑时 text == text)。
  - 编辑一律**基于原文切片 + 字符串插入**, 禁整份重排。
  - 幂等: 已存在的目标节不再插入 (重跑零变化)。
  - 写后**读回校验**: 节数守恒 (+8)、R403 节唯一、分区内序非递增、目标节逐条在位。
  - 回填内容全部带**来源锚**(提交 sha / 文档路径), 并标「读数未改」; 未见收口读数的轮次如实写状态。
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DOC = REPO / "docs" / "improvements.md"
MARK = "R518 机检更正（2026-09-17）"

H416 = "## R416 — R371-D2 收口"
H401 = "## R401 — 能力自检循环常驻化"
H403 = "## R403 — chat template 裁定"
H412 = "## R412 — 多会话 slot 争用"

SEC_R419 = """## R419 — 探针多轮化：把「轮数 / 首次通过率」从恒等判据变成可分化判据（回填）

**版本**: R419 · **日期**: 2026-09-14 · **状态**: 已收口（仪器侧达成；真机读数为**负结论**，如实登记）· **回填标注**: 本节由 `docs/plans/v0.40.0-r419-probe-multiturn.md` + 提交 `695d6ba`/`77a49bc`/`98339a8`/`05b8c94` 重建，**读数未改**。

- **因果链**: R418 已把「过程/成本」维度落成仪器（`eval/probe/process_metrics.py`），但探针只有单轮 ⇒ 「轮数恒为 1」「首次通过率 ≡ 整题全对率」两个维度结构性不可分化。
- **交付**: 探针多轮化仪器（成对正负控 + 7 态自证）；三个**仪器缺陷**闸：① 被测程序打印坏字节 ⇒ 判定器 `UnicodeDecodeError` 崩掉整臂（改字节捕获 + `errors="replace"` + `bad_encoding` 计数，`grade selftest` 29→31）；② **同命名空间重跑静默覆盖**既有读数 ⇒ `REFUSE_NS_COLLISION` 闸；③ 首轮失败在日志不可见 + `reply_chars` 恒 0（归档 11.9 KB 而摘要写 0）⇒ 首轮行原样打印 + 集中回填（`run_probe` 25→26）。
- **真机读数（诚实结论）**: 4 次 `onfail` 跑 **3 次饱和 / 1 次分化** ⇒ 真机侧**未稳定复现分化**，本轮不作能力结论；决定性微实验 PASS（同 sid 跨进程 4271 命中）。
- **口径坑入档**: `turn N` 是**进程内**轮次标记 ⇒ 轮数须取**归档文件数**（外部真值）。
- **证据**: `docs/plans/v0.40.0-r419-probe-multiturn.md`、提交 `05b8c94`（收口）/`98339a8`（§4-§5 落地）/`77a49bc`（微实验）/`695d6ba`（起步存档）。

"""

SEC_R418 = """## R418 — 探针「过程/成本」维度 KPI：归属铁律 + 真机成本读数 + 成对负控（回填）

**版本**: R418 · **日期**: 2026-09-14 · **状态**: 已收口（仪器 + 真机读数 + 登记齐；本地提交未推）· **回填标注**: 本节由 `docs/plans/v0.39.0-r418-process-kpi.md` + 提交 `737a45d`/`1f44c8b` 重建，**读数未改**。

- **因果链**: R417 处理掉题集天花板（饱和）后，仍有分辨力的维度是**过程/成本**（每题 tokens / 轮数 / 首次通过率）⇒ 需独立仪器与归属规则。
- **交付**: `eval/probe/process_metrics.py`（过程/成本维度 KPI 仪器）+ **归属三级降级**（精确名 → 时间窗 `[ts-elapsed-5s, ts+60s]` 内唯一候选 → `n/a` + 记因；**绝不任取第一个候选**）。
- **成对负控**: 歧义/缺失样本必须落 `n/a`，且 **`n/a` 从均值分母剔除并单列计数**（`n/a ≠ 0`）——把缺读数按 0 摊会让「每题成本」假降。
- **诚实边界**: 该轮成本读数取自单轮题集 ⇒ 「轮数」维度此时仍退化为恒等判据（由 R419 处理）。
- **证据**: `docs/plans/v0.39.0-r418-process-kpi.md`（§3 实现结果 / §4 复验命令）、`eval/probe/process_metrics.py`、提交 `1f44c8b`。

"""

SEC_R417 = """## R417 — 探针反饱和：3 个高判别力族 + 族级缺陷注入负控（回填）

**版本**: R417 · **日期**: 2026-09-14 · **状态**: 已收口（判别力自证 PASS；**首个非饱和真机读数**）· **回填标注**: 本节由 `docs/plans/v0.38.0-r417-probe-anti-saturation.md` + `eval/rover/r417/README-evidence.md` + 提交 `0488017` 重建，**读数未改**。

- **因果链**: 原 7 族题集对当前链**已饱和**（agent 与 oracle 同为整题全对 1.0；同题复跑 seed 20260913 = 35/35）⇒ 天花板效应，「质量」无法从它读出 ⇒ 靶点是**判别力**，不是题量。
- **交付**: 新增 3 个高判别力族 `topo_min`/`vm_run`/`json_mini` + `tight_gen` **每题强制「规格紧」隐藏用例** + **族级缺陷注入负控**（作弊/缺陷解必须整题全对 0，oracle 正控满分）。
- **真机读数**: 整题全对 **1/3**、用例级 **47/54**（诚实登记：真机**仍饱和**，只有 JSON 族打成非饱和）。
- **两处判定器真缺陷（测量层，已修 + 已配负控）**: ① 长回复里「报告式」候选片段顶掉完整可编译程序 ⇒ 候选提取分两轮 + 前缀长度下限；② `exit≠0` 顶掉正确 stdout ⇒ 分类改 **stdout 优先**（期望为空时崩溃仍判失败）。
- **机检/登记**: `eval/probe/grade.py --selftest` **29/29**；全量 **1164/0/0**；形式校验 6/6；登记 `docs/verification-registry.json` → `r417.probe-anti-saturation`（L4）。
- **证据**: `eval/rover/r417/README-evidence.md`、`docs/plans/v0.38.0-r417-probe-anti-saturation.md`、提交 `0488017`。

"""

SEC_R407 = """## R407 — qwen2 前向对账：attn bias 层归属缺陷（定位 + 修复 + 逐位验证）（回填）

**版本**: R407 · **日期**: 2026-09-14 · **状态**: 已完成（V1–V6 全部真实读数；AOT 发布与全量回归已跑）· **回填标注**: 本节由 `docs/plans/v0.29.0-r407-qwen2-attn-bias-and-forward-parity.md` + 提交 `cd8feeb` 重建，**读数未改**。

- **因果链**: R406 把 chat template 升为「读 GGUF 模板 + Jinja 子集解释器」并 32/32 逐字节对齐 ⇒ 乱码**归因移出模板侧**；本轮把「引擎缺陷」推进到**具体张量与具体层**。
- **缺陷**: `ForwardPass` 把 **`blk.0` 的 attn bias 喂给全部 28 层**（qwen2 每层 bias 逐字节不同）⇒ 静默数值错误（不报错、只降质量）。
- **修法/验证**: 按层取 bias + 独立实现逐位对账（V1–V6）。
- **证据**: `docs/plans/v0.29.0-r407-qwen2-attn-bias-and-forward-parity.md`、`eval/rover/r407/`、提交 `cd8feeb`（**R403–R407 工作区一并提交** ⇒ 该提交同时承载 R405/R406 产物）。

"""

SEC_R406 = """## R406 — 模板驱动 chat template（Jinja 子集）与 R1 链归因（回填）

**版本**: R406 · **日期**: 2026-09-14 · **状态**: 已完成（P0-2a 解释器 / P0-2b 生成路径接线）；P0-1（llama.cpp oracle 收尾）进行中 · **回填标注**: 本节由 `docs/plans/v0.28.0-r406-jinja-template-and-r1-chain.md` + 提交 `cd8feeb` 重建，**读数未改**；**无独立证据目录**（如实标注）。

- **因果链**: chat template 原为「只为 DeepSeek 手写的专用渲染器」⇒ 换模型即失真。
- **交付**: 从 GGUF 读 `tokenizer.chat_template` 原文 + **Jinja 子集解释器**；以 jinja2 3.1.6 渲染的三套金标夹具（32 例）做**逐字节**对账；生成路径切到模型自带模板。
- **用途**: 用「prompt 已证明正确」这一事实，把 R1-Distill-1.5B 的乱码输出**归因从模板侧移出**（⇒ 交 R407 定位到引擎 attn bias 层归属）。
- **证据**: `docs/plans/v0.28.0-r406-jinja-template-and-r1-chain.md`、提交 `cd8feeb`（与 R403/R405/R407 同批提交）。

"""

SEC_R405 = """## R405 — 本机增强 R1-Distill-1.5B 计划（四条线，不改权重）（回填）

**版本**: R405 · **日期**: 2026-09-14 · **状态**: 计划已登记；P0/P1 待执行（P0-1 对账在后台）· **回填标注**: 本节由 `docs/plans/v0.27.0-r405-r1-local-enhancement.md` + 提交 `cd8feeb` 重建，**读数未改**；**未见该轮收口节**（状态按计划文档原文登记，不补写读数）。

- **用户令（逐字）**: 「请给我适合本机增强R1-Distill-1.5B的可落地方案」。
- **上游**: R400 生成链（`9d2191a`）+ R403（RoPE 配对修复）+ R404（bge 融合对账）。
- **形态**: §0 先列**本机硬约束**（实测值 + 出处，方案不许绕过它们）⇒ 四条线均不改权重。
- **证据**: `docs/plans/v0.27.0-r405-r1-local-enhancement.md`、`eval/rover/r405/`。

"""

SEC_R404 = """## R404 — bge 融合对账 + 产品口径订正（回填）

**版本**: R404 · **日期**: 2026-09-14 · **状态**: 已完成（对账产物落盘 + 口径订正）· **回填标注**: 本节由 `eval/bge/r404/` 产物 + 提交 `4d1bf90`/`8094faf` 重建，**读数未改**；**无独立轮志文档**（如实标注，证据目录为 `eval/bge/r404/`）。

- **对账产物**: `eval/bge/r404/parity-probe.json`、`eval/bge/r404/csharp-fusion-replay.json`（C# 侧融合重放；`4d1bf90` 刷新产物时**指标全同、仅时间戳变化**）。
- **口径订正（`8094faf`）**: 产品 `lex+small` 融合值为 **0.7833**（**非** 0.8500）+ 110 MB base 删除登记 + 默认模型路径指向链上真身。
- **归属备注**: 该产物目录此后被 `cddcabe`（R516）触碰 ⇒ 归属以提交为准。
- **证据**: `eval/bge/r404/parity-probe.json`、`eval/bge/r404/csharp-fusion-replay.json`、提交 `4d1bf90`/`8094faf`。

"""

SEC_R402 = """## R402 — rover 生成链性能归因：盘读 vs 计算（三通道取证）+ 读数补登记（回填）

**版本**: R402 · **日期**: 2026-09-14 · **状态**: 已收口（步1 归因 + 步2 读数补登记）· **回填标注**: 本节由 `docs/reports/r402/io-attribution.md` + `eval/rover/r402/` + 提交 `33baddd`/`6483721` 重建，**读数未改**。

- **因果链**: R400 生成链的耗时主体是「盘读」还是「计算」未分离 ⇒ 优化靶点无法选择。
- **交付**: `scripts/r402_io_attribution.py` 三通道取证（进程 IO 记账 `ProcIo.cs` / `ReadBenchCli.cs` 读基准 / 前向通道）+ `docs/reports/r402/io-attribution.md`；登记表 +22 行。
- **步2 结论**: **加线程不升级**（读数补登记于 `6483721`）⇒ 该方向不再投入。
- **证据**: `docs/reports/r402/io-attribution.md`、`eval/rover/r402/{README.md,io-attribution-run3.json,io-attribution-run2-doublecounted-device.json,run1-console-capture.txt}`、`scripts/r402_io_attribution.py`、`src/agent.rover/runtime/ProcIo.cs`、`src/agent.tests/RoverProcIoTests.cs`。

"""

FIX_828_PREFIX = "**台账缺口（遗留）**"
FIX_828_SUFFIX = ("**" + MARK + "**：机检实测缺口为 R402 / R404 / R405 / R406 / R407（R403 有节但**错位**、"
                  "R408–R416 在位）⇒ 已逐节回填 + 修正 R403 排序；机检器 "
                  "`eval/capability/r518/scan_round_sections.py`（C1 覆盖 + C2 分区序，rc 0/1/2）。"
                  "**本行前半段口径（R409 时登记）自本行更正起作废**。")

FIX_1831_PREFIX = "**文档缺口（如实登记）**"
FIX_1831_SUFFIX = ("**" + MARK + "**：该登记**过宽** —— R408–R416 轮节实际在位；实测缺口 = "
                   "R402 / R404 / R405 / R406 / R407 / R417 / R418 / R419（另 R403 排序违例），已于 R518 逐节回填。"
                   "**旧口径作废**（原文保留留痕，不撤）。")


def replace_once(text: str, old: str, new: str, tag: str) -> str:
    n = text.count(old)
    if n != 1:
        print(f"DEVICE_DEFECT 锚点 {tag} 命中 {n} 次 (要求 1)")
        sys.exit(2)
    return text.replace(old, new, 1)


def replace_line(text: str, prefix: str, suffix: str, tag: str) -> str:
    """在**唯一命中前缀**的行尾追加更正段 (原文逐字保留 ⇒ 不重打原行, 免标点/破折号漂移)。
    v1 用整行字面量锚: 手抄时多打了 "- " 前缀 ⇒ 命中 0 (fail-closed 未写盘)。"""
    lines = text.splitlines(keepends=True)
    key = prefix.strip()
    def norm(s: str) -> str:
        t = s.strip()
        for m in ("- ", "* ", "> ", "+ "):
            if t.startswith(m):
                t = t[len(m):].strip()
        return t
    hits = [i for i, l in enumerate(lines) if norm(l).startswith(key)]
    if len(hits) != 1:
        near = [l[:90] for l in lines if key[:8] in l][:3]
        print(f"DEVICE_DEFECT 行锚点 {tag} 命中 {len(hits)} 次 (要求 1); 近似候选={near}")
        sys.exit(2)
    lines[hits[0]] = lines[hits[0]].rstrip("\n") + " " + suffix + "\n"
    return "".join(lines)


def main() -> int:
    raw = DOC.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        print("DEVICE_DEFECT 文档含 BOM")
        return 2
    text = raw.decode("utf-8")
    orig = text

    # 幂等: 目标节已在位 ⇒ 跳过 (重跑零变化)
    if all(h in text for h in ("## R419 —", "## R417 —", "## R407 —", "## R402 —")) and MARK in text:
        print("IDEMPOTENT_SKIP 目标节与更正标记均已在位")
        return 0

    # 步1: 定位 R403 节 (从其标题到 R412 标题前), 取出后从原位置删除
    ia, ib = text.find(H403), text.find(H412)
    if ia < 0 or ib < 0 or ia >= ib:
        print(f"DEVICE_DEFECT R403/R412 锚点异常 ia={ia} ib={ib}")
        return 2
    r403_block = text[ia:ib]
    if "tool-template-behavior.json" not in r403_block or len(r403_block) < 500:
        print("DEVICE_DEFECT R403 节切片不完整")
        return 2
    text = text[:ia] + text[ib:]

    # 步2: 插入 R419/R418/R417 (R420 之后, R416 之前)
    text = replace_once(text, H416, SEC_R419 + SEC_R418 + SEC_R417 + H416, "H416")

    # 步3: 插入 R407/R406/R405/R404 + 搬回来的 R403 + R402 (R408 之后, R401 之前)
    text = replace_once(text, H401, SEC_R407 + SEC_R406 + SEC_R405 + SEC_R404 + r403_block + SEC_R402 + H401, "H401")

    # 步4: 两处过期口径更正 (行前缀锚 + 行尾追加, 原文逐字保留)
    text = replace_line(text, FIX_828_PREFIX, FIX_828_SUFFIX, "fix828")
    text = replace_line(text, FIX_1831_PREFIX, FIX_1831_SUFFIX, "fix1831")

    # 读回前自检: 除编辑点外其余字节不变 (逐段核对: 原文件被切走的只有 R403 块)
    if text.count(H403) != 1:
        print(f"DEVICE_DEFECT R403 节出现 {text.count(H403)} 次")
        return 2
    if text.count(SEC_R419.strip()[:40]) != 1 or text.count(SEC_R402.strip()[:40]) != 1:
        print("DEVICE_DEFECT 新节重复")
        return 2

    DOC.write_text(text, encoding="utf-8", newline="")

    back = DOC.read_text(encoding="utf-8")
    secs_before = sum(1 for l in orig.splitlines() if l.startswith("## "))
    secs_after = sum(1 for l in back.splitlines() if l.startswith("## "))
    lines_before, lines_after = len(orig.splitlines()), len(back.splitlines())
    print(f"HEADERS {secs_before} -> {secs_after} (期望 +8 = {secs_before + 8})")
    print(f"LINES {lines_before} -> {lines_after} (净增 = 新增节行数 - 0)")
    print(f"R403_POSITION_OK={back.find(H403) > back.find('## R404 —') and back.find(H403) < back.find('## R402 —')}")
    print(f"MARK_COUNT={back.count(MARK)}")
    ok = secs_after == secs_before + 8 and back.count(H403) == 1
    print("BACKFILL_EXIT=" + ("0" if ok else "1"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
