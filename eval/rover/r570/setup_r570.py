#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R570 派生 + 预注册 (先写后跑) 器具 —— 由 eval/rover/r569/setup_r569.py 派生。

本轮 = **零开发**对照轮 (用户令 2026-09-18「开工, 不许新增夹具和额外开发了」)：
既有开关 `AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL` 取值 **0 (默认关) vs 2** × 外部真值 codex，6 **新**窗 w143..w148。

选轴依据 (数据先行, 非预言式): R546/R547 已立该轴的**剂量行使面**，但明写「早停对**质量**的影响未测」；
从 R566/R567/R569 已落盘读数机取 `public_probe_failed` 分布 (R569B0 = [1,0,2,2,0,2] / R567B0 = [2,0,1,4,1,2])
⇒ 阈值 2 在约 3/6 窗可达 ⇒ **行使面天然存在**，不是「未行使的轴」。
该轴同时是主线唯一成本杠杆面 (「探针已判产物不合格 ⇒ 省掉那次远端回灌修复请求」)。

与来源轮 R569 的差异 (逐条声明, 其余逐字节继承/dose 键取值外):
  ① 命名空间 R569→R570 / r569→r570 / 窗集 w137..w142 → w143..w148 / 工作目录 /tmp/r570 / 端口 49511→49521;
  ② 单变量键 `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR`(0 vs 3) → `AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL`(0 vs 2);
     臂名 R569B0/R569B3 → R570E0/R570E2, 子目录 agentB0/agentB3 → agentE0/agentE2;
  ③ `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` 两臂**均不设** ⇒ 取产品默认 (源码派生 `R1Options.MaxExecRepair = 1`, R568 已立),
     与 R566B1 档同配置 (并列可比, 禁相减);
  ④ 起手闸 prev-postcheck 指 R569 件 (swing_mb=90); 上界规则 (R569 已落地的 `MARGIN := min(want, cap)`) **原样继承**;
  ⑤ ingest/kpi 器具**声明式增补** (读既有遥测字段, 非新夹具): `early_stop_pfail` / `early_stop_skipped`
     + 步数面 `steps_executed` / `plan_steps_total` 回仓 (闭合 R569 §7 候选④「步数面丢失」)。

