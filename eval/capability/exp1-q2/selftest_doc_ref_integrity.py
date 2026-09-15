#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_doc_ref_integrity.py 的仪器自证 (multi-state fixtures + CLI 入口回放)。

为什么要有它: 本轮第一版探针把「无目录裸文件名」判成 stale_path (389 条虚高), 是**人工读桶**
才发现的。没有仪器自证, 探针的读数就只能靠人盯 —— 本文件把「探针的判定行为」钉成可回归断言。

判据 (每条都要两侧样例: 该判红必红, 该放行必放行):
  S1  正常引用 (文件存在 + 行号在范围 + 行内符号存在) ⇒ ok
  S2  语料内路径不存在 ⇒ stale_path                      (该红必红)
  S3  行号越界 ⇒ stale_lines                             (该红必红)
  S4  路径/行号成立但符号全文件缺失 ⇒ symbol_absent      (候选红)
  S5  代码围栏内引用 ⇒ skipped_fence, 且**不进** live 判定桶
  S6  裸文件名唯一候选 ⇒ 解析成事实判定 (不是弃权)
  S7  裸文件名多候选 ⇒ waived/ambiguous_bare_name (**不得**判 stale)
  S8  裸文件名零候选 ⇒ waived/unresolvable_bare_name (**不得**判 stale)
  S9  语料外命名空间 ⇒ waived/out_of_scope (**不得**判 stale)
  S10 G4 两侧: 目标类型缺席 ⇒ premise_refuted=True; 目标类型在场 ⇒ False (不是恒真门)
  S11 G1 正/负控: 正控 >0 ∧ 负控 ==0 (计数器不得恒 0/恒真)
  S12 确定性: 同一 fixture 两跑读数逐位相同
  S13 CLI 入口回放: 以子进程调入口, 产出 result.json 必含 gate_pass/exit_code/criteria_pre_registered
  S14 弃权闸: --expect-mixed ⇒ exit 3 (弃权不判红)
  S15 环境失败 ⇒ exit 3 (不崩、不误判红)
  S16 非平凡: 两族的引用文档集合互异 (or 双空)

三态退出码: 0 全部符合预期 / 2 有断言不符 (真红) / 3 仪器或环境自身失败 (弃权)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probe_doc_ref_integrity.py"

SYMBOLS_CS = """// fixture: 正控符号容器
public interface IResponseSegmentPlugin { }
public interface IFooPlugin { }
public class CapabilityScanner { }
public class PythonArtifactPlugin : IResponseSegmentPlugin { }
public class FooImpl : IFooPlugin { }
"""

FOO_CS = """public class FooHelper
{
    public int Value = 1;
}
"""

LEGACY_CS = """// fixture: 目标类型在场分支 (G4 另一侧)
public interface ICapabilityPlugin { }
public class PluginExecutionResult { }
public class CapabilityPluginRegistry { }
"""

DOCS = {
    "good.md": "引用事实: src/lib/Foo.cs:1 定义了 `FooHelper` (行内符号存在)。\n",
    "stale_path.md": "已删文件: src/Deleted.cs:3 (`GhostPlugin`)。\n",
    "stale_lines.md": "越界行号: src/lib/Foo.cs:999 (`FooHelper`)。\n",
    "sym_absent.md": "符号缺失: src/lib/Foo.cs:1 (`NotThereSymbolZq`)。\n",
    "fenced.md": "命令输出示例 (围栏内不算引用事实):\n\n```\n$ git show src/lib/Foo.cs:2\n```\n",
    "bare_unique.md": "同名唯一: Foo.cs:2 (`FooHelper`)。\n",
    "bare_ambig.md": "多候选: Dup.cs:1 (`DupA`)。\n",
    "bare_missing.md": "无候选: Nope.cs:1。\n",
    "out_of_scope.md": "语料外: vendor/third_party/x.cs:1。\n",
    "relocated.md": "已搬家: src/legacy/Moved.cs:1 (`MovedHelper`)。\n",
    "relocated_multi.md": "搬家多候选: src/legacy/Dup.cs:1。\n",
}


# R444 加固: 未知参数必须 fail-closed (L2 器具验收面负控) —— 原实现静默忽略未知参数。
_UNKNOWN = [a for a in sys.argv[1:] if a.startswith("--") and a.split("=")[0] not in ("--expect-mixed", "--out", "--repo")]
if _UNKNOWN:
    print("用法错误: 未知参数 %s" % _UNKNOWN, file=sys.stderr)
    sys.exit(2)

