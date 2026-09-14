#!/usr/bin/env python3
"""开发侧回流 digest 生成器 (R416 候选 · 最小实现).

目的: 把「链/探针的真实读数」机械汇总成**单页**文档, 让开发侧 (assistant) 的下轮上下文
      有一个可复验的唯一入口 —— 而不是靠人工读遥测/日志再靠记忆维护。

判据 (v1 只做可机械核验的部分):
  1. 每个 D 断链点: 编号 + 标题 + 状态标记 + 源文件行号 (可点回原文核验)
  2. 每个探针裁决: verdict 文件 + PASS/FAIL + 断言数 (外部真值产物的元数据)
  3. 轮次提交: 最近 N 个 R#### 提交 (本地, 未推计数)
  4. 台账: registry 行数/updated_round + kpi.jsonl 已记轮次
  5. 口径红线: 常量清单 (防"自算错而自洽")
  6. 复验命令: 规范命令逐条给出

诚实边界: 本文件不产生任何新读数, 只做汇聚; 未标注状态的 D 条目渲染为「(未标注)」,
          不猜测、不以推断代事实。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "reports" / "dev-return-digest.md"
PLAN = ROOT / "docs" / "plans" / "v0.22.0-r371-capability-probe-python-game.md"

STATUS_MARKERS = ("已验收", "已修", "待复跑", "待修", "未做", "已实施", "关闭")

PROTOCOL = [
    "AOT 是唯一发布形态; JIT 跑通只算中间证据 (IL 警告必须为 0)。",
    "测量取**外部真值**: 桩/假后端逐请求落盘, 不信被测量代码自报计数器。",
    "计数口径 tokens_evaluated = 总长, prompt_n = 新算, cache_n = 命中 (恒等; 错算 ⇒ 比率 > 1)。",
    "llm_call.truncated 是**最终**闭合性 (救回后为 false); 截断事实只在 llm_call_continue。",
    "「没测到」≠「失败」; 负控必须实测为 0, 缺正控时「仪器错」与「被测错」不可分。",
    "写源码的尖括号字面量会被工具替换 ⇒ 用转义/字符码构造常量, 写后按码点复核。",
    "推送暂停令未解除 ⇒ 只本地 commit; 凭据一律不入 git config、不硬编码。",
]


def sh(*args: str) -> str:
    p = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True)
    return p.stdout.strip()


def d_breakpoints() -> list[tuple[str, str, str, int]]:
    """⇒ [(id, title, status, line_no)]"""
    out: list[tuple[str, str, str, int]] = []
    if not PLAN.exists():
        return out
    lines = PLAN.read_text(encoding="utf-8").splitlines()
    pat = re.compile(r"^#{2,4}\s*(.*?)\bD(\d+)(-[a-z0-9]+)?\b(.*)$")
    for i, ln in enumerate(lines, 1):
        m = pat.match(ln)
        if not m:
            continue
        head, did, suffix, tail = m.group(1), m.group(2) + (m.group(3) or ""), m.group(4), m.group(4)
        status = next((s for s in STATUS_MARKERS if s in tail), "(未标注)")
        raw = re.sub(r"[（(].*?[)）]", " ", head + " " + tail)
        raw = re.sub(r"^[\s#]*R?\d{3}-?", " ", raw)          # 去 R37x- / 前导数字
        raw = re.sub(r"^\s*\d+(\.\d+)?\s*", " ", raw)      # 去 3.1 小节号
        raw = raw.replace("断链点", " ").replace(":", " ").replace("：", " ")
        raw = re.sub(r"^\s*/\s*D\d+\s*", " ", raw)   # "D7/D1 真机验收" ⇒ "真机验收"
        title = re.sub(r"\s+", " ", raw).strip(" ·-—*|")
        out.append((did, title[:52], status, i))
    # 去重: 同一 D 可能出现在多个小节 (标题/状态分散) ⇒ 取「最长标题 + 首个显式状态 + 最早行号」
    seen: dict[str, tuple[str, str, str, int]] = {}
    for did, title, status, ln in out:
        if did not in seen:
            seen[did] = (did, title, status, ln)
            continue
        p_did, p_title, p_status, p_ln = seen[did]
        best_title = p_title if len(p_title) >= len(title) else title
        best_status = p_status if p_status != "(未标注)" else status
        seen[did] = (p_did, best_title, best_status, min(p_ln, ln))
    return list(seen.values())


def probe_verdicts() -> list[tuple[str, str, str, int, str]]:
    rows: list[tuple[str, str, str, int, str]] = []
    for f in sorted((ROOT / "eval" / "rover").glob("*/verdict*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            rows.append((f.parent.name, f.name, f"UNREADABLE({e.__class__.__name__})", 0, "n/a"))
            continue
        verdict = d.get("verdict") or d.get("result") or "?"
        n, src = 0, "n/a"
        for k in ("checks", "assertions", "results", "items", "arms", "gate"):
            v = d.get(k)
            if isinstance(v, list) and v:
                n, src = len(v), k
                break
        if not n:
            for k in ("total", "passed"):
                if isinstance(d.get(k), int) and d[k]:
                    n, src = d[k], k
                    break
        if not n:  # 无列表/计数字段 ⇒ 退化为「顶层判据字段数」(布尔/数值型)
            n = sum(1 for k, v in d.items() if isinstance(v, bool))
            src = f"bool_fields" if n else "n/a"
        rows.append((f.parent.name, f.name, str(verdict), n, src))
    return rows


def inline_only_ds(heading_ids: set[str]) -> list[tuple[str, int]]:
    """正文提及但无独立小节的 D 编号 ⇒ [(id, 首次出现行)]（文档缺口, 如实暴露）"""
    if not PLAN.exists():
        return []
    lines = PLAN.read_text(encoding="utf-8").splitlines()
    pat = re.compile(r"\bD(\d+)(-[a-z0-9]+)?\b")
    seen: dict[str, int] = {}
    for i, ln in enumerate(lines, 1):
        if ln.startswith("#"):
            continue
        for m in pat.finditer(ln):
            did = m.group(1) + (m.group(2) or "")
            seen.setdefault(did, i)
    return sorted((d, ln) for d, ln in seen.items() if d not in heading_ids)


def round_commits(n: int = 25) -> tuple[list[tuple[str, str]], int]:
    log = sh("git", "log", f"-n{n}", "--pretty=%h|%s")
    rows: list[tuple[str, str]] = []
    pat = re.compile(r"\bR(\d{3})\b")
    for ln in log.splitlines():
        if "|" not in ln:
            continue
        h, s = ln.split("|", 1)
        if pat.search(s):
            rows.append((h, s))
    ahead = sh("git", "rev-list", "--count", "origin/main..HEAD") or "?"
    return rows, int(ahead) if ahead.isdigit() else -1


def ledgers() -> tuple[int, str, list[str]]:
    reg = json.loads((ROOT / "docs" / "verification-registry.json").read_text(encoding="utf-8"))
    rows = reg.get("rows", [])
    rounds: list[str] = []
    kpi = ROOT / "eval" / "capability" / "kpi.jsonl"
    if kpi.exists():
        for ln in kpi.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln).get("round")
            except Exception:  # noqa: BLE001
                continue
            if r and r not in rounds:
                rounds.append(r)
    return len(rows), str(reg.get("updated_round")), rounds


def main() -> int:
    ds = d_breakpoints()
    probes = probe_verdicts()
    commits, ahead = round_commits()
    reg_rows, reg_round, kpi_rounds = ledgers()

    L: list[str] = []
    L.append("# 开发侧回流 digest（机械生成 · 单页）")
    L.append("")
    L.append("> 生成器: `scripts/dev_return_digest.py` · 本文件**不产生新读数**，只汇聚已有外部真值产物与台账；")
    L.append("> 未标注状态的 D 条目渲染为「(未标注)」，不猜测。用途：给开发侧（assistant）下轮上下文一个可复验的唯一入口。")
    L.append("")
    L.append(f"## 1. D 断链点（源: `{PLAN.relative_to(ROOT)}`）")
    L.append("")
    L.append("| D | 标题 | 状态 | 源行 |")
    L.append("|---|---|---|---|")
    for did, title, status, ln in sorted(ds, key=lambda r: (int(re.sub(r"\D", "", r[0]) or 0), r[0])):
        L.append(f"| D{did} | {title} | {status} | L{ln} |")
    L.append("")
    L.append("## 2. 探针裁决（源: `eval/rover/*/verdict*.json`）")
    L.append("")
    L.append("| 目录 | 裁决文件 | verdict | 判据数 | 来源键 |")
    L.append("|---|---|---|---|---|")
    for d, f, v, n, src in probes:
        L.append(f"| {d} | {f} | **{v}** | {n} | `{src}` |")
    inline = inline_only_ds({d for d, *_ in ds})
    if inline:
        L.append("")
        L.append("**正文提及但无独立小节的 D 编号**（文档缺口, 不猜测其状态）: "
                 + ", ".join(f"D{d}(L{ln})" for d, ln in inline))
    L.append("")
    L.append("## 3. 轮次提交（本地；推送暂停令生效）")
    L.append("")
    L.append(f"- 未推送提交数: **{ahead if ahead >= 0 else 'n/a'}**")
    L.append("")
    L.append("| commit | 主题 |")
    L.append("|---|---|")
    for h, s in commits:
        L.append(f"| `{h}` | {s} |")
    L.append("")
    L.append("## 4. 台账")
    L.append("")
    L.append(f"- `docs/verification-registry.json`: **{reg_rows}** 行, updated_round = **{reg_round}**")
    L.append(f"- `eval/capability/kpi.jsonl` 已记轮次: {', '.join(kpi_rounds) if kpi_rounds else '(空)'}")
    L.append("- 已知盲区: 状态检测器只读 `data/probe/kpi.jsonl`; 轮次台账另有 `data/probe/capability/kpi.jsonl`（孤儿）")
    L.append("")
    L.append("## 5. 口径红线（审计对照）")
    L.append("")
    for i, p in enumerate(PROTOCOL, 1):
        L.append(f"{i}. {p}")
    L.append("")
    L.append("## 6. 复验命令")
    L.append("")
    L.append("```bash")
    L.append('export DOTNET_ROOT="$HOME/.dotnet"')
    L.append('env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \\')
    L.append('  "$HOME/.dotnet/dotnet" test src/agent.tests/agentframework.tests.csproj -c Release')
    L.append('"$HOME/.dotnet/dotnet" publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_release')
    L.append("python3 scripts/dev_return_digest.py   # 重新生成本文件")
    L.append("```")
    L.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    txt = OUT.read_text(encoding="utf-8")
    import hashlib

    print(f"WROTE {OUT.relative_to(ROOT)} bytes={len(txt.encode())} lines={txt.count(chr(10))}")
    print(f"sha256={hashlib.sha256(txt.encode()).hexdigest()[:16]}")
    print(f"d_items={len(ds)} probes={len(probes)} commits={len(commits)} ahead={ahead} reg_rows={reg_rows} reg_round={reg_round}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
