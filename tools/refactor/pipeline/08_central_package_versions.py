#!/usr/bin/env python3
"""R527 候选④ — 中央包版本 (CPM): src/Directory.Packages.props 接管全部 PackageReference 版本。

口径:
  * 收集 src 下全部 csproj 的 PackageReference (id, version); 同一 id 出现两个不同版本 ⇒ fail-closed 拒收。
  * 生成 src/Directory.Packages.props (ManagePackageVersionsCentrally=true + 逐包 PackageVersion, 字典序)。
  * 删除 csproj 内 PackageReference 的 Version="..." (保留 PrivateAssets/IncludeAssets 等其它属性)。
  * 幂等: 连跑两次字节恒定。负控 --selfcheck 注入重复包+冲突版本必须被拒。
"""
from __future__ import annotations

import argparse
import glob
import io
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = "/home/agentuser/AgentFramework"
SRC = os.path.join(ROOT, "src")
PROPS = os.path.join(SRC, "Directory.Packages.props")

RX_PKGREF = re.compile(r'<PackageReference\b[^>]*?/>', re.S)
RX_VER = re.compile(r'\s+Version="([^"]*)"')
RX_PV = re.compile(r'<PackageVersion\s+Include="([^"]+)"\s+Version="([^"]+)"\s*/>')


def read_props(path=PROPS):
    """已有中央版本 (幂等/防回退: 只按 id 增量合并, 绝不因为某些 csproj 被 revert 而丢条目)。"""
    out: dict[str, str] = {}
    if os.path.exists(path):
        for pid, ver in RX_PV.findall(io.open(path, encoding="utf-8").read()):
            out[pid] = ver
    return out


def collect(paths):
    pkgs: dict[str, str] = {}
    conflicts = []
    for p in paths:
        try:
            tree = ET.parse(p)
        except ET.ParseError as e:
            conflicts.append(f"{p}: XML 解析失败 {e}")
            continue
        for ref in tree.iter("PackageReference"):
            pid = ref.get("Include") or ref.get("Update")
            ver = ref.get("Version")
            if pid is None:
                conflicts.append(f"{p}: PackageReference 无 Include/Update")
                continue
            if ver is None:
                continue  # 已由 CPM 接管
            prev = pkgs.get(pid)
            if prev is not None and prev != ver:
                conflicts.append(f"{pid}: 版本冲突 {prev} vs {ver} ({p})")
            pkgs[pid] = ver
    return pkgs, conflicts


def write_props(pkgs: dict[str, str]) -> str:
    lines = [
        "<Project>",
        "",
        "  <!-- R527 (候选④): 中央包版本 (CPM)。版本号唯一权威源 = 本文件;",
        "       csproj 内 PackageReference 只留 Include (以及 PrivateAssets 等非版本属性)。",
        "       ManagePackageVersionsCentrally=true ⇒ 任何漏声明的包 id 会在 restore 期 fail-closed 报错。 -->",
        "  <PropertyGroup>",
        "    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>",
        "  </PropertyGroup>",
        "",
        "  <ItemGroup>",
    ]
    for pid in sorted(pkgs):
        lines.append(f'    <PackageVersion Include="{pid}" Version="{pkgs[pid]}" />')
    lines += ["  </ItemGroup>", "", "</Project>", ""]
    return "\n".join(lines)


def strip_versions(paths, apply: bool) -> int:
    hit = 0
    for p in paths:
        txt = io.open(p, encoding="utf-8").read()
        orig = txt

        def repl(m):
            nonlocal hit
            tag = m.group(0)
            if 'Version="' not in tag:
                return tag
            hit += 1
            return RX_VER.sub("", tag)

        txt = RX_PKGREF.sub(repl, txt)
        if apply and txt != orig:
            io.open(p, "w", encoding="utf-8").write(txt)
    return hit


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(SRC, "*", "*.csproj")))
    if a.selfcheck:
        # 负控: 人造「同包两版本」必须被拒; 正控: 同包同版本不得误报。
        import tempfile
        bad = []
        with tempfile.TemporaryDirectory() as d:
            mk = lambda n, v: (lambda p: (io.open(p, "w", encoding="utf-8").write(
                f'<Project><ItemGroup><PackageReference Include="Xunit" Version="{v}" /></ItemGroup></Project>'), p)[1])(
                os.path.join(d, n))
            p1, p2 = mk("a.csproj", "1.0.0"), mk("b.csproj", "2.0.0")
            pkgs, conflicts = collect([p1, p2])
            if not conflicts or "Xunit" not in conflicts[0]:
                bad.append(f"负控未拒收: pkgs={pkgs} conflicts={conflicts}")
            io.open(p2, "w", encoding="utf-8").write(
                '<Project><ItemGroup><PackageReference Include="Xunit" Version="1.0.0" /></ItemGroup></Project>')
            pkgs, conflicts = collect([p1, p2])
            if conflicts or pkgs.get("Xunit") != "1.0.0":
                bad.append(f"正控误报: pkgs={pkgs} conflicts={conflicts}")
        for b in bad:
            print("  自检失败", b)
        print(f"NC_SELFCHECK conflict_rejected={not bad} 树内 csproj 版本残留="
              f"{sum(len(RX_VER.findall(io.open(p, encoding='utf-8').read())) for p in paths)}")
        return 1 if bad else 0

    pkgs, conflicts = collect(paths)
    merged = read_props()          # 已有条目先保留
    for pid, ver in pkgs.items():
        if pid in merged and merged[pid] != ver:
            conflicts.append(f"{pid}: 中央版本 {merged[pid]} vs csproj {ver}")
        merged[pid] = ver
    if conflicts:
        print("FAIL-CLOSED 拒收:")
        for c in conflicts:
            print("   ", c)
        return 1

    doc = write_props(merged)
    if a.apply:
        old = io.open(PROPS, encoding="utf-8").read() if os.path.exists(PROPS) else ""
        if old != doc:
            io.open(PROPS, "w", encoding="utf-8").write(doc)
    stripped = strip_versions(paths, a.apply)
    residual = sum(len(RX_VER.findall(io.open(p, encoding="utf-8").read())) for p in paths)
    if a.apply and residual:
        print(f"FAIL-CLOSED 残留 csproj Version= 属性 {residual} 处 (应在 0)")
        return 1
    print(f"csproj={len(paths)} 包 id={len(merged)} 去版本命中={stripped} 残留={residual} apply={a.apply}")
    for pid in sorted(merged):
        print(f"   {pid} = {merged[pid]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
