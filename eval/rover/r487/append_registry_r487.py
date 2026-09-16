#!/usr/bin/env python3
# R487 台账回灌: 追加 3 行到 docs/verification-registry.json (幂等: 同 id 已存在则替换)
# 保形写回: 原文缩进 = 1 空格; 末尾必须带换行(缺尾换行会被 SER 断言拒写)。
import collections, io, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
P = os.path.join(ROOT, 'docs', 'verification-registry.json')

EV_ROLL = "python3 eval/rover/r487/analyze_r487.py"
EV_GATE = "python3 eval/rover/r487/check_h6_blocker_cause.py"
EV_DER = "python3 eval/rover/r487/derive_r487.py --force"
EV_BAND = "python3 eval/recall/r487/band_probe_r487.py"

NEW = [
    collections.OrderedDict([
        ("id", "r487.three-arm-realand-kpi-negative"),
        ("level", "L3"),
        ("capability", "真机三臂同夹具全链跑通 (rc=0, 三臂各 12 轮): A0 = /tmp/pub_r479v2/agenthost (门关+rj 开, 无微闸; sha256 6a9b7aed22a22f48…) / Arole485 = /tmp/pub_r485/agenthost (同 A0 臂参, 只换二进制; sha256 03c77d56e8c485af…) / R485 = 同 R485 二进制 + 门开 + repeat_skip。判据: H1 闸活 PASS (telemetry micro_step_skipped = A0 0 / Arole485 4 / R485 2); **H2 主 KPI FAIL**: 供应商真值 token A0 80,302 -> R485 81,770 (+1.83%, 目标 -30% 未达), 调用数 22 -> 14; **H3 FAIL**: Arole485 63,825 -> R485 81,770 (+28.1%) 且调用 15 -> 14 (方向相反); **H4 FAIL**: R485 实质轮 6/12 (模板答复 4 + 复述回放 2 ⇒ 质量面未不降); **H0 FAIL**: A0 锚未复现 (22 次调用 / 80,302 tok vs R482 21 / 72,634) ⇒ 本轮与 R482 分母不可直接比。结论: 微问询预发送闸**确在管道内生效**(打点非零)但**单靠它不足以达成 token 降幅**, 且未跳过的轮次上下文更贵 (14 次调用 81.8k tok = 5,841 tok/调用 vs Arole485 4,255) ⇒ 归因为「剩余上游调用的前缀更长」, 下一轮靶点 = 上下文剪裁/前缀复用, 而非再加闸。"),
        ("evidence_cmd", EV_ROLL),
        ("evidence_path", "eval/rover/r487/verdict-r487.json"),
        ("negative_control", "三臂同夹具同网格同时窗 (p12) ⇒ 差分归因; H1 以 A0 臂 micro_step_skipped==0 作**阴性对照**(旧二进制无闸 ⇒ 打点必须为零, 实测 0) 而 Arole485/R485 非零 ⇒ 打点来自新二进制而非夹具; H5 二进制形态 (sha256 双值匹配 + prov under_test.native_ok + neg_ok) 全 PASS ⇒ 读数绑定到被验二进制; 供应商 usage 与臂自记分列 (臂自身 tag 化 $USAGE 文件 0 字节 ⇒ 记 unreported, 不用 0 冒充); 缺任一臂 usage/report 即判红 (fail-closed)"),
        ("covers", [
            "eval/rover/r487/prereg_r487.json",
            "eval/rover/r487/analyze_r487.py",
            "eval/rover/r487/verdict-r487.json",
            "eval/rover/r487/run_both_r487.sh",
            "eval/rover/r487/run_arm_real_r487.sh",
            "eval/rover/r487/both_r487.log",
        ]),
        ("owner_round", "R487"),
    ]),
    collections.OrderedDict([
        ("id", "r487.blocker-multi-cause-and-gate-single-source"),
        ("level", "L2"),
        ("capability", "起手闸器具两条收口: (a) blocker_cause **多因并列** (取消 either/or; 修前 tagged 三元表达式只留一因 ⇒ 内存不足与 build-server 残留同时成立时只报后者, 归因错误); 差分负控三态 C1 常规 rc=0 PASS / C2 --nc-block rc=2 causes=[内存不足] / C3 --nc-both (起手 25s 期实起 VBCSCompiler 假进程) rc=2 causes=[内存不足, build-server 残留] ⇒ 两因并存可判, 修前形态结构上不可达; (b) 臂执行器/驱动器**机派生** (eval/rover/r487/derive_r487.py: 28 条替换规则逐条计数断言, 少/多一处即 rc=2 且不写盘) + 起手闸与沉降等待**单一源** (臂内零阈值字面量, grep 2650 = 0), 并加 H7 机检 (literal_2650_count=0 ∧ gate_refs>=1 ∧ 旧命名空间可执行形态残留=0)。"),
        ("evidence_cmd", EV_GATE),
        ("evidence_path", "eval/rover/r487/h6_blocker_cause_readings.json"),
        ("negative_control", "H6: --nc-block/--nc-both 为**修前行为复现**(不排除 shell ⇒ 旁支/自身命令行提到监视字串即误报) ⇒ 判据非恒真; C3 以真实新进程 (VBCSCompiler 名) + 真实内存不足构造**双因并存**, 断言 causes 恰为 2 且顺序固定。H7: 派生期 5 次断言失败均在写盘前拦下 (证据: derive_r487.log.json 的 fail_closed 记录), 证明派生表不是装饰"),
        ("covers", [
            "eval/rover/r483/preflight_gate.py",
            "eval/rover/r487/derive_r487.py",
            "eval/rover/r487/check_h6_blocker_cause.py",
            "eval/rover/r487/h6_blocker_cause_readings.json",
            "eval/rover/r487/derive_r487.log.json",
        ]),
        ("owner_round", "R487"),
    ]),
    collections.OrderedDict([
        ("id", "r487.band-subband-and-corpus-list"),
        ("level", "L2"),
        ("capability", "R481-G 遗留收口: rel 候选**子档分档读数** (explicit_rel / root_rel / slash_token / escape 顺序分区, 每 local rel 候选恰好一桶 ⇒ 守恒式可机检) + 语料钉**清单导出** (漂移可归因, 补 R481-G 已知缺口「器具只输出 files_sha16 无语料清单」)。读数 (本 pin: files=6882, files_sha16=3da4c878e2b160bb): markdown resolved_rate **0.8125** (阈值 0.90 ⇒ FAIL, 与已注册 R481-B 器具 **同值** 0.8125 ⇒ 单源一致性); explicit_rel rewrite_ok_rate 0.0913 (阈值 0.85 ⇒ FAIL; 严格分区下 < R481-B 的 0.1091, 差异为桶语义: 本器具把越根/非 rel 来源的 explicit 候选排除出该桶; 两侧同判 FAIL ⇒ 判定对语义选择稳健); root_rel resolved_rate **1.0** (阈值 0.90 ⇒ PASS); slash_token 58,155 (命名噪声档, 无阈值, 单列); 外部 url 档 = unreported (离线无网)。"),
        ("evidence_cmd", EV_BAND),
        ("evidence_path", "eval/recall/r487/band_readings_r487.json"),
        ("negative_control", "--nc-blind (强制候选一律不可解析, 同码路差分) ⇒ root_rel 1.0 -> 0.0 且 markdown 0.8125 -> 0.0, 判据翻面 ⇒ 器具承载判定; 守恒式断言 files/paths 总账 (refs 分档求和 == local 总数) 首跑即**判红**(自查出本器具分支双重计数 bug) ⇒ 修正后 ok=True, 判红非装饰; 与已注册器具同值 (0.8125) 作**外部一致性**校验"),
        ("covers", [
            "eval/recall/r487/band_probe_r487.py",
            "eval/recall/r487/band_readings_r487.json",
            "eval/recall/r487/corpus-list-r487.json",
            "eval/recall/prereg_r481g.json",
        ]),
        ("owner_round", "R487"),
    ]),
]

d = json.load(io.open(P, encoding='utf-8'), object_pairs_hook=collections.OrderedDict)
rows = d['rows']
ids = {r['id'] for r in rows}
added, replaced = [], []
for n in NEW:
    if n['id'] in ids:
        for i, r in enumerate(rows):
            if r['id'] == n['id']:
                rows[i] = n
        replaced.append(n['id'])
    else:
        rows.append(n)
        added.append(n['id'])
d['updated_round'] = 'R487'
if not rows:
    raise SystemExit("SER_ASSERT: rows 为空, 拒写")
io.open(P, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
print(json.dumps({"added": added, "replaced": replaced, "total_rows": len(rows),
                  "updated_round": d['updated_round']}, ensure_ascii=False))
