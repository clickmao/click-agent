#!/usr/bin/env python3
# R472 台账回灌: 追加 2 行到 docs/verification-registry.json (幂等: 同 id 已存在则替换)
import collections, io, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
P = os.path.join(ROOT, 'docs', 'verification-registry.json')

EV_PROBE = ("env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR python3 eval/rover/r472/probe_cache_cap.py")
EV_POST = ("env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR python3 eval/rover/r472/check_criteria_r472.py")

NEW = [
    collections.OrderedDict([
        ("id", "r472.prefix-cache-no-provider-cap"),
        ("level", "L3"),
        ("capability", "真机受控实验裁决「远端命中饱和成因」: 8 次真实调用(deepseek-flash, 与 config/base/models.yaml:9,16 同模型同端点), 共享前缀阶梯 910/3789/5811 tok, warm 命中 768/3584/5632(全部为 64 整数倍, hit/前缀 0.844/0.946/0.969 单调升) ⇒ 最大命中 5,632 > 假设饱和上沿 2,304 ⇒ 「provider 在 ~2.1k 截断命中」被单条观察直接证伪(NO_CAP); 三条 cold(唯一 nonce 开头)命中 0/0/0; 恒等式 prompt==hit+miss 8/8; 成本实测 0.008954 CNY(上限 0.02 预注册); 后果: 命中量 = 与历史调用共享的前缀长度(块对齐), 升前缀有效, R469「97% 对长轮结构性不可达」的机制表述作废(该样本 43/43 无同会话前驱 + 4k 私有文本)"),
        ("evidence_cmd", EV_PROBE),
        ("evidence_path", "eval/rover/r472/asserts-r472.json"),
        ("negative_control", "C3 负控: 三条 cold 以唯一 nonce 开头(与任何既有文本无共享前缀) ⇒ hit 必须 == 0, 任一 >0 即判 UNDECIDABLE(防把环境偶然缓存当成实验效应); C4 正控: 小臂 hit >= 0.80 x P_hat(排除「缓存根本没生效」的假阴性, 实测 0.844 通过); C2 恒等式 8/8; C6 复现臂 BIG.warm2.hit == BIG.warm.hit(5,632 == 5,632); C7 判定函数合成自检 FAIL(见 r472.criteria-posthoc-and-mechanism-law 行, 原判不覆盖)"),
        ("covers", [
            "eval/rover/r472/probe_cache_cap.py",
            "eval/rover/r472/prereg-r472.json",
            "eval/rover/r472/asserts-r472.json",
            "eval/rover/r472/real-usage-r472.jsonl",
            "docs/plans/v0.89.0-r472-provider-cache-cap-experiment.md",
        ]),
        ("owner_round", "R472"),
    ]),
    collections.OrderedDict([
        ("id", "r472.criteria-posthoc-and-mechanism-law"),
        ("level", "L2"),
        ("capability", "事后判据处置 + 机制定律: (a) 预注册 C7(判定函数自检)判 FAIL 的原判保留不覆盖, 根因定位为 v1 CAP 分支阈值与前缀臂尺寸不自洽(P_MID 需 >= 3150 才可达, 合成 case cap=2048/P_MID=2600 因此判 PARTIAL); (b) 修正版 v2 饱和信号改为「命中量不再随前缀增长」(hit_BIG <= 1.15 x hit_MID) ⇒ 合成 4 例 CAP/NO_CAP/UNDECIDABLE/PARTIAL 全对, 且真实数据在 v1/v2 下同判 NO_CAP ⇒ 结论不依赖判据修正; (c) 机制定律 prompt_cache_hit_tokens == 64*floor((prompt_tokens-c)/64), c = 142 由 5 点不等式交集唯一确定, 5/5 点吻合"),
        ("evidence_cmd", EV_POST),
        ("evidence_path", "eval/rover/r472/posthoc-r472.json"),
        ("negative_control", "本文件 new_api_calls == 0(禁用新调用补测); P1 复现预注册 C7 失败而不是掩盖/重写历史; P3 v2 合成 4 例含 UNDECIDABLE 与 PARTIAL 两例(证明判定函数非恒真、非恒 CAP/NO_CAP 二值); P4 c 的唯一性即判别力(c=141 被 MID 臂排除: 3789-141=3648=57x64 但实测 3584); P0 用数据级证伪(5,632 > 2,304)避免依赖判定函数"),
        ("covers", [
            "eval/rover/r472/check_criteria_r472.py",
            "eval/rover/r472/posthoc-r472.json",
            "eval/rover/r472/prereg-r472.json",
            "docs/reports/r472-cache-cap-experiment.md",
        ]),
        ("owner_round", "R472"),
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
d['updated_round'] = 'R472'
# 台账原文缩进 = 1 空格, 重排会制造全文件 diff 噪声 ⇒ 必须保形写回
io.open(P, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
print(json.dumps({"added": added, "replaced": replaced, "total_rows": len(rows), "updated_round": d['updated_round']}, ensure_ascii=False))
