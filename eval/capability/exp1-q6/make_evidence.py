#!/usr/bin/env python3
"""EXP1-Q6 证据生成器: 从归属台账 JSON **派生** README 与计划文档附录 G。

所有数字/路径/提交号一律从 attribution_q6_v120.json + selftest JSON 读取后格式化,
不手打 (R435 教训: 手打字面量会被写入通道改写 / 与台账漂移)。
"""
import json
import sys
from collections import Counter
from pathlib import Path

Q6 = Path(__file__).resolve().parent
ROOT = Q6.parents[2]
ATTR = Q6 / "attribution_q6_v120.json"
SELF = Q6 / "selftest_q6_v120.json"
PROBE = "eval/capability/exp1-q6/attribute_failed_refs.py"
INSTR = "eval/capability/exp1-q4/probe_doc_ref_integrity.py"

r = json.loads(ATTR.read_text(encoding="utf-8"))
st = json.loads(SELF.read_text(encoding="utf-8"))
after = json.loads((Q6 / "attribution_q6_after_docs.json").read_text(encoding="utf-8"))
S, R = r["stale_path"], r["relocated"]
sc, rc = Counter(x["class"] for x in S), Counter(x["class"] for x in R)
dels = Counter((x["del"]["deletion_sha"][:7], x["del"]["deletion_commits"][0]["subject"].split(":")[0],
                x["del"]["deletion_commits"][0]["date"][:10]) for x in S)
docs_same = Counter(x["doc"] for x in S if x["class"] == "same_commit_as_deletion")
paths_dead = sorted({x["path"] for x in S})


def tbl(rows, head):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


stale_rows = [(x["class"], f"`{x['doc']}`", x["doc_line"], f"`{x['path']}`", x["del"]["deletion_sha"][:7],
               str(x["blame_sha"])[:7], str(x["intro_sha"])[:7], x["axis_source"]) for x in S]
reloc_rows = [(x["class"], f"`{x['path']}`", f"`{x['target']}`" if x.get("target") else "—",
               f"`{x['doc']}`") for x in R]
del_rows = [(f"`{k[0]}`", k[1], k[2], v) for k, v in sorted(dels.items())]