def build_fixture(root: Path, legacy: bool = False):
    (root / "src" / "lib").mkdir(parents=True, exist_ok=True)
    (root / "src" / "other").mkdir(parents=True, exist_ok=True)
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "src" / "lib" / "Symbols.cs").write_text(SYMBOLS_CS, encoding="utf-8")
    (root / "src" / "lib" / "Foo.cs").write_text(FOO_CS, encoding="utf-8")
    (root / "src" / "lib" / "Dup.cs").write_text("public class DupA { }\n", encoding="utf-8")
    (root / "src" / "other" / "Dup.cs").write_text("public class DupB { }\n", encoding="utf-8")
    (root / "src" / "lib" / "Moved.cs").write_text("public class MovedHelper { }\n", encoding="utf-8")
    if legacy:
        (root / "src" / "lib" / "Legacy.cs").write_text(LEGACY_CS, encoding="utf-8")
        (root / "docs" / "legacy_a.md").write_text(
            "旧契约甲: src/lib/Legacy.cs:2 (`ICapabilityPlugin`)。\n", encoding="utf-8")
        (root / "docs" / "legacy_b.md").write_text(
            "旧契约乙: src/lib/Legacy.cs:3 (`PluginExecutionResult`)。\n", encoding="utf-8")
    for name, text in DOCS.items():
        (root / "docs" / name).write_text(text, encoding="utf-8")


def run_probe(repo: Path, out: Path, extra=None, timeout=120):
    cmd = [sys.executable, str(PROBE), "--repo", str(repo), "--out", str(out)]
    cmd.extend(extra or [])
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    data = None
    if out.is_file():
        try:
            data = json.loads(out.read_text(encoding="utf-8"))
        except Exception:
            data = None
    if data is not None:
        cj = out.with_name("citations.jsonl")
        if cj.is_file():
            rows = []
            for line in cj.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
            data["citations"] = rows
    return p.returncode, data, (p.stdout or "")[-400:], (p.stderr or "")[-400:]


CHECKS = []


def check(name, ok, detail):
    CHECKS.append({"id": name, "ok": bool(ok), "detail": detail})


def verdict_for(res, doc, path):
    for c in res["citations"]:
        if c["doc"] == doc and c["path"] == path:
            return c
    return None


