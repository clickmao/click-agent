#!/usr/bin/env python3
"""R526-4 构建配置集中化: src/Directory.Build.props + 25 个 csproj 去重
   只收敛「全员同值」的属性; 例外项目 (netstandard2.1 / LangVersion 8.0 / ImplicitUsings disable) 保留自身覆盖。"""
import io, os, re

ROOT = "/home/agentuser/AgentFramework"
os.chdir(ROOT)

PROPS = """<Project>

  <!-- R526 完全重构: 构建配置集中化 (原 25 个 csproj 各自重复 TargetFramework/Nullable/ImplicitUsings/LangVersion)。
       props 只提供默认值; 例外项目在自身 csproj 内覆盖 (netstandard2.1 / LangVersion 8.0 / ImplicitUsings disable)。 -->
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <LangVersion>latest</LangVersion>
  </PropertyGroup>

</Project>
"""

io.open("src/Directory.Build.props", "w", encoding="utf-8", newline="\n").write(PROPS)

CENTRAL = {
    "TargetFramework": "net10.0",
    "Nullable": "enable",
    "ImplicitUsings": "enable",
    "LangVersion": "latest",
}

changed = []
for dp, dn, fn in os.walk("src"):
    dn[:] = [d for d in dn if d not in ("obj", "bin")]
    for f in fn:
        if not f.endswith(".csproj"):
            continue
        p = os.path.join(dp, f)
        t = io.open(p, encoding="utf-8").read()
        orig = t
        for k, v in CENTRAL.items():
            t = re.sub(rf"[ \t]*<{k}>{re.escape(v)}</{k}>\r?\n", "", t)
        if t != orig:
            io.open(p, "w", encoding="utf-8", newline="\n").write(t)
            changed.append(p)

print(f"写入 src/Directory.Build.props; 去重 csproj {len(changed)} 个")
for p in sorted(changed):
    print("  ", p)
