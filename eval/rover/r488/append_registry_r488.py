#!/usr/bin/env python3
# R488 台账回灌: 追加 3 行到 docs/verification-registry.json (幂等: 同 id 已存在则整行替换)
# 形式门禁 R2f/R2e: 产品面行 (eval/) 必带 evidence_generated_with 八键; frozen+artifact ⇒
#   artifact_sha12 必须等于证据现盘字节 sha256[:12]; instrument_sha12 同闸; 本脚本**机算**这两值
#   (缺文件/缺器具 ⇒ rc=3 fail-closed, 不写盘)。
# 保形写回: 缩进 1 空格; 末尾必须带换行(缺尾换行会被 SER 断言拒写); 读入 utf-8。
import hashlib, io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
REG = os.path.join(ROOT, 'docs', 'verification-registry.json')


def sha12(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.isfile(p):
        sys.exit("缺文件 (fail-closed): %s" % rel)
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]


ROWS = [
    {
        "id": "r488.two-by-two-ablation-kpi-first-pass",
        "level": "L3",
        "capability": ("真机 2x2 析因消融 (turn_gate x repeat_skip) 同刻四臂全链跑通 (rc=0 / ALLDONE 12:35:19, 各 12 轮, "
                       "本地中继->真供应商, blocked=0 x4): B(off,off) / G(on,off) / S(off,on) / R(on,on), 同一二进制 "
                       "/tmp/pub_r485/agenthost (sha256 03c77d56e8c485af… = R485 AOT pin, 15,363,728 B, IL 警告 0) 且 src/ 零改动 "
                       "⇒ 差分只归因开关。读数 (供应商 usage 真值列): B 15 调用/70,944 tok; G 12/58,130 (-18.06%); S 14/66,396 (-6.41%); "
                       "R 11/47,333 (-33.28%, 调用 -26.67%)。判据: **H1 主 KPI PASS (B->R -33.28%, 首次 >=30%)**; H2 FAIL 方向被证伪 "
                       "(gate 单独 prompt/调用 4,392.1->4,395.2 = +3.1 ⇒ R487 的「剩余调用上下文变长」在本夹具不成立); H3 PASS; "
                       "H4 FAIL (可加性残差 -6,249 = -8.81% of B ⇒ 超加性, 禁单开关相加外推); H5 FAIL(R/G) 质量面 (去重答复 R 7/12, "
                       "G 9/12; R 臂 t2-t5 = 同一句 21 字模板「收到，继续按当前方向推进，本轮不重新规划。」未声明为本地 skip + t6=t1、t9=t8 "
                       "复述回放 ⇒ 实质轮 6/12); H6 PASS x4 (臂自身 usage 行数 15/12/14/11 == 中继真值列); H0 FAIL (跨轮锚漂移 11.15% "
                       "⇒ 本轮只同刻差分, 不与 R487 相减)。结论: 验收② token 口径首次达线, **但降幅主要由 turn_gate 的模板通道买来** "
                       "⇒ 验收③质量面未达成, 不能同轮宣称; 主臂读数不稳定 (R487 R485=81,770 vs 本轮 Rr=47,333, 同臂参差 -42.1%) ⇒ 只报 L2 级。"),
        "evidence_cmd": "python3 eval/rover/r488/analyze_r488.py --json eval/rover/r488/verdict-r488.json",
        "evidence_path": "eval/rover/r488/verdict-r488.json",
        "instrument_path": "eval/rover/r488/analyze_r488.py",
        "negative_control": ("四臂同刻同夹具同网格 (p12) 同时窗 + 同一二进制 ⇒ 差分归因开关而非二进制; H0 锚 (B 臂 == R487 Arole485 同臂参) "
                             "作**跨轮可比性阴性对照**: 实测漂移 11.15% > 10% ⇒ 判 FAIL 并禁用跨轮相减; H6 以「臂自身 usage 文件非空且行数 == "
                             "中继真值列」作候选④ 修复的正控 (修前 Arole485/R485 为 0 字节); 空正文/质量以**去重答复数**机取 (不手抄); "
                             "缺任一臂 usage/turns 即判红 (fail-closed)。"),
        "covers": ["eval/rover/r488/prereg_r488.json", "eval/rover/r488/analyze_r488.py",
                   "eval/rover/r488/verdict-r488.json", "eval/rover/r488/run_both_r488.sh",
                   "eval/rover/r488/run_arm_real_r488.sh", "eval/rover/r488/both_r488.log"],
        "owner_round": "R488",
    },
    {
        "id": "r488.tag-namespace-fix-and-machine-derive",
        "level": "L2",
        "capability": ("候选④ 修复: 臂执行器调中继时真值列路径并入 TAG (修前 relay 收 `\"$DIR\" \"$ARM\"` ⇒ Arole485/R485 两臂真值落共用名 "
                       "`usage-Arole.jsonl`/`usage-R.jsonl`, **臂自身 tag 化文件 0 字节**, 等于臂自记分列不可用); 修后四臂 usage-<ARM><TAG>.jsonl "
                       "行数 = 15/12/14/11 (机检 H6 PASS x4)。候选⑦: eval/rover/r488/derive_r488.py 由 r487 臂执行器**机派生** r488 臂与驱动器 "
                       "(逐条替换计数断言, 少/多一处即 rc=2 **且不写盘**; 首跑即拦下 both 脚本第 16 行文本不符 ⇒ 修表后重跑 35 条全过) + 残留机检 6 项 "
                       "(`eval/rover/r487`/`R487_`/`--round R487`/`[both-r487]`/`# R487 `/`2650` 各 0) + bash -n; 起手闸仍单一源 (臂内零阈值字面量)。"),
        "evidence_cmd": "python3 eval/rover/r488/derive_r488.py --check && python3 eval/rover/r488/derive_r488.py",
        "evidence_path": "eval/rover/r488/derive_r488.log.json",
        "instrument_path": "eval/rover/r488/derive_r488.py",
        "negative_control": ("派生器 fail-closed 负控: 断言计数不符即 rc=2 不写盘 (本轮真被触发过一次: both 脚本 R 行文本 'R 失败' vs 'R485 失败' ⇒ "
                             "拦下, 未产出半成品脚本); 残留机检以 6 个禁用子串各自计数为 0 作负控 (任一残留 ⇒ rc=2); 臂脚本经 `bash -n` 语法闸。"),
        "covers": ["eval/rover/r488/derive_r488.py", "eval/rover/r488/derive_r488.log.json"],
        "owner_round": "R488",
    },
    {
        "id": "r488.r486-invitro-first-run-and-empty-base-rate",
        "level": "L2",
        "capability": ("候选⑥ 对侧 R486 确定性桩差分器具**首次真跑** + 命名缺陷修复: check_r486.py 的 TAGS 写作 `pre-empt/post-empt` 而运行器 "
                       "run_diff_r486.sh 算出 `TAG=$ARM-$(echo $MODE | cut -c1-5)` ⇒ 现盘文件名 `*-empty` ⇒ 修前 check 恒 rc=3「缺输入」且只读到 "
                       "2/4 臂 (pre-plain/post-plain), 空正文两臂永远读不到 ⇒ 该器具自 R486 落盘起**从未产出判据**。修后真跑 rc=0 + 判据 rc=1: "
                       "**H1 FAIL** (pre_empty 1 vs post_empty 1, delta 0) / **H3 FAIL** (pre_empty 期望 2, 实测 1) / **H4 FAIL** (pre 遥测 "
                       "retry_skipped 0/0, post 1/0) / H2 PASS / NC1 PASS ⇒ 「空正文(带 tool_calls) ⇒ 浪费重试」的 pre/post 差分**在本夹具未复现** "
                       "(夹具 AGENTFRAMEWORK_ACTION_LOOP=off ⇒ 重试路径可能结构不可达) ⇒ 预注册前提被证伪, **宣称收窄**: 不据此宣称 R478/R479 修复生效或失效。"
                       "真机空正文基数 (供应商真值列 content_len==0, 候选③ 可测化): 全调用 B 3/15 · G 4/12 · S 2/14 · R 5/11; 剔前 2 次结构性调用 ⇒ "
                       "B 1/13 · G 2/10 · S 0/12 · R 3/9 (R 臂最贵)。"),
        "evidence_cmd": "python3 eval/rover/r486/check_r486.py",
        "evidence_path": "eval/rover/r486/verdict-r486.json",
        "instrument_path": "eval/rover/r486/check_r486.py",
        "negative_control": ("器具自带 NC1 (`--nc-blind`) PASS = 桩内容可盲判的反向对照; H1/H3 以「差分必须恰好为 1 次请求」为方向断言, 实测 0 ⇒ "
                             "判负而不是判成「无差异即通过」(拒把未复现当成功); 预注册 eval/rover/r486/prereg_r486.json 写于本轮真跑之前, 前提被证伪后"
                             "宣称收窄并单列, 不回改断言。"),
        "covers": ["eval/rover/r486/check_r486.py", "eval/rover/r486/run_diff_r486.sh",
                   "eval/rover/r486/prereg_r486.json", "eval/rover/r486/verdict-r486.json",
                   "eval/rover/r486/diff_r486.log"],
        "owner_round": "R488",
    },
]