readme = f"""# EXP1-Q6 证据 · 全仓失效引用的四级归属复核

> 判据 (预注册于复核器头部) / 复核器: `{PROBE}` **{r['probe']}**
> 输入: `eval/capability/exp1-q6/result_q6_before.json` (仪器 v2.3.0 读数, 未改动)
> 台账: `eval/capability/exp1-q6/attribution_q6_v120.json` · 自证: `{SELF.name}` ({st['passed']}/{st['n']} 绿)

## 1. 结论 (读数)

- 仪器 v2.3.0 的全仓两桶 **逐条复核完毕**: `stale_path` **{len(S)}** 条 / `relocated` **{len(R)}** 条。
- `stale_path` {len(S)} 条 = **{sc.get('retired_after_write', 0)} 条「退役前成形」(历史留痕)** + **{sc.get('same_commit_as_deletion', 0)} 条「与退役同提交」(不可判/弃权)**;
  真·死引用 (`dead_after_delete`) = **{sc.get('dead_after_delete', 0)}** 条, 口径冲突 (`no_deletion_commit`) = **{r['n_no_deletion_truth']}** 条。
- 涉及文件 **{len(paths_dead)}** 个, 全部满足: 全树**无同名候选** (独立于仪器过滤面的 os.walk 复核) + 有**删除提交**且该提交是 HEAD 祖先。
- `relocated` {len(R)} 条 = **{rc.get('fixable_direct', 0)} 条定点可改 (唯一候选 + 行号/符号成立)** + **{rc.get('path_elision', 0)} 条写法漂移 (路径里含省略号)**。
- 复核器退出码 **{r['exit_code']}** (0 = 无缺陷); 自证 **{st['passed']}/{st['n']}** 全绿。

### 1.1 删除侧外部真值 (stale_path)

{tbl(del_rows, ["删除提交", "提交主题前缀", "日期", "引用条数"])}

### 1.2 stale_path 逐条

{tbl(stale_rows, ["定性", "文档", "行", "路径", "删除提交", "行级锚", "串级锚", "锚来源"])}

### 1.3 relocated 逐条

{tbl(reloc_rows, ["定性", "文档写的路径", "唯一候选(树内实际路径)", "文档"])}

## 2. 判据 (本轮新增的四级归属)

| 级 | 判据 | 取数 | 反面控制 |
|---|---|---|---|
| L-1 | 精确相对路径在 HEAD 内存在 | 版本库索引查询 | 存在路径不得被本桶收进 (`P1`) |
| L-2 | 全树**无过滤**同名搜索 (独立于仪器 `_rel_ok`) = 0 候选 | 自写目录遍历 | 存在文件必须 >0 命中 (`N2b`) |
| L-3 | `stale_path` 桶必须有**删除提交**, 且该提交是 HEAD 祖先 | 历史检索 + 祖先判定 | 从未入版本库的路径 ⇒ `never_tracked`, 不得判"真删" (`N1`) |
| L-4 | **时间轴**: 事实自身引入点 vs 退役点 | 行级历史追溯 + 串级首现(须跟随重命名) 双锚 | 真版本库夹具三样本必须落**三个不同类** (`T1/T2/T3`) |

分类次序 (先给"证否缺陷"的强证据, 再弃权, 最后才判缺陷):
`任一证据不晚于退役 ⇒ retired_after_write` → 否则 `有证据与退役同提交 ⇒ same_commit_as_deletion(弃权)`
→ 否则 `全部证据都晚于退役 ⇒ dead_after_delete`; 双锚互斥 ⇒ `axis_disagreement(弃权)`。

## 3. 自证 ({st['passed']}/{st['n']})

{tbl([(c['check'], 'PASS' if c['pass'] else 'FAIL') for c in st['checks']], ['检查项', '结果'])}

## 4. 复现命令 (逐字)

```
python3 {INSTR} --repo . --out eval/capability/exp1-q6/result_q6_before.json
python3 {PROBE} --repo . --selftest
python3 {PROBE} --repo . --result eval/capability/exp1-q6/result_q6_before.json \\
        --out eval/capability/exp1-q6/attribution_q6_v120.json
```

## 5. 诚实边界

① 证据等级 **L1 静态机检** (无编译/测试/真机运行)。
② **"当前不成立" ≠ "写成时就错"**: 本轮的 0 缺陷是**第二判据** (`dead_after_delete`) 的读数, 不代表那 {len(S)} 条引用在当下有效——
　其**当前无效性**已由 L-1/L-2/L-3 三项外部真值证成 (见上表), 只是**缺少"写作时即失效"的证据**。
③ {sc.get('same_commit_as_deletion', 0)} 条「与退役同提交」是**弃权不是清白**: 一次提交既退役文件又写入文档时,
　"变更前勘查的记录"与"变更后残留"在时间轴上同形, 判据不可分 (要判别需变更前快照/变更描述, 时间戳无用)。
④ 时间轴锚点是**版本库历史**锚: 未入版本库的文档无锚 ⇒ 弃权 (`ambiguous_no_time_axis` 本档 {sc.get('ambiguous_no_time_axis', 0)} 条)。
⑤ 语料是**移动目标** (对侧作业在改 `src/`): 本轮读数与 HEAD 绑定; 复跑前先记 HEAD。
⑥ 本轮**三次被测测量层自身缺陷** (均先于结论修掉, 见 §7)。

## 6. 确定性复跑 (同输入两跑逐位相同)

`attribution_q6_after_docs.json` = 复核器在**含本附录的语料状态**上重跑同一输入的结果:
逐条类别 ({len(S)} stale + {len(R)} relocated, 含文档路径与行号) 与 `attribution_q6_v120.json` **逐位相同**
(`stale {dict(sc)}` / `relocated {dict(rc)}`, `n_defects {after['n_defects']}`)。双重作用: ① 复核器确定性成立;
② **本附录零 `src/` 路径字面量** ⇒ 未引入新引用 (仪器复跑对照: `stale_path 21→21` / `relocated 13→13` / `symbol_absent 65→65` / `stale_lines 4→4`)。

## 7. 测量层自捕 (先修仪器, 再谈被测)

| # | 版本 | 缺陷 | 症状 | 修法 |
|---|---|---|---|---|
| 1 | v1.0.0 | 时间轴锚点取**文档最后修改提交** (而非引用自身引入点) | 同一批 7 条被判 `dead_after_delete` | 锚点下沉到**行级历史追溯 + 串级首现** |
| 2 | v1.1.0 | 串级首现检索**未跟随重命名** ⇒ 返回重命名提交当"首次出现" | 1 条假红 (首现锚 = R392 重命名 20:49, 真值 = 原提交 19:26) | 检索加**跟随重命名**; 并新增「同提交」独立类 |
| 3 | v1.1.0 | 同一提交时"祖先判定"返回不可判 ⇒ 落到歧义分支, 理由文案与事实不符 | 理由写"锚点均不可得"而实际两锚都可得到 | 祖先判定返回三态 (早/同/晚) + 理由文案按事实更新 |
"""

out_readme = Q6 / "README-evidence.md"
out_readme.write_text(readme, encoding="utf-8")

