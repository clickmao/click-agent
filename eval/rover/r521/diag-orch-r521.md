# R521 候选② · 编排臂 9/58 逐用例定因 (机检读数)

**来源**: 快照 `eval/rover/r521/snapshots/w1/agentO/g1` (R520 影子路径闸修复后的第一份编排产物, n1–n5 全 Completed) + 判据 `eval/rover/r521/cases/cases-r521.json`。
**判分**: `python3 eval/rover/r519/grade_r519.py --dir <snapshot> --out ...` ⇒ **9/58** (life 0/14 · sub 0/14 · nim 5/15 · wythoff 4/15; 49 败 = 44× `stdout 不匹配` + 5× `rc=1`)。
**文件面**: 5 个模块**都在** (`games/{__init__,life,sub,nim,wythoff,__main__}.py`) ⇒ **不是缺产物**, 是实现/契约错。

## 逐模块定因 (公开用例首例, 逐位对读)

| 模块 | rc | 期望 | 实测 | 定因类 |
|---|---|---|---|---|
| life | 0 | `...../...../...../.###./…` | `00000/00000/00000/01110/…` | **输出字母表错**: 演化**正确** (`01110`≡`.###.`), 只把 `#`/`.` 写成 `1`/`0` ⇒ 14/14 全灭 |
| sub | 1 | `WIN 6` | (空) `IndexError: list index out of range` | **输入解析崩溃**: 未跳过首行 `31 3` (n k) ⇒ 14/14 全灭 |
| nim | 0 | `WIN 2 8` | `WIN 1 8` | **规范解错**: 取法本身是必胜着法, 但堆号取 `1` 而非 `2` (「堆号最小」语义) ⇒ 10/15 败 |
| wythoff | 0 | `WIN 15 15` | `WIN` | **输出截断**: 只印 `WIN`, 丢两个整数 (必胜着法未落盘) ⇒ 11/15 败 |

## 结论 (可操作)

编排臂本窗失败面**主要是接口契约**(字母表 / 首行跳过 / 着法规范形 / 字段完整), **不是算法不会**:
- 算法面证据: life 演化逐位正确; nim 找到的 `1 8` 是**合法**必胜着法 (只是非规范最小解)。
- ⇒ 下一轮候选: 把「输出契约」写进节点提示/验收 (R520 已加第 5 条纪律, 建议再加**逐模块 I/O 契约自测**), 预期可把 9/58 抬到算法面真实水位。

## 复现命令

```bash
python3 eval/rover/r519/grade_r519.py --dir eval/rover/r521/snapshots/w1/agentO/g1 --out /tmp/o.json
python3 -c "import json,io;print(json.load(io.open('/tmp/o.json',encoding='utf-8'))['passed'])"
```