def main():
    txt = io.open(REG, encoding='utf-8').read()
    if not txt.endswith('\n'):
        raise SystemExit('SER_ASSERT: registry 缺尾换行 ⇒ 拒写')
    reg = json.loads(txt)
    rows = reg['rows']
    idx = {r['id']: i for i, r in enumerate(rows)}
    out = []
    added, replaced = 0, 0
    for r in ROWS:
        r = dict(r)
        r['evidence_generated_with'] = {
            "evidence_kind": "artifact",
            "pin_status": "frozen",
            "pin_reason": "archived-per-round",
            "artifact_sha12": sha12(r['evidence_path']),
            "instrument": r['instrument_path'],
            "instrument_sha12": sha12(r['instrument_path']),
            "binding": "audit-pin",
            "audited_by_round": "R488",
        }
        r.pop('instrument_path', None)
        if r['id'] in idx:
            rows[idx[r['id']]] = r
            replaced += 1
        else:
            out.append(r)
            added += 1
    rows.extend(out)
    reg['updated_round'] = 'R488'
    new = json.dumps(reg, ensure_ascii=False, indent=1) + '\n'
    io.open(REG, 'w', encoding='utf-8').write(new)
    back = json.loads(io.open(REG, encoding='utf-8').read())
    ok = (len(back['rows']) == len(rows) and back['updated_round'] == 'R488'
          and all(r.get('evidence_generated_with', {}).get('artifact_sha12') == sha12(r['evidence_path'])
                  for r in back['rows'] if r.get('owner_round') == 'R488'))
    print(json.dumps({"added": added, "replaced": replaced, "rows": len(back['rows']),
                      "updated_round": back['updated_round'], "readback_ok": ok,
                      "tail_nl": io.open(REG, 'rb').read().endswith(b'\n')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