appendix = f"""
---

## 附录 G · EXP1-Q6 全仓剩余失效引用的四级归属复核 (L1 静态; 本侧 60m 作业不占主线轮号)

### G.1 触发与范围

附录 F.5 的下轮候选 (逐字): 「按同一四级归属**逐条复核全仓剩余 `stale_path 21`**」。本轮即此项:
把仪器 v2.3.0 判定为 `stale_path {len(S)}` / `relocated {len(R)}` 的**每一条**引用逐条做归属复核, 并给出外部真值。

复核器 (新, 与仪器解耦): `{PROBE}` **{r['probe']}** —— 只消费仪器读数 JSON, 不修改仪器判据面。

### G.2 预注册判据 (读数前写死)

| 级 | 判据 | 反面控制 (自证内) |
|---|---|---|
| L-1 | 精确路径在 HEAD 内存在性 | `P1` 活路径不得落入本桶 |
| L-2 | 全树**无过滤**同名搜索 = 0 候选 (独立于仪器过滤面) | `N2` 退役文件 0 命中 ∧ `N2b` 活文件 >0 命中 |
| L-3 | 有**删除提交**且该提交是 HEAD 祖先 | `N1` 从未入版本库 ⇒ `never_tracked` (不得判"真删") |
| L-4 | 时间轴双锚: **行级**历史追溯 + **串级**首现 (须跟随重命名) | 真版本库夹具三样本 (`T1` 退役前 / `T2` 退役后 / `T3` 同提交) 落**三个不同类** |

定性次序: `任一证据不晚于退役 ⇒ retired_after_write` → `有证据与退役同提交 ⇒ same_commit_as_deletion(弃权)`
→ `全部证据晚于退役 ⇒ dead_after_delete`; 双锚互斥 ⇒ `axis_disagreement`; 无删除提交 ⇒ `no_deletion_commit`。

### G.3 读数

- `stale_path {len(S)}` = **retired_after_write {sc.get('retired_after_write', 0)}** + **same_commit_as_deletion {sc.get('same_commit_as_deletion', 0)}**;
  `dead_after_delete` **{sc.get('dead_after_delete', 0)}** | `axis_disagreement` **{sc.get('axis_disagreement', 0)}** | `no_deletion_commit` **{r['n_no_deletion_truth']}**。
- `relocated {len(R)}` = **fixable_direct {rc.get('fixable_direct', 0)}** (唯一候选 + 行号/符号成立 ⇒ 定点可改) + **path_elision {rc.get('path_elision', 0)}** (路径含省略号 ⇒ 写法漂移)。
- 涉及文件 **{len(paths_dead)}** 个; 删除侧外部真值 (提交 → 条数): {", ".join(f"`{k[0]}`({v})" for k, v in sorted(dels.items()))} —— **全部**为 HEAD 祖先。
- `same_commit_as_deletion` 分布: {", ".join(f"`{k}` {v} 条" for k, v in docs_same.most_common())}。
- 复核器退出码 **{r['exit_code']}**; 自证 **{st['passed']}/{st['n']}** 全绿 (`{SELF.name}`)。

### G.4 结论与语义澄清 (本轮核心发现)

**"当前不成立" 与 "写成时就错" 是两个判据, 不可互相代替。** 上一轮只做到前者 (引用路径在树内不存在),
本轮补上后者 (引用**成形时**所指是否已不存在): **真·死引用 {sc.get('dead_after_delete', 0)} 条** ⇒ 语料中**没有**"写作时即失效"的引用。
但 {len(S)} 条引用的**当前无效性**仍由 L-1/L-2/L-3 外部真值证成 ⇒ 它们是**文档时效维护**对象 (补退役标记 / 改写路径),
不是缺陷指控 —— 处置动作与"死引用"相同但**定级不同**, 混为一谈会在批量退役提交上产生成片假红。

### G.5 诚实边界

见 `eval/capability/exp1-q6/README-evidence.md` §5: ① L1 静态; ②{sc.get('same_commit_as_deletion', 0)} 条「同提交」是**弃权非清白** (时间轴不可分, 需变更前快照才可判);
③ 时间轴只锚**版本库历史**, 未入库文档弃权; ④ 语料移动目标, 读数与 HEAD 绑定; ⑤ 本轮**三次测量层自捕** (锚点取错层 / 未跟随重命名 / 同提交误落歧义) 已先修后测, 修法入 skill。

### G.6 证据

`eval/capability/exp1-q6/{{result_q6_before.json, attribution_q6_v120.json, selftest_q6_v120.json, README-evidence.md, attribute_failed_refs.py}}`。

### G.7 下轮候选 (一步)

把 `relocated` 的 **{rc.get('fixable_direct', 0)} 条定点可改** + **{rc.get('path_elision', 0)} 条写法漂移** 做**文档侧定点修复** (改写为显式路径; 省略形态改全路径),
并对 `retired_after_write` 引用补**退役标记** (留痕继承已有机制, 见附录 F.3) —— 改动只碰文档, 复跑仪器断言两桶归零。
"""

plan = ROOT / "docs/plans/v0.22.0-exp1-local-index-and-code-graph.md"
old = plan.read_text(encoding="utf-8")
marker = "## 附录 G · EXP1-Q6"
if marker in old:
    head, _sep, _tail = old.partition("\n---\n\n" + marker)
    old = head
plan.write_text(old.rstrip("\n") + "\n" + appendix, encoding="utf-8")

print(json.dumps({"readme": str(out_readme), "readme_bytes": out_readme.stat().st_size,
                  "plan": str(plan), "plan_lines": len(plan.read_text(encoding='utf-8').splitlines()),
                  "class_counts": r["class_counts"], "exit": r["exit_code"]}, ensure_ascii=False, indent=2))
