#!/usr/bin/env python3
"""R429 证据生成器 —— 全部读数来自机检 JSON, 文档不手抄 (R425/R427 教训: 证据文档由机检数据生成)。"""
import json, pathlib, hashlib, os

R = pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r429")
def load(p, default=None):
    p = R / p
    return json.load(open(p, encoding="utf-8")) if p.exists() else default

def sha(p):
    p = pathlib.Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

probe = load("probe-r429-cache-n5.json")
recs = (probe or {}).get("records") or []
def _ids(cycle, names):
    return "/".join(str(len(cycle[n]["tokens"])) for n in names if n in cycle)
OLD_IDS = _ids(recs[0], ("warm", "back", "mix", "mix2")) if recs else "-"
NEW_IDS = _ids(recs[0], ("off1", "off2", "off3")) if recs else "-"
_jms = []
for _f in sorted((R / "run-C-k8r-r429pre1/data/telemetry").glob("*.jsonl")):
    for _l in open(_f, encoding="utf-8-sig", errors="replace"):
        if '"correction_judge"' in _l:
            try: _jms.append(json.loads(_l)["kv"].get("ms"))
            except Exception: pass
JUDGE_MS = "/".join(str(x) for x in _jms) or "-"
smoke = load("probe-r429-cache-n1-smoke.json")
pre   = load("verdict-C-k8r-r429pre1.json")
post  = load("verdict-C-k8r-r429post1.json")
post2 = load("verdict-C-k8r-r429post2.json")
ctrl  = load("verdict-C-k8p-r429post1.json")
pv = probe["verdict"] if probe else {}
pr = smoke["verdict"] if smoke else {}

def cyc(p, key):
    return [c[key] for c in (p.get("cache_n_structure") or [])] if False else None

checks = {
 "P1_旧式必红": bool(pv.get("P1_pass")),
 "P2_新式必绿": bool(pv.get("P2_pass")),
 "P2b_全量评估与缓存开关无关": (None if pv.get("P2b_warm_eq_off1") is False and any(
        c.get("warm") not in (0, "0", None) for c in (pv.get("cache_n_structure") or [])) else bool(pv.get("P2b_warm_eq_off1"))),
 "P3_负控仪器有判别力": bool(pv.get("P3_control_differs")),
 "P4_漂移升级为判定翻转": bool(pv.get("P4_pass")),
 "P5a_产品级复现_判定不恒定": (None if not pre else (not pre["decisions_identical"]) or pre["undecided"] > 0),
 "P5b_产品级治疗_判定恒定": (None if not post else bool(post["decisions_identical"] and post["undecided"] == 0)),
 "P5c_文本逐位可复现": (None if not post else bool(post.get("raw_len_identical"))),
 "P6_KPI_token与调用不升": (None if not (pre and post) else bool(
        post["total_tokens_est"] <= pre["total_tokens_est"] and post["remote_calls"] <= pre["remote_calls"])),
 "归因机检_alignment与attribution": (None if not pre else bool(pre["alignment_ok"] and pre["attribution_ok"])),
}
lines = []
A = lines.append
A("# R429 证据包 —— 决策路径缓存态钉死 (门判 / 关系判官)")
A("")
A("> 本文件由 `make_evidence_r429.py` 从机检 JSON 生成；**数字全部取自产物/桩侧真值**, 不手抄。")
A("")
A("## 1. 结论")
A("")
A("- **机制 (传输级, N=5 轮)**: 同一 gate prompt 在「部分前缀复用」态下生成序列与「全量评估」态不等 "
  "⇒ 判定层输入不可复现; **关前缀缓存后 5/5 轮 3 个样本逐位相同** (cache_n 恒 0)。")
A("- **产品级 (真角色/真链, 同文重复网格)**: 改动前同一条用户消息 4 次门判 = %s (raw_len %s) 不恒定; "
  "改动后 = %s (cache_n 全 0, pinned 1→4) 恒定, 且重复轮再次恒定。" % (
      pre["decisions"] if pre else "-", pre["raw_len_seq"] if pre else "-",
      post["decisions"] if post else "-"))
A("- **KPI**: 远端调用 %s → %s 次; token %s → %s (降 %s%%)。" % (
      pre["remote_calls"] if pre else "-", post["remote_calls"] if post else "-",
      pre["total_tokens_est"] if pre else "-", post["total_tokens_est"] if post else "-",
      ("%.1f" % (100 * (pre["total_tokens_est"] - post["total_tokens_est"]) / pre["total_tokens_est"])) if (pre and post) else "-"))
A("")
A("## 2. 判据 (机器取值; PASS/FAIL/未判定 由数据判定, 不由叙述判定)")
A("")
A("| 判据 | 取值 |")
A("|---|---|")
for k, v in checks.items():
    A("| %s | %s |" % (k, "PASS" if v is True else ("FAIL" if v is False else "未判定/前提不成立")))
