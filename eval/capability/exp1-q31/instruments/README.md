# EXP1-Q31 器具纪律 (长驻 L2 面器具)

本目录 = 长驻器具 (`face_cap_headroom.py` / `only_equivalence_guard.py` / `retired_interop_*` 等),
每轮被 L2 器具验收面 (`eval/capability/instruments_check.py`) 全量调起。**改这里 = 改面** ⇒ 器具 sha 变,
登记表 pin 与面记录 L2 字段必须同轮同步 (器具**定稿之后**一次同步, 不是改一次同步一次 —— EXP1-Q35 实测
第二次漂移被面记录 `l2_fields.instrument_sha12: DRIFT` 逮住)。

## 1. 面记录的可比性纪律 (EXP1-Q36 定稿)

1. **同名重跑 + 窗口零仓内写入**: 需要「同树态逐跑比对」时, 连续多跑必须
   ①同一工作目录名 (目录名会进 prompt/记录 ⇒ 命名噪声) ②窗口内本侧零仓内写入
   ③**驱动日志与面记录一律落仓外** (`/tmp/<round>_face_<tag>.{json,out,runtime.json}`)。
   仓内日志会在闸内被正确归类为 `foreign_writes` (T1–T3 实测), 于是「干净窗口」前提不成立。
2. **跑前占用核验**: 同 gateway 的前端循环与兄弟作业共享本工作树 (实测 EXP1-Q36 T9 窗口内有前端 R494
   会话写 `eval/rover/r494/*` 与 `eval/bge/r404/*`)。跑面之前先核验占用**并落盘再读**
   (工具回显长输出会被截断成一行 ⇒ 误判空闲); 有兄弟写者在飞 ⇒ 要么有界等待, 要么照跑并把结果标为
   「窗口不纯」, **不得**把该跑当成干净基线。
3. **pin 需重取的条件**: 面记录的 `side_effect_attribution.{foreign_writes, old_gate_delta,
   old_gate_false_reds}` 任一非空 ∧/或 `census_in_repo_cwd` 计数变 ⇒ 该轮窗口不纯 ⇒ 绑在该面记录上的
   `pin_kind=semantic-projection` 摘要**需重取** (不是缺陷, 是窗口不纯的可见痕迹)。
   口径声明见 `eval/capability/projection_rules.json :: clean_window_condition`。

## 2. 投影遮蔽的边界 (谁可以遮、谁不可以)

- **可以遮**: 运行期/环境/身份读数 —— 墙钟、随机目录、进程 pid、窗口内他人写入与既有文件成员、由其派生的计数、
  扫描派生量 (commands/events/raw_events/raw_paths_n)。
- **不可以遮**: 器具行为面 —— `results[*]` 的逐条裁决/rc/证据 sha/负控、`side_effects` (自身脏路径)、
  `side_effect_attribution.{verdict,red,measurement_ok,reasons}`、`conservation.ok`。
- **唯一例外 (成员级、按身份枚举)**: `results[*]` 中 id ∈ {`bind_evidence.check`,
  `bind_evidence.committed-state`} 两个**自指成员** —— 其真值随**树态**翻转 (提交前 rc=2 / 提交后 rc=0,
  实测 T1..T3 vs T4..T7), 冻结它等于冻结一个非器物量。它们是**枚举**而非模式匹配, 且其真值由
  `eval/capability/exp1-q30/check_committed_state_q30.py` 在提交后独立判定。
- 新增遮蔽族必须先有**实测差分**依据 (同树态重跑差异叶), 并把依据与理由写进规则条目的 `basis`。

## 3. 判定器/反证的最小判别力

- 反证类检查 (「作用域收窄非空转」「未 inject 必红」) 必须在**前置条件可满足**的状态下设计:
  在刚 repin 完的表上要求「全表 apply 与定向 apply 字节不同」= 恒红且无判别力 (EXP1-Q35 实测)。
  修法 = scratch 副本里**再注入一行待派生** (EXP1-Q36 `pick_second_anchor`/`break_pin`), 令反证前提必然成立。
- 台账类器具的**轮号必须参数化**: 行内轮号硬编码会把本轮读数记到旧轮名下 (归属错标),
  `--append` 缺轮号必须 fail-closed 拒跑, 幂等键必须含轮号。
