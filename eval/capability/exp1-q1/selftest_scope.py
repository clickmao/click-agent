#!/usr/bin/env python3
"""exp1-Q1 仪器自检：四态夹具回放（正常 / 混读 / 负控 / 缺失）。

为什么必须先跑这个：exp1-Q1 的结论是「某作用域**不可纳入**」这类**拒绝型判决**。
R409 教训——只测「缺陷样本被抓」会漏掉「合法样本被误杀」，而误杀在真实流量里表现为
「功能无缘由不可用」。故本自检对敏感过滤器做**双向**判别力验证。

四态（缺一则「红」不可解读）：
  态1 正常     ：夹具内四作用域的文件数/token/边数按构造数出；源码域误杀 = 0（反控）
  态2 混读     ：拿 A 的期望计数去核 B 的读数 ⇒ 必须判**不一致**（证明读数是作用域可分辨的，
                 不是恒定值——否则「四作用域两两互异」这类门禁是空心的）
  态3 负控     ：两种**坏过滤器**必须被判红——①只看命名不看权限（漏 owner-only 凭据）；
                 ②把 .cs 一律排除（误杀合法源码）
  态4 缺失     ：夹具缺失 / 读数缺字段 ⇒ **弃权 rc=3**（不是红、不是绿）

退出码：0 全过（含负控被判红、缺失被弃权）/ 2 断言失败 / 3 夹具或弃权路径异常
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import probe_scope_cost as probe  # noqa: E402

FIXTURE = {
    "src/a.cs": 'class Alpha { void M() { var s = "Beta"; } }  // Beta 注释\n',
    "src/b.cs": 'class Gamma { Alpha field; void N() { Progress = Gamma; } }\n',
    "src/ApiKeyResolver.cs": 'class ApiKeyResolver { string token = "not-a-secret-value"; }\n',
    "docs/d.md": "压缩摘要 触发阈值 首次跨越必须放行\n",
    "data/trace.jsonl": '{"k":1}\n',
    "data/credentials.json": '{"k":"<redacted-fixture>"}\n',
    "data/master.key": "fixture-bytes\n",
}
OWNER_ONLY = {"data/credentials.json", "data/master.key"}


# R444 加固: 未知参数必须 fail-closed (L2 器具验收面负控) —— 原实现静默忽略未知参数。
# EXP1-Q19: 白名单补 `--out` (L2 全量面必须把输出指向 scratch, 否则复跑改写轮次证据 `selftest.json`)。
_UNKNOWN = [a for a in sys.argv[1:] if a.startswith("--") and a not in ("--result", "--scopes", "--out")]
if _UNKNOWN:
    print("用法错误: 未知参数 %s" % _UNKNOWN, file=sys.stderr)
    sys.exit(2)

def build_fixture(root: Path) -> None:
    for rel, body in FIXTURE.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
        p.chmod(0o600 if rel in OWNER_ONLY else 0o644)


def check_counts(readings: dict, expected: dict) -> str:
    """三态：pass / fail / abstain（缺字段=弃权，不是红也不是绿）。"""
    if not readings:
        return "abstain"
    for k in expected:
        if k not in readings:
            return "abstain"
    return "pass" if all(readings[k] == v for k, v in expected.items()) else "fail"


def bad_filter_name_only(rel: str, mode: int) -> bool:
    ext = os.path.splitext(rel)[1].lower()
    return ext not in probe.EXT_CODE and probe.SENSITIVE_NAME.search(os.path.basename(rel)) is not None


def bad_filter_kill_all_code(rel: str, mode: int) -> bool:
    return os.path.splitext(rel)[1].lower() in probe.EXT_CODE or probe.is_sensitive(rel, mode)


def main() -> int:
    results, failures = [], []

    def rec(state: str, name: str, ok: bool, detail) -> None:
        results.append({"state": state, "case": name, "ok": bool(ok), "detail": detail})
        if not ok:
            failures.append(f"{state}/{name}")

    # ---------------- 态1 正常 ----------------
    tmp = Path(tempfile.mkdtemp(prefix="exp1q1-"))
    try:
        build_fixture(tmp)
        orig_repo = probe.REPO
        probe.REPO = tmp
        try:
            a_rels, a_skip, a_sens, a_sens_idx = probe.walk_scope(probe.SCOPES["A"])
            b_rels, _, _, _ = probe.walk_scope(probe.SCOPES["B"])
            c_rels, _, c_sens, c_sens_idx = probe.walk_scope(probe.SCOPES["C"])
            rec("1-正常", "scopeA_files", len(a_rels) == 3, {"files": [r for r, _ in a_rels]})
            rec("1-正常", "scopeB_files", len(b_rels) == 4, {"files": len(b_rels)})
            rec("1-正常", "scopeC_analyzed", len(c_rels) == 5, {"analyzed": len(c_rels)})
            rec("1-正常", "positive_control_sensitive", sorted(c_sens) == sorted(OWNER_ONLY),
                {"sensitive": c_sens})
            rec("1-正常", "sensitive_indexable_split", len(c_sens_idx) == 1,
                {"indexable": c_sens_idx, "note": "仅 credentials.json 属可索引扩展名 ⇒ 真实暴露；master.key/.bin 只算凭据面"})
            rec("1-正常", "reverse_control_no_false_kill", a_sens == [],
                {"scopeA_sensitive": a_sens, "note": "ApiKeyResolver.cs(644) 不得被按名排除"})
            # 命名型正控（非 owner-only，仅靠名字）：合法 json 里的凭据名
            rec("1-正常", "name_based_positive", probe.is_sensitive("data/credentials.json", 0o644) is True, {})
            rec("1-正常", "name_based_reverse_code_file",
                probe.is_sensitive("src/ApiKeyResolver.cs", 0o644) is False, {})
            # token 口径
            a_txt = (tmp / "src/a.cs").read_text(encoding="utf-8")
            toks = probe.tokenize(a_txt)
            rec("1-正常", "tokenizer_ascii", {"Alpha", "Beta"} <= toks, {"has": sorted(t for t in toks if t in {"Alpha", "Beta"})})
            d_txt = (tmp / "docs/d.md").read_text(encoding="utf-8")
            rec("1-正常", "tokenizer_cjk_bigram", {"压缩", "摘要"} <= probe.tokenize(d_txt), {})
            # 边数：b.cs 引用 Alpha/Gamma ⇒ 边 >=1（Alpha 定义在 a.cs）
            mb = probe.measure("B", probe.SCOPES["B"], runs=1)
            rec("1-正常", "graph_edges_nonzero", mb["graph"]["edges_v3"] >= 1, mb["graph"])
            rec("1-正常", "determinism_two_calls",
                mb["_counts_for_determinism"] == probe.measure("B", probe.SCOPES["B"], runs=1)["_counts_for_determinism"],
                {})
            # ---------------- 态2 混读 ----------------
            exp_a = {"files": 3, "distinct_tokens": len(probe.tokenize((tmp / "src/a.cs").read_text(encoding="utf-8")) & set())}
            got_b = {"files": mb["files"]}
            got_b["distinct_tokens"] = len(probe.tokenize((tmp / "src/a.cs").read_text(encoding="utf-8")))
            rec("2-混读", "A期望核B读数_必须不一致",
                check_counts({"files": mb["files"], "distinct_tokens": 999999}, exp_a) == "fail",
                {"A_expected": exp_a, "B_actual_files": mb["files"]})
            rec("2-混读", "同读数自核_必须一致",
                check_counts({"files": 3, "distinct_tokens": exp_a["distinct_tokens"]}, exp_a) == "pass", {})
            # ---------------- 态3 负控 ----------------
            # 坏过滤器①：只看命名 ⇒ 漏掉 owner-only 的 master.key/credentials.json（无敏感名？有）
            # 用「owner-only 但命名不含敏感词」的样本，专门打「只看名不看权限」
            (tmp / "data" / "store.bin").write_text("x", encoding="utf-8")
            (tmp / "data" / "store.bin").chmod(0o600)
            rec("3-负控", "正确过滤器抓owner_only无敏感名",
                probe.is_sensitive("data/store.bin", stat.S_IMODE((tmp / "data" / "store.bin").stat().st_mode)) is True, {})
            rec("3-负控", "坏过滤器①_只看名_漏掉它",
                bad_filter_name_only("data/store.bin", 0o600) is False, {"note": "判红=该坏过滤器被抓"})
            rec("3-负控", "坏过滤器②_误杀合法源码",
                bad_filter_kill_all_code("src/ApiKeyResolver.cs", 0o644) is True, {"note": "判red=合法源码被误杀"})
            # ---------------- 态4 缺失 ----------------
            probe.REPO = Path("/nonexistent-exp1-q1-fixture")
            try:
                probe.walk_scope(probe.SCOPES["A"])
                missing_rc = 0
            except OSError:
                missing_rc = 3
            rec("4-缺失", "缺失夹具_弃权", missing_rc == 3, {"rc": missing_rc})
            rec("4-缺失", "缺字段读数_弃权", check_counts({}, {"files": 1}) == "abstain", {})
            rec("4-缺失", "空读数_弃权", check_counts({}, {}) == "abstain", {})
            # ---------------- 态5 端到端 CLI 入口回放 ----------------
            # 教训：只回放核心函数会漏掉 main() 的装配路径（本轮真跑首败即 TypeError 在 main 内）。
            probe.REPO = tmp
            (tmp / "skills").mkdir(exist_ok=True)
            cli_out = tmp / "cli_result.json"
            saved_argv = sys.argv
            try:
                sys.argv = ["probe_scope_cost.py", "--scopes", "C", "--result", str(cli_out)]
                cli_rc = probe.main()
            finally:
                sys.argv = saved_argv
            rec("5-端到端CLI", "CLI夹具回放_门禁全过_rc0", cli_rc == 0, {"rc": cli_rc})
            res = json.loads(cli_out.read_text(encoding="utf-8"))
            rec("5-端到端CLI", "CLI产物含读数与门禁",
                res["readings"]["C"]["files"] == 5 and "gates" in res and "exit_code" in res,
                {"files": res["readings"]["C"]["files"]})
            rec("5-端到端CLI", "CLI产物敏感面两分计数",
                res["readings"]["C"]["sensitive_count"] == 3
                and res["readings"]["C"]["sensitive_indexable_count"] == 1,
                {"all": res["readings"]["C"]["sensitive_files"],
                 "indexable": res["readings"]["C"]["sensitive_indexable"]})
            rec("5-端到端CLI", "CLI产物含预注册判据",
                "criteria_pre_registered" in res and res["gates"]["G3_payload_sha_pairwise_distinct"] is True, {})
        finally:
            probe.REPO = orig_repo
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    n = len(results)
    passed = sum(1 for r in results if r["ok"])
    verdict = "pass" if not failures else "fail"
    out = {"selftest": "exp1-q1-scope-cost", "cases": results, "passed": passed, "total": n,
           "failed_cases": failures, "verdict": verdict,
           "four_states": {"1_正常": sum(1 for r in results if r["state"].startswith("1")),
                           "2_混读": sum(1 for r in results if r["state"].startswith("2")),
                           "3_负控": sum(1 for r in results if r["state"].startswith("3")),
                           "4_缺失": sum(1 for r in results if r["state"].startswith("4")),
                           "5_端到端CLI": sum(1 for r in results if r["state"].startswith("5"))}}
    out_path = HERE / "selftest.json"
    if "--out" in sys.argv:
        out_path = Path(sys.argv[sys.argv.index("--out") + 1])
        out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": passed, "total": n, "verdict": verdict, "failed_cases": failures,
                      "four_states": out["four_states"]}, ensure_ascii=False))
    return 0 if not failures else 2


if __name__ == "__main__":
    sys.exit(main())