def main():
    tmp = Path(tempfile.mkdtemp(prefix="exp1q2-selftest-"))
    try:
        fixA = tmp / "fixA"
        fixB = tmp / "fixB"
        build_fixture(fixA, legacy=False)
        build_fixture(fixB, legacy=True)

        outA = tmp / "resultA.json"
        rcA, A, soA, seA = run_probe(fixA, outA)
        if A is None:
            print(json.dumps({"stage": "selftest", "error": "probe produced no JSON (fixA)",
                              "rc": rcA, "stdout": soA, "stderr": seA, "exit_code": 3},
                             ensure_ascii=False, indent=2))
            return 3

        live = [c for c in A["citations"] if c["kind"] == "code" and not c["in_code_fence"]]
        tally = A["citation_verdicts"]
        waive = A["waive_reasons"]

        g = verdict_for(A, "docs/good.md", "src/lib/Foo.cs")
        check("S1_ok", g and g["verdict"] == "ok", g)

        s = verdict_for(A, "docs/stale_path.md", "src/Deleted.cs")
        check("S2_stale_path", s and s["verdict"] == "stale_path"
              and s["resolve_mode"] == "in_scope_missing", s)

        s = verdict_for(A, "docs/stale_lines.md", "src/lib/Foo.cs")
        check("S3_stale_lines", s and s["verdict"] == "stale_lines",
              {"verdict": (s or {}).get("verdict"), "file_lines": (s or {}).get("file_lines")})

        s = verdict_for(A, "docs/sym_absent.md", "src/lib/Foo.cs")
        check("S4_symbol_absent", s and s["verdict"] == "symbol_absent"
              and s["symbols_absent"] == ["NotThereSymbolZq"], s)

        fenced = [c for c in A["citations"] if c["in_code_fence"]]
        check("S5_fence_skipped", len(fenced) == 1 and fenced[0]["verdict"] == "skipped_fence"
              and fenced[0]["doc"] == "docs/fenced.md"
              and all(not c["in_code_fence"] for c in live), {"n_fenced": len(fenced)})

        s = verdict_for(A, "docs/bare_unique.md", "Foo.cs")
        check("S6_bare_unique_resolved", s and s["resolve_mode"] == "unique_basename"
              and s["verdict"] == "ok", s)

        s = verdict_for(A, "docs/bare_ambig.md", "Dup.cs")
        check("S7_bare_ambiguous_waived", s and s["verdict"] == "waived"
              and s.get("waive_reason") == "ambiguous_bare_name", s)

        s = verdict_for(A, "docs/bare_missing.md", "Nope.cs")
        check("S8_bare_missing_waived", s and s["verdict"] == "waived"
              and s.get("waive_reason") == "unresolvable_bare_name", s)

        s = verdict_for(A, "docs/out_of_scope.md", "vendor/third_party/x.cs")
        check("S9_out_of_scope_waived", s and s["verdict"] == "waived"
              and s.get("waive_reason") == "out_of_scope", s)

        # 第四级: 路径失效但同名文件在树内搬家 (与"已删除"必须分开)
        s = verdict_for(A, "docs/relocated.md", "src/legacy/Moved.cs")
        check("S17_relocated_single_fact_ok", s and s["verdict"] == "relocated"
              and len(s.get("relocated_to") or []) == 1
              and s.get("relocated_fact_verdict") == "ok", s)

        s = verdict_for(A, "docs/relocated_multi.md", "src/legacy/Dup.cs")
        check("S18_relocated_multi_no_fact", bool(s) and s["verdict"] == "relocated"
              and len(s.get("relocated_to") or []) == 2
              and "relocated_fact_verdict" not in s, s)

        check("S19_relocated_not_stale", tally.get("relocated", 0) == 2
              and A["stale_like_n"] == 3, {"tally": tally, "stale_like_n": A["stale_like_n"]})

        # 弃权不得计入 stale
        check("S9b_waived_not_stale", tally.get("waived", 0) == 3 and waive == {
            "ambiguous_bare_name": 1, "unresolvable_bare_name": 1, "out_of_scope": 1},
            {"tally": tally, "waive": waive})

        check("S10a_G4_true_when_absent", A["gates"]["G4_premise_refuted"] is True
              and A["q2_decision_data"]["premise_reuse_existing_contract_holds"] is False,
              A["q2_decision_data"]["target_symbol_counts"])

        outB = tmp / "resultB.json"
        rcB, B, soB, seB = run_probe(fixB, outB)
        check("S10b_G4_false_when_present", B is not None
              and B["gates"]["G4_premise_refuted"] is False
              and B["q2_decision_data"]["premise_reuse_existing_contract_holds"] is True,
              B and B["q2_decision_data"]["target_symbol_counts"])

        occ = A["symbol_occurrences"]
        check("S11_controls_two_sided",
              occ.get("IResponseSegmentPlugin", 0) > 0 and occ.get("CapabilityScanner", 0) > 0
              and occ.get("PythonArtifactPlugin", 0) > 0
              and occ.get("NoSuchTypeZzq9Xx", 0) == 0 and occ.get("RegistryThatNeverExistedZq", 0) == 0,
              {k: v for k, v in occ.items() if k in ("IResponseSegmentPlugin", "CapabilityScanner",
                                                     "PythonArtifactPlugin", "NoSuchTypeZzq9Xx")})

        outA2 = tmp / "resultA2.json"
        rcA2, A2, _, _ = run_probe(fixA, outA2)
        same = bool(A2 and A2["citation_verdicts"] == A["citation_verdicts"]
                    and A2["symbol_occurrences"] == A["symbol_occurrences"])
        check("S12_two_pass_identical", same and A["gates"]["G2_two_pass_identical"] is True, None)

        required = {"gate_pass", "exit_code", "criteria_pre_registered", "citation_verdicts",
                    "honest_boundaries", "checks_posthoc", "evidence_level"}
        check("S13_cli_entry_contract", rcA in (0, 2, 3) and required.issubset(A.keys())
              and A["evidence_level"] == "L1-static" and A["exit_code"] == rcA,
              {"rc": rcA, "missing": sorted(required - set(A.keys()))})

        rcM, M, _, _ = run_probe(fixA, tmp / "resultM.json", extra=["--expect-mixed"])
        check("S14_waiver_gate_exit3", rcM == 3, {"rc": rcM})

        rcX, X, _, _ = run_probe(tmp / "does-not-exist", tmp / "resultX.json")
        check("S15_env_failure_abstains", rcX == 3 and X is None, {"rc": rcX})

        fd = A["gates"]["G5_family_docs"]
        sigs = {k: tuple(v) for k, v in fd.items()}
        check("S16_nontrivial_families", len(set(sigs.values())) > 1 or all(not v for v in sigs.values())
              and A["gates"]["G5_families_distinct"] is True, {k: len(v) for k, v in fd.items()})

        n_bad = sum(1 for c in CHECKS if not c["ok"])
        summary = {
            "selftest": "exp1-q2-instrument-selfproof",
            "n_checks": len(CHECKS), "n_failed": n_bad,
            "failed": [c for c in CHECKS if not c["ok"]],
            "fixture_tally_A": A["citation_verdicts"],
            "fixture_waive_A": A["waive_reasons"],
            "probe_rc_A": rcA,
            "exit_code": 0 if n_bad == 0 else 2,
        }
        (tmp / "selftest_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                                   encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        # 固化到证据目录 (供复核)
        dst = HERE / "selftest_result.json"
        dst.write_text(json.dumps({"summary": summary, "checks": CHECKS},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
        return summary["exit_code"]
    except Exception as exc:
        print(json.dumps({"stage": "selftest-harness", "error": repr(exc), "exit_code": 3},
                         ensure_ascii=False))
        return 3
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
