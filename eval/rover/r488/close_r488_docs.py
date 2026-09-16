#!/usr/bin/env python3
# R488 收口: 把 R488 段追加/替换进 docs/reports/iteration-master-plan.md,
# 索引表**机取自** docs/verification-registry.json (owner_round==R488, 禁手改), 并打印覆盖自检。
# 幂等: 段已存在则整段替换 (从 '## R488（' 到文件尾); 保形: 段间空行 1。
import io, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PLAN = os.path.join(ROOT, 'docs', 'reports', 'iteration-master-plan.md')
REG = os.path.join(ROOT, 'docs', 'verification-registry.json')

NARR = """## R488（2026-09-16）真机 2×2 析因消融 + 候选④ TAG 修复 — **主 KPI 首次达线（token −33.28%）**，质量面判负

- 靶点：R413 验收②③。R487 判负但**同时翻 `turn_gate`/`repeat_skip` 两开关 ⇒ 无因果分离**，其归因（剩余调用上下文变长）从未被验证。
- 设计（为什么是 2×2）：同刻四臂 `B`(off,off) / `G`(on,off) / `S`(off,on) / `R`(on,on)，**同一二进制** `/tmp/pub_r485/agenthost`
  （sha256 `03c77d56e8c485af…` = R485 AOT pin，15,363,728 B，IL 警告 0）+ 同夹具 + 同 key + 同内存闸；`git status --porcelain -- src/` 空
  ⇒ **零 C# 改动 ⇒ 差分只能归因开关**（不能归因二进制）。
- 真跑：`bash eval/rover/r488/run_both_r488.sh` ⇒ **rc=0 / ALLDONE 12:35:19**，四臂各 12 轮（本地中继 → 真供应商，`blocked=0`×4）。
- 读数（供应商 usage 真值列）：B **15 调用 / 70,944 tok**；G **12 / 58,130**（**−18.06%**）；S **14 / 66,396**（**−6.41%**）；R **11 / 47,333**（**−33.28%**，调用 −26.67%）。
- 判据：**H1 主 KPI PASS**（B→R −33.28% ⇒ **首次 ≥30%**）· **H2 FAIL（方向被证伪）**（gate 单独 prompt/调用 4,392.1→4,395.2 = **+3.1** ⇒ R487 归因不成立）
  · H3 PASS · **H4 FAIL**（可加性残差 **−6,249 = −8.81% of B**，超加性 ⇒ 禁由单开关相加外推）· **H5 FAIL(R/G)**（去重答复 R **7/12**、G 9/12）
  · H6 **PASS×4**（臂自身 usage 15/12/14/11 行 == 中继真值列）· **H0 FAIL**（跨轮锚漂移 **11.15%** ⇒ 本轮只同刻差分，不与 R487 相减）。
- 质量细读（R 臂逐字）：t2–t5 = **同一句 21 字模板**「收到，继续按当前方向推进，本轮不重新规划。」（4 轮，**未声明为本地 skip**）+ t6 逐字=t1、t9 逐字=t8（复述回放）
  ⇒ 实质轮 **6/12** ⇒ **−33.28% 主要由模板通道买来**；⇒ **验收②达成、验收③质量面未达成**。
- 归因：达线靠 `turn_gate`（单独 −18.06%），`repeat_skip` 质量安全但只 −6.41%；叠加 −33.28% 且质量 7/12 ⇒ 下一步靶点 = **不降质的上下文剪裁/前缀复用**。
- 候选④（修复）：relay / tel / telcount 命名并入 TAG ⇒ 四臂真值列**逐臂非空**（修前 `Arole485`/`R485` 为 **0 字节**、真值落共用名）。
- 候选⑦：`eval/rover/r488/derive_r488.py` 由 r487 臂执行器**机派生** r488 臂与驱动器（逐条计数断言，不符即 rc=2 **且不写盘**；首跑即拦下 both 脚本第 16 行文本不符 ⇒ 修表后重跑）+ 残留机检 6 项 + `bash -n`。
- 候选⑥：对侧 R486 确定性桩差分器具**首次真跑** + 修命名缺陷（`check_r486.py` TAGS `pre-empt/post-empt` vs 运行器 `TAG=$ARM-$(cut -c1-5)` ⇒ `*-empty`；修前只读 2/4 臂、**恒 rc=3 缺输入**）
  ⇒ 真跑 rc=0、判据 rc=1：**H1/H3/H4 FAIL**（pre_empty 1 vs post_empty 1，delta 0）· H2/NC1 PASS ⇒ **差分未复现**（夹具 `AGENTFRAMEWORK_ACTION_LOOP=off`），**不据此宣称修复生效/失效**（预注册前提被证伪 ⇒ 宣称收窄）。
  真机空正文基数（真值列）：全调用 B 3/15 · G 4/12 · S 2/14 · R 5/11；剔前 2 次结构性调用 ⇒ B 1/13 · G 2/10 · S 0/12 · **R 3/9**。
- 环境事件：起手闸 **fail-closed 两次拒跑**（MemAvailable 2,614 / 2,640 MB < 2,650 MB，闸单一源、臂内零手抄阈值）⇒ 释放闲置孤儿 `pyright-langserver`
  （6 s CPU tick 0 / socket 0 / RSS 345 MB）+ `drop_caches` ⇒ **2,987 MB PASS**；全程未杀在跑作业。
- 诚实边界：单夹具单次（n=12，**无置信区间**）；跨轮**不可比**（H0 FAIL；R487 `R485`=81,770 与本轮 `Rr`=47,333 **同臂参差 −42.1%** ⇒ 主臂读数不稳定，只报 L2 级）；
  ②上下文剪裁 / ③skip 显式声明 / ⑤R479 遗留**未做**（三者都改链代码 ⇒ 换被测二进制，与本轮真机臂窗口互斥）；未改 C# ⇒ 未重发布 AOT；未 push。
- registry：本轮 +3 行（`updated_round=R488`）。

### R488 · 轮次索引增量（机取自 `docs/verification-registry.json`，禁手改）
"""


def main():
    reg = json.load(io.open(REG, encoding='utf-8'))
    rows = [r for r in reg['rows'] if r.get('owner_round') == 'R488']
    rows.sort(key=lambda r: r['id'])
    lines = []
    for r in rows:
        cap = r['capability'].replace('\n', ' ')
        lines.append("| %s | `%s` | %s | %s … |" % (r['owner_round'], r['id'], r['level'], cap[:90]))
    body = NARR + "\n" + "\n".join(lines) + "\n\n"
    rounds = sorted({r['owner_round'] for r in reg['rows']})
    body += ("覆盖自检: 轮号 %s；registry rows=%d，updated_round=%s。\n" % (rounds, len(reg['rows']), reg['updated_round']))
    miss = [x for x in ('R488',) if x not in rounds]
    body += "**缺登记行轮号: %s**\n" % ("无" if not miss else ",".join(miss))

    txt = io.open(PLAN, encoding='utf-8').read()
    m = re.search(r'^## R488（', txt, re.M)
    if m:
        txt = txt[:m.start()]
    while not txt.endswith('\n\n'):
        txt += '\n'
    io.open(PLAN, 'w', encoding='utf-8').write(txt + body)
    print(json.dumps({"rows_machined": len(rows), "registry_rows": len(reg['rows']),
                      "replaced": bool(m), "plan_lines": len(io.open(PLAN, encoding='utf-8').read().splitlines())},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