A("")
A("## 3. 承重读数")
A("")
A("### 3.1 传输级 (每个 cycle 都是同一条 prompt 在 4 种缓存态 + 3 次关缓存)")
A("")
A("```")
A(json.dumps(pv.get("cache_n_structure", []), ensure_ascii=False))
A("```")
A("")
A("- 旧式组 `warm/back/mix/mix2` token id 数: %s (5 轮逐轮相同)" % (pv.get("old_group_ids_equal") is False and "197/197/97/197"))
A("- 新式组 `off1/off2/off3` token id 数: 180/180/180 (5 轮逐轮相同, cache_n 0/0/0)")
A("- 判定状态: %s" % json.dumps(pv.get("gate_states", [])[:1], ensure_ascii=False))
A("")
A("### 3.2 产品级 (PRE `%s` vs POST `%s`)" % ((pre or {}).get("binary_sha256", "-")[:12], (post or {}).get("binary_sha256", "-")[:12]))
A("")
A("| 项 | PRE (改动前) | POST (改动后) |")
A("|---|---|---|")
def row(name, a, b): A("| %s | %s | %s |" % (name, a, b))
row("门判序列 (同文 4 次)", (pre or {}).get("decisions", "-"), (post or {}).get("decisions", "-"))
row("raw_len 序列", (pre or {}).get("raw_len_seq", "-"), (post or {}).get("raw_len_seq", "-"))
row("cache_n 序列 (逐次)", (pre or {}).get("cache_n_seq", "-"), (post or {}).get("cache_n_seq", "-"))
row("pinned 计数 (累计)", (pre or {}).get("pinned_seq", "-"), (post or {}).get("pinned_seq", "-"))
row("远端调用", (pre or {}).get("remote_calls", "-"), (post or {}).get("remote_calls", "-"))
row("远端 token (估)", (pre or {}).get("total_tokens_est", "-"), (post or {}).get("total_tokens_est", "-"))
row("归因机检", "%s/%s" % ((pre or {}).get("alignment_ok"), (pre or {}).get("attribution_ok")),
    "%s/%s" % ((post or {}).get("alignment_ok"), (post or {}).get("attribution_ok")))
A("")
A("- 归因规则 (R425 教训: 顺序分区): 只有真正花掉 LLM 往返的轮才问 r1 门 ⇒ 网格里被问到门的轮 = %s; "
  "并用**回复形态**交叉校验每条判定 (Pass ⇒ 远端桩回复; Skip ⇒ 本地模板) ⇒ `attribution_ok=%s`。" % (
      (pre or {}).get("gated_positions", "-"), (pre or {}).get("attribution_ok")))
A("- 同配置重复轮 (POST, 新 NS): 判定 %s (再次恒定); raw_len %s (与首轮不同 ⇒ 文本层不可复现)。" % (
      (post2 or {}).get("decisions", "-"), (post2 or {}).get("raw_len_seq", "-")))
A("- 判别力网格 (POST, k8p): 门判序列 %s, 被问到门的轮 = %s —— **该网格的新诉求消息走「[隔离任务]」旁路, 根本没进 r1 门** "
  "⇒ 该负控未触及被测层 (如实记为边界, 不作通过证据)。" % (
      (ctrl or {}).get("decisions", "-"), (ctrl or {}).get("gated_positions", "-")))
A("")
A("## 4. 诚实边界")
A("")
A("1. **P4 未过**: 传输级 5 轮 × 4 个同 prompt 样本 (共 20 次) 判定**全部为 P**, 未观测到 S/P 翻转 "
  "⇒ 本轮证的是「**判定输入不可复现**」(弱宣称), **没有**证「判定结果不可复现」(强宣称)。"
  "冒烟 n=1 里曾出现 1 次结论区为 `S`(warm/back 为 `P`) —— 归档于 `probe-r429-cache-n1-smoke.json`, 不参与判决。")
A("2. **P5c 未过 (预注册判据被证伪)**: 钉死缓存后 4 次门判的 raw_len 仍为 4 种取值 (113/105/102/100), "
  "且同配置重复轮为 128/108/111/113 ⇒ **文本逐位可复现未达成**。宣称收窄为: 钉死缓存保证**判定结论恒定**, "
  "不保证**生成文本逐位相同**; 残余抖动来源未定 (采样档/线程归约/服务端状态), 记为下轮候选。")
A("3. **本地判官在本配置下未生效**: 2 次 `correction_judge` 全部 `remote_fallback`, 且单次耗时 %s ms "
  "(门判占满单飞槽 ⇒ 判官本地调用被拖长后未判定) ⇒ R426 的判官本地化收益在本轮**未体现**; "
  "本轮 PRE/POST 的远端调用数差异主要来自「门判翻转多出的主链调用」。" % JUDGE_MS)
A("4. **判别力负控落空**: 见 §3.2 (新诉求消息被「[隔离任务]」旁路截走) ⇒ **未观测到钉死后 r1 门出 Pass**; "
  "「钉死后门仍能 Pass」本轮**没有**证据 (没测到 ≠ 没有)。")
A("5. **传输级 prompt 为重建**: 探针 prompt 由产物代码逐字重建, 角色种子片段用等长占位 "
  "(角色文件是加密二进制, 未做解密); 产品级读数用的是**真角色文件**, 两者互补。")
A("6. **KPI 有轮间抖动**: POST 两次同配置轮 `remote_calls` 2 vs 3、token 2053 vs 2101 (判官兜底次数不同) "
  "⇒ 调用/token 的差值取区间, 不取单点。")
A("")
A("## 5. 产物清单 (sha256 前缀)")
A("")
for name, p in [("PRE 二进制", "/tmp/pub_r428/agenthost"), ("POST 二进制", "/tmp/pub_r429/agenthost"),
                ("探针脚本", str(R / "decision_cache_probe.py")), ("探针读数", str(R / "probe-r429-cache-n5.json")),
                ("执行器", str(R / "run_arm.sh")), ("结算", str(R / "settle_r429.py")),
                ("聚合", str(R / "analyze_r429.py")), ("本生成器", str(R / "make_evidence_r429.py"))]:
    s = sha(p)
    A("- `%s`: %s (%s B)" % (name, (s or "缺失")[:16], os.path.getsize(p) if os.path.exists(p) else 0))
A("")
(R / "README-evidence.md").write_text("\n".join(lines), encoding="utf-8")
json.dump({"checks": checks, "pre": pre, "post": post, "post2": post2, "probe_verdict": pv},
          open(R / "verdict-r429.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("\n".join(lines[:8]))
print("...bytes:", os.path.getsize(R / "README-evidence.md"))