零产品源码改动 / 零新增夹具 / 零新增开关; 冻结题集与用例脚本逐字节复用 (复用不复制语义)。
"""
import hashlib
import io
import json
import os
import shutil
import sys

REPO = "/home/agentuser/AgentFramework"
PDIR = os.path.join(REPO, "eval/rover/r570")
SRC = os.path.join(REPO, "eval/rover/r569")
FREEZE_SRC = os.path.join(REPO, "eval/rover/r560")
WINS = ["w143", "w144", "w145", "w146", "w147", "w148"]
WINS_PREV = ["w137", "w138", "w139", "w140", "w141", "w142"]
ARMS = ["C1", "R570E0", "R570E2"]
TASKSET_SHA = "e0c667c2a313c04b2d87ac06fcba9f50166a4a0be5d5162cabdbf520d9d3927a"
BIN_SHA = "320d0eb17e709d15ce7d149ceff45fc1cacff814ac01b9fbda67f702726cee48"
PROMPT_SHA = "516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3"
GRADER_SHA_EXP = "a67215a7"

DERIVED = ["run_r569.sh", "ingest_r569.py", "fingerprint_r569.py", "kpi_r569.py",
           "matrix_r569.py", "adjudicate_r569.py", "gate_margin_r569.py",
           "mem_sampler.py", "mem_sample_once.py"]


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def win_map():
    return {a: b for a, b in zip(WINS_PREV, WINS)}


def rules():
    r = []
    for a, b in win_map().items():
        r.append((a, b))
    r += [
        ("w137..w142", "w143..w148"),
        ("WIN0=${WIN0:-137}", "WIN0=${WIN0:-143}"),
        ("R569B0", "R570E0"), ("R569B3", "R570E2"),
        ("agentB0", "agentE0"), ("agentB3", "agentE2"),
        ("R569", "R570"), ("r569", "r570"),
        ("49511", "49521"),
        # prev-postcheck 指上一轮 (源轮) 件: 源 runner 里指 R566/R567 件, 这里显式改指 R569 件
        ("eval/rover/r567/gate-postcheck-r567.json", "eval/rover/r569/gate-postcheck-r569.json"),
        ("prev-postcheck = R567 件", "prev-postcheck = R569 件"),
        # 单变量键 + 取值
        ("AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR", "AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL"),
        ('AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL"]) == 3', 'AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL"]) == 2'),
        ('run_agent R570E2 "$W" agentE2 3', 'run_agent R570E2 "$W" agentE2 2'),
        ("EARLY_STOP_PFAIL=3", "EARLY_STOP_PFAIL=2"),
        ("EARLY_STOP_PFAIL 取值 **0 vs 3**", "EARLY_STOP_PFAIL 取值 **0 vs 2**"),
        ("(R570E0 =0 / R570E2 =3)", "(R570E0 =0 / R570E2 =2)"),
        ("既有开关 AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL 取值 **0 vs 3**",
         "既有开关 AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL 取值 **0 vs 2**"),
        # --- 末段规则: 匹配**通用替换之后**的注释残留 (逐条声明式改写, 不留裸 token) ---
        ("(轴=3)", "(轴=2)"),
        ("R570E2 轴=3", "R570E2 轴=2"),
        ("R570E2(轴=3)", "R570E2(轴=2)"),
        ("(候选④行使臂由 B0 换为 B3 —— R566 实测 B0 每窗恒 1 调用 ⇒ C4-3 敏感性不可判; 判据文本不变)。",
         "(候选④行使臂取早停臂 E2; 该臂每窗调用数 <2 时 C4-3 非平凡判据记未行使, 不记 0)。"),
        ("① 轮号命名空间 R567→R570 / r567→r570 (工作目录 /tmp/r570, 端口 49521); "
         "起手闸 prev-postcheck = R569 件 (swing 103)",
         "① 轮号命名空间 R569→R570 / r569→r570 (工作目录 /tmp/r570, 端口 49521); "
         "起手闸 prev-postcheck = 上一轮 R569 件 (swing_mb=90)"),
        ("R570E0 (MAX_EXEC_REPAIR=0) + R570E2 (MAX_EXEC_REPAIR=3)",
         "R570E0 (EARLY_STOP_PFAIL=0) + R570E2 (EARLY_STOP_PFAIL=2)"),
    ]
    return r


def substitute(text):
    n, out = {}, text
    for a, b in rules():
        c = out.count(a)
        if c:
            out = out.replace(a, b)
            n[a] = c
    return out, n


def derive_files():
    os.makedirs(PDIR, exist_ok=True)
    man = {"round": "R570", "source_round": "R569",
           "note": "派生件清单 (器具改 ⇒ 须重审 + 保形重钉): 每条给出源/目标 sha256 与替换计数",
           "files": []}
    for fn in DERIVED:
        src = os.path.join(SRC, fn)
        dst_name = fn.replace("r569", "r570").replace("R569", "R570")
        dst = os.path.join(PDIR, dst_name)
        txt = io.open(src, encoding="utf-8").read()
        new, counts = substitute(txt)
        io.open(dst, "w", encoding="utf-8").write(new)
        man["files"].append({"src": "eval/rover/r569/%s" % fn, "dst": "eval/rover/r570/%s" % dst_name,
                             "src_sha256": sha(src), "dst_sha256": sha(dst),
                             "substitutions": counts,
                             "n_lines_src": txt.count("\n"), "n_lines_dst": new.count("\n")})
    man["source_unchanged"] = all(sha(os.path.join(SRC, fn)) == f["src_sha256"]
                                  for fn, f in zip(DERIVED, man["files"]))
    man["residual_check"] = residual_check()
    json.dump(man, io.open(os.path.join(PDIR, "derivation-manifest-r570.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    ok = all(f["n_lines_src"] == f["n_lines_dst"] for f in man["files"])
    print("[派生] files=%d source_unchanged=%s line_counts_equal=%s residual=%s"
          % (len(man["files"]), man["source_unchanged"], ok, man["residual_check"]["ok"]))
    return man


def residual_check():
    """残留机检 (R566 自捕的『漏替换』族): 派生件里不得残留上一轮命名空间/旧轴键/旧剂量取值。

    唯一**声明式豁免**: 指向上一轮 (R569) 的 prev-postcheck 件路径与说明行 —— 该引用是**设计意图**
    (起手闸余量由上一轮实测振幅派生), 逐行豁免并在读数里可见 (豁免行数须 >0 且 <=2)。
    """
    bad_tokens = ["R569", "r569", "MAX_EXEC_REPAIR", "B0", "B3", "49511", "w137", "w138", "w139",
                  "w140", "w141", "w142", "agentB", "轴=3"]
    hits, exempt = [], []
    for fn in DERIVED:
        dst_name = fn.replace("r569", "r570").replace("R569", "R570")
        p = os.path.join(PDIR, dst_name)
        if not os.path.isfile(p):
            continue
        for i, line in enumerate(io.open(p, encoding="utf-8").read().splitlines(), 1):
            toks = [t for t in bad_tokens if t in line]
            if not toks:
                continue
            if "prev-postcheck" in line:
                exempt.append({"file": dst_name, "line": i, "tokens": toks})
                continue
            hits.append({"file": dst_name, "line": i, "tokens": toks, "text": line[:120]})
    return {"ok": not hits and len(exempt) <= 2, "hits": hits, "exempt_prev_round_refs": exempt,
            "note": "B0/B3 作为独立 token 残留即为漏替换 (臂名应已变 E0/E2); 命中即 fail-closed; "
                    "prev-postcheck 引用行按设计豁免 (须 <=2 行)"}


def patch_ingest():
    """声明式增补: 读既有遥测字段 early_stop_* + 步数面回仓 (R569 §7 候选④)。断言不放宽。"""
    p = os.path.join(PDIR, "ingest_r570.py")
    txt = io.open(p, encoding="utf-8").read()
    pairs = [
        ('             "public_probe_trigger_rc")',
         '             "public_probe_trigger_rc", "early_stop_pfail", "early_stop_skipped")'),
        ('                         "self_test_unmet": tr.get("self_test_unmet")})',
         '                         "self_test_unmet": tr.get("self_test_unmet"),\n'
         '                         "early_stop_pfail": tr.get("early_stop_pfail"),\n'
         '                         "early_stop_skipped": tr.get("early_stop_skipped"),\n'
         '                         "steps_executed": tr.get("steps_executed"),\n'
         '                         "plan_steps_total": tr.get("plan_steps_total")})'),
        ('                             "public_probe_failed": tr.get("public_probe_failed")}',
         '                             "public_probe_failed": tr.get("public_probe_failed"),\n'
         '                             "early_stop_pfail": tr.get("early_stop_pfail"),\n'
         '                             "early_stop_skipped": tr.get("early_stop_skipped"),\n'
         '                             "steps_executed": tr.get("steps_executed")}'),
        ('rec["rule"] = "调用/新算 prompt 取中继 dump 索引区段; 剂量行使 ⇔ transcript.exec_repairs>0; 账核对 = dump 区段 vs transcript.calls"',
         'rec["rule"] = ("调用/新算 prompt 取中继 dump 索引区段; 轴行使 ⇔ transcript.early_stop_skipped>0（早停）∨ transcript.exec_repairs>0（执行回灌）; 账核对 = dump 区段 vs transcript.calls")'),
    ]
    for a, b in pairs:
        assert a in txt, "ingest 锚点未命中: %s" % a[:60]
        txt = txt.replace(a, b, 1)
    io.open(p, "w", encoding="utf-8").write(txt)
    print("[增补] ingest_r570.py: early_stop_pfail/early_stop_skipped + steps 面回仓")
    return sha(p)


def patch_kpi():
    p = os.path.join(PDIR, "kpi_r570.py")
    txt = io.open(p, encoding="utf-8").read()
    pairs = [
        ('                                 "public_probe_failed": e["self_transcript"].get("public_probe_failed") if e["self_transcript"] else None})',
         '                                 "public_probe_failed": e["self_transcript"].get("public_probe_failed") if e["self_transcript"] else None,\n'
         '                                 "early_stop_pfail": e["self_transcript"].get("early_stop_pfail") if e["self_transcript"] else None,\n'
         '                                 "early_stop_skipped": e["self_transcript"].get("early_stop_skipped") if e["self_transcript"] else None,\n'
         '                                 "steps_executed": e["self_transcript"].get("steps_executed") if e["self_transcript"] else None,\n'
         '                                 "plan_steps_total": e["self_transcript"].get("plan_steps_total") if e["self_transcript"] else None})'),
        ('        d["exec_repairs_max"] = max([x["exec_repairs"] or 0 for x in wl], default=None)',
         '        d["exec_repairs_max"] = max([x["exec_repairs"] or 0 for x in wl], default=None)\n'
         '        d["early_stop_skipped_sum"] = sum([x["early_stop_skipped"] or 0 for x in wl])\n'
         '        d["early_stop_pfail_vals"] = [x["early_stop_pfail"] for x in wl]\n'
         '        d["steps_executed_vals"] = [x["steps_executed"] for x in wl]'),
        ('        print("  [KPI %s] calls=%d new=%d completion=%d med=%s rng=%s max_exec_repair=%s exec_max=%s" % (\n'
         '            arm, d["calls"], d["new_prompt"], d["completion"], d["median_cases"], d["range_cases"],\n'
         '            d["max_exec_repair_observed"], d["exec_repairs_max"]))',
         '        print("  [KPI %s] calls=%d new=%d completion=%d med=%s rng=%s exec_max=%s eskip_sum=%s pfail=%s steps=%s" % (\n'
         '            arm, d["calls"], d["new_prompt"], d["completion"], d["median_cases"], d["range_cases"],\n'
         '            d["exec_repairs_max"], d["early_stop_skipped_sum"], d["early_stop_pfail_vals"],\n'
         '            d["steps_executed_vals"]))'),
    ]
    for a, b in pairs:
        assert a in txt, "kpi 锚点未命中: %s" % a[:60]
        txt = txt.replace(a, b, 1)
    io.open(p, "w", encoding="utf-8").write(txt)
    print("[增补] kpi_r570.py: early_stop/skips/steps 三面入表")
    return sha(p)


def check_runner_semantics():
    """驱动器**端到端**语义机检 (R566 自捕『端口脚本漏替换窗口名』族): 只查文本替换计数不够,
    必须断言「新轴真的从 schema 走到臂 env / 从取值走到 pre-注册闸」四个环节都在盘。"""
    p = os.path.join(PDIR, "run_r570.sh")
    txt = io.open(p, encoding="utf-8").read()
    checks = {
        "旧轴键零残留": "AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR" not in txt,
        "臂 env 注入新键": "AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL=$dose" in txt,
        "pre-注册闸断言取新值2": 'AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL"]) == 2' in txt,
        "E2 调用点传值2": 'run_agent R570E2 "$W" agentE2 2' in txt,
        "E0 调用点传值0": 'run_agent R570E0 "$W" agentE0 0' in txt,
        "prev-postcheck 指上一轮": "eval/rover/r569/gate-postcheck-r569.json" in txt,
        "窗起点=143": "WIN0=${WIN0:-143}" in txt,
        "端口=49521": "49521" in txt,
        "旧端口零残留": "49511" not in txt,
    }
    bad = [k for k, v in checks.items() if not v]
    print("[驱动器语义] %s %s" % ("OK" if not bad else "FAIL:%s" % bad, checks))
    return {"ok": not bad, "failed": bad, "checks": checks}


def freeze_copy():
    ts_src = os.path.join(FREEZE_SRC, "taskset-r560.json")
    ts_dst = os.path.join(PDIR, "taskset-r570.json")
    if sha(ts_src) != TASKSET_SHA:
        print("[致命] 冻结题集 sha 不符: %s" % sha(ts_src))
        return None
    shutil.copyfile(ts_src, ts_dst)
    cases_dst = os.path.join(PDIR, "cases")
    if os.path.isdir(cases_dst):
        shutil.rmtree(cases_dst)
    shutil.copytree(os.path.join(FREEZE_SRC, "cases"), cases_dst)
    reg = {"round": "R570", "note": "冻结件逐字节复用登记 (复用不复制语义 ⇒ 原件零改动)",
           "source_round": "R560",
           "taskset": {"src": "eval/rover/r560/taskset-r560.json",
                       "dst": "eval/rover/r570/taskset-r570.json",
                       "src_sha256": sha(ts_src), "dst_sha256": sha(ts_dst)},
           "cases": []}
    for root, _, files in os.walk(cases_dst):
        for fn in sorted(files):
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, cases_dst)
            s = os.path.join(FREEZE_SRC, "cases", rel)
            reg["cases"].append({"rel": rel, "src_sha256": sha(s), "dst_sha256": sha(p),
                                 "byte_identical": sha(s) == sha(p)})
    reg["all_byte_identical"] = (reg["taskset"]["src_sha256"] == reg["taskset"]["dst_sha256"]
                                 and all(c["byte_identical"] for c in reg["cases"]))
    sc = os.path.join(cases_dst, "run_cases_r521.py")
    h = sha(sc)
    reg["grader_sha256"] = h
    json.dump(reg, io.open(os.path.join(PDIR, "frozen-reuse-registration-r570.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[冻结件] taskset sha=%s cases=%d all_byte_identical=%s grader_ok=%s"
          % (reg["taskset"]["dst_sha256"][:16], len(reg["cases"]), reg["all_byte_identical"],
             h.startswith(GRADER_SHA_EXP)))
    return h if reg["all_byte_identical"] and h.startswith(GRADER_SHA_EXP) else None


def prereg(grader_sha):
    pre = {
        "round": "R570",
        "written_before_run": True,
        "author": "cron-agent (60min tick, 2026-09-19)",
        "claim": "**同窗零开发对照轮 (第四窗集)**: 既有开关 `AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL` 的取值 "
                 "**0 (默认关) vs 2** (同一枚二进制, 同题面/夹具/role/判分器逐字节复用) × 外部真值 codex, 6 新窗 w143..w148。"
                 "承重问题 = R546/R547 明写未测的「早停对**质量**的影响」, 并同时量主线唯一成本杠杆面"
                 "(探针已判产物不合格 ⇒ 省掉那次远端回灌修复请求) 的**成本-质量前沿**。"
                 "零产品源码改动 / 零新增夹具 / 零新增开关。",
        "one_time_context": "用户令 2026-09-19「继续下一轮」⇒ 走零开发臂 (既有开关); "
                            "R569 §7 登记的两项须动契约/产品分支的候选 (g1 失分面修复 / 交付闸语义) **未放行**; "
                            "剂量轴已定案关闭, 本轮**不重开**。",
        "candidates_ledger": {
            "R570-① 剂量轴再开窗": "未做 —— 非承重变量、已定案关闭 (重开条件 = 换承重面或臂内机制改动)",
            "R570-② g1/wythoff 失分面修复 (契约加厚 v3 / 产物落点自验)": "未做 —— 须动契约或产品分支 ⇒ **待放行**",
            "R570-③ 交付闸语义 (rc=5/rc=8 仍交付)": "未做 —— 须新增产品分支 ⇒ **待放行** (只读取证亦无新数据面)",
            "R570-④ 起手闸把本会话工具子进程纳入噪声面": "未做 —— 器具改版非本轮承重; 本轮以 pid 定向回收行使窗口 (R569 已立)",
            "R570-⑤ 步数面回仓": "做 —— ingest/kpi 声明式增补 (读既有遥测字段 steps_executed/plan_steps_total)",
            "R570-⑥ 早停轴同窗单变量 (承重)": "做 —— 6 新窗 w143..w148, 3 臂同窗 (既有开关, 零开发)",
        },
        "single_variable": "**仅一个 env 开关的值**: `AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL` ∈ {0 (R570E0, 显式关), 2 (R570E2)}; "
                           "`AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` 两臂**均不设** ⇒ 取产品默认 (源码派生 `R1Options.MaxExecRepair = 1`, "
                           "R568 已立, 与 R566B1 档同配置); 全臂共用同一枚 AOT 二进制 (sha %s, runner 第 0 步机检), "
                           "题面/夹具/role/窗口逐字节同" % BIN_SHA[:16],
        "arms": {
            "C1": {"side": "codex", "desc": "外部真值 (另一套 agent 框架 CLI, 同模型, 同题面同夹具同窗)", "env": {}},
            "R570E0": {"side": "agent", "desc": "早停轴 = 0 (关; 控制臂)",
                       "env": {"AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL": "0"}},
            "R570E2": {"side": "agent", "desc": "早停轴 = 2 (探针已判产物不合格 pfail>=2 ⇒ 不再花一次远端回灌修复)",
                       "env": {"AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL": "2"}},
        },
        "arm_env_definition_note": "两臂早停键**都显式落盘**且只有这一个键取值不同 ⇒ 单变量由构造保证; runner 第 0 步机检。"
                                   "其余 env 全臂相同 (R1_CONTRACT / R1_MAX_REPAIR=1 / PUBLIC_SELFCHECK=1 / ROLE_FILE / "
                                   "TRANSCRIPT / WORKSPACE / TAG); MAX_EXEC_REPAIR 两臂均不设 (产品默认 1)。",
        "scope_declaration": {
            "windows": WINS, "window_count": 6,
            "task": "g1 (冻结题面; prompt sha256 与 R559/R560/R563/R565/R566/R567/R569 逐字节相同)",
            "task_prompt_sha256_expected": PROMPT_SHA,
            "binary_sha256_expected": BIN_SHA,
            "hidden_cases": 58,
            "grader_sha256": grader_sha,
            "cross_round_deltas_forbidden": "与 w104..w118 / w119..w124 / w125..w130 / w131..w136 / w137..w142 的读数**并列不相减** (新窗)",
        },
        "criterion_version": "v2 (逐窗并列 + 真值崩窗 unreliable[MARGIN=3] + 配对判据[n>=3, 无窗<=-3, 中位>=-2] + VOID 臂窗单列) "
                             "—— 口径文本取自 docs/external-reference-harness.md §12, 本文件只引用不重定义; **本轮不改判据 v2**",
        "acceptance_rule": {
            "primary": "判据 v2 判决 (eval/rover/r561/verdict_r561.py 装置, adjudicate_r570.py 零逻辑复制复用); "
                       "每臂对**同窗真值**配对",
            "rc": "0 全过 / 1 判据未过 (被测或前提) / 2 器具缺陷 / 3 缺侧或不可判",
            "expected_direction": "**方向未预设** (该轴的成本方向明确: 省一次远端调用; 质量方向 R546/R547 未测 ⇒ 本轮作**前沿测量**, "
                                  "不预设增益也不预设损失); 任何降幅宣称必须同时过 A1/A2/A3 三条成对判据",
            "cross_check": "铁律 11 前置器 python3 eval/rover/r507pre/exec_precondition.py --round r570 (两侧产出物独立物化 + 真跑 + 逐用例判对); "
                           "rc!=0 ⇒ 全部成本/降幅读数标「参考(未可验收)」",
        },
        "axis_criteria_R570": {
            "note": "三条成对判据**先于本窗集落盘**; 缺任一条 ⇒ 不作任何成本/质量宣称 (只出读数)",
            "A1 行使面 (机制启用断言)": "transcript.early_stop_skipped Σ >= 1 且 存在 skipped>=1 的窗数 >= 1; "
                                        "Σ == 0 ⇒ 记 `mechanism-not-engaged`, 成本对比作废 (不得据此说『无增益』)",
            "A2 成本 (gain)": "同窗配对: Σcalls(E2)/Σcalls(E0) <= 0.70 ∧ Σnew_prompt(E2)/Σnew_prompt(E0) <= 0.70 "
                              "(主线阈值 ≥30% 降幅; 调用数为主口径——无 tokenizer 口径争议, 与 token 双报)",
            "A3 质量不降 (paired)": "逐窗配对 (E2 − E0) 用例数: 中位 >= -2 ∧ 无窗 <= -3 ∧ 有效窗 n >= 3",
            "宣称规则": "A1 ∧ A2 ∧ A3 全过 ⇒ 方可宣称「早停轴 = 调用降幅达标且质量不降」; 只过 A2 不过 A3 ⇒ "
                        "如实写「成本降 / 质量降」前沿读数, **禁用收益动词**; A1 不过 ⇒ 整轴作未行使处理",
        },
        "candidate4": {
            "name": "判定输入指纹 / 命中率双口径复核 (新窗)",
            "exercise_arm": "R570E2",
            "pre_registered_checks": {
                "C4-1 恒等式": "每个中继 dump: prompt_tokens == hit + miss ∧ 0 <= hit <= prompt (违反 >0 ⇒ rc=2 器具/口径缺陷)",
                "C4-2 确定性": "行使臂每窗**第 1 次调用**的 prompt sha8 全窗相同 ∧ transcript 任务/前缀 sha 全窗相同",
                "C4-3 非平凡": "call1 vs call2 的 prompt sha 跨窗**互异** (确定性 ≠ 恒定输出); 该臂每窗调用数 <2 ⇒ 记未行使, 不记 0",
                "C4-4 命中率双口径": "v_all(含冷启动) / v_incr(去冷启动) 逐窗出数; 未上报记哨兵不入比率",
            },
            "rc": "0 全过 / 2 违反 / 3 输入缺失; 未行使 ⇒ 记 honest_boundary, 不改判据",
        },
        "candidate5_gate_clause": {
            "candidate": "起手闸振幅余量条款 (上界规则 R569 已落地) **本窗集行使**",
            "rule": "MARGIN := min(max(FLOOR=60, prev_swing), ceiling_mb - GATE_MB); REQ = GATE_MB + MARGIN",
            "derivation": "prev_postcheck = eval/rover/r569/gate-postcheck-r569.json (swing_mb=90) ⇒ want=90; "
                          "cap = 本次起手前 3 次采样 max - 2650 ⇒ MARGIN = min(90, cap)",
            "fail_closed": "cap < FLOOR ⇒ rc=2 (不静默放行); 派生失败/顶棚 < REQ ⇒ 不起臂",
            "controls": {
                "PC": "连续 2 次 preflight_gate --gate-mb REQ ⇒ 期望 PASS ×2",
                "NC_hog": "400MB 占用 ⇒ 期望 GATE_BLOCKED",
                "discriminating_pair": "把内存态压进判别带 [2650, REQ): --gate-mb 2650 ⇒ PASS ∧ --gate-mb REQ ⇒ GATE_BLOCKED; "
                                       "带内不可达 ⇒ rc=3 如实登记",
            },
        },
        "evidence_scope": {"require": ["%s/%s" % (w, a) for w in WINS for a in ARMS]},
        "preregistered_expectations": {
            "quality": "前沿测量 (不预设方向); 三臂同窗配对; 单窗禁作能力结论 (R523 已立)",
            "cost": "调用数/新算 prompt/completion 三列分列 (禁名义总量); 早停省下的调用以 `early_stop_skipped` 归因",
            "honest_boundary": "g1 族的 wythoff 失分已三次定因 (产物缺陷); 本轮不修 (未放行) ⇒ 铁律 11 rc=1 可能性高, 不得据此改写判据; "
                               "步数面本轮回仓 (R569 丢失项)",
        },
        "notes": "本文件先写后跑 (runner 第 0 步机检: round / 臂集 3 / require 18 / criterion_version v2 / 两臂早停键集与取值 0 vs 2)。"
                 "判据 v2 口径不在本文件重定义, 只引用 docs/external-reference-harness.md §12。",
    }
    json.dump(pre, io.open(os.path.join(PDIR, "prereg-r570.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[预注册] arms=%s require=%d" % (sorted(pre["arms"]), len(pre["evidence_scope"]["require"])))

    d = json.load(io.open(os.path.join(PDIR, "prereg-r570.json"), encoding="utf-8"))
    assert d["round"] == "R570" and d["written_before_run"] is True
    assert set(d["arms"]) == {"C1", "R570E0", "R570E2"}, sorted(d["arms"])
    assert len(d["evidence_scope"]["require"]) == 18
    assert str(d["criterion_version"]).startswith("v2")
    doses = {a: int(d["arms"][a]["env"]["AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL"]) for a in ("R570E0", "R570E2")}
    assert doses == {"R570E0": 0, "R570E2": 2}, doses
    assert not (set(WINS) & set(WINS_PREV)), WINS
    assert len(d["axis_criteria_R570"]) >= 5
    print("[机检] 预注册 7 项全过 (early_stop=%s, wins=%s)" % (doses, WINS))
    return 0


def compile_gate():
    """派生件**语法门** (R570 自捕, 首跑实证: ingest 的 rule 串被拼出未转义引号 ⇒
    整轮 6 窗的派生件(ingest/evidence/kpi/matrix/adjudicate/precondition 发现)全缺, 而测量面完好;
    首跑只能靠运行期 SyntaxError 发现, 代价 = 后处理全重跑)。

    牙: 对每个派生 .py 跑 py_compile; 任一不过 ⇒ fail-closed rc=3 (先于起手闸/预注册, 禁起臂)。
    负控: 用**首跑真实坏行**的副本喂本函式, 必须 rc=3 (见 self_test_compile_gate)。
    """
    import py_compile
    bad = []
    for fn in DERIVED:
        dst = fn.replace("r569", "r570").replace("R569", "R570")
        if not dst.endswith(".py"):
            continue
        p = os.path.join(PDIR, dst)
        if not os.path.isfile(p):
            continue
        try:
            py_compile.compile(p, cfile=os.path.join("/tmp", "r570-pyc", dst + "c"), doraise=True)
        except py_compile.PyCompileError as e:
            bad.append({"file": dst, "err": str(e).strip().splitlines()[-1][:160]})
    return {"ok": not bad, "bad": bad}


def self_test_compile_gate():
    """语法门**负控**: 首跑真实坏行 (未转义引号 + 裸 ∨) 的副本必须被判红。

    坏行逐字取自首跑 stderr (见 readings-candidate: 首跑 6 窗 ingest 全 SyntaxError)。
    """
    import py_compile
    os.makedirs("/tmp/r570-pyc", exist_ok=True)
    bad_src = io.open(os.path.join(PDIR, "ingest_r570.py"), encoding="utf-8").read()
    cand = [l for l in bad_src.splitlines() if 'rec["rule"]' in l]
    assert cand, "锚点未命中 (锚点由产物自身派生, 禁手打列位)"
    indent = cand[0][: len(cand[0]) - len(cand[0].lstrip())]
    bad_line = ('rec["rule"] = ("调用/新算 prompt 取中继 dump 索引区段; 轴行使 ⇔ '
                'transcript.early_stop_skipped>0 "(早停) ∨ transcript.exec_repairs>0 (执行回灌); '
                '账核对 = dump 区段 vs transcript.calls")')
    arm = bad_src.replace(cand[0], indent + bad_line, 1)
    p = "/tmp/r570-pyc/negative-control-ingest.py"
    io.open(p, "w", encoding="utf-8").write(arm)
    try:
        py_compile.compile(p, cfile="/tmp/r570-pyc/nc.pyc", doraise=True)
        got = 0
    except py_compile.PyCompileError:
        got = 3
    # 正控: 现盘派生件必须过
    pos = compile_gate()["ok"]
    return {"negative_control_rc": got, "positive_control_ok": pos,
            "teeth": got == 3 and pos, "rc": 0 if (got == 3 and pos) else 2}


def main():
    os.makedirs(PDIR, exist_ok=True)
    gs = freeze_copy()
    if gs is None:
        return 3
    derive_files()
    patch_ingest()
    patch_kpi()
    r = residual_check()
    if not r["ok"]:
        print("[致命] 残留机检未过: %s" % r["hits"])
        return 3
    cg = compile_gate()
    if not cg["ok"]:
        print("[致命] 派生件语法门未过: %s" % cg["bad"])
        return 3
    scg = self_test_compile_gate()
    print("[语法门] 正控 ok=%s / 负控 rc=%s ⇒ rc=%d" % (scg["positive_control_ok"], scg["negative_control_rc"], scg["rc"]))
    if scg["rc"] != 0:
        return 2
    rs = check_runner_semantics()
    if not rs["ok"]:
        print("[致命] 驱动器语义机检未过: %s" % rs["failed"])
        return 3
    rc = prereg(gs)
    import subprocess
    r2 = subprocess.run([sys.executable, os.path.join(PDIR, "gate_margin_r570.py"), "--selftest"],
                        capture_output=True, text=True)
    print("[条款成对控制] rc=%d %s" % (r2.returncode, r2.stdout.strip()[:400]))
    if r2.returncode != 0:
        return 2
    return rc


if __name__ == "__main__":
    sys.exit(main())
