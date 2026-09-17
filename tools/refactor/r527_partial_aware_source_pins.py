#!/usr/bin/env python3
"""R527 候选③ 维护: 源级钉死断言改为「按类型读全部 partial 文件」。

问题 (R527 实测): R526 把"单类型单文件"放宽为"单类型 = 主文件 + 同名分片 (<Type>.<Suffix>.cs)", 但
测试里 27 处源级钉死仍是 `File.ReadAllText(Path.Combine(root, "...../ ModelQueueRouter.cs"))` ——
分片一拆, 断言就读不到真身 (R527 全量测试: 1755 中 8 条失败, 全部属这一族)。

修法 (机械):
  1) 新增 `src/agent.tests/SourcePin.cs`: 唯一入口, 读「主文件 + 同名分片」并拼接。
     严格口径: 分片必须匹配 `^<Stem>\\..+\\.cs$` (至少一个点), 故 `<Stem>Text.cs` 这类**别的类型**不会被吸进来。
  2) 全测试目录机械改写 `File.ReadAllText(Path.Combine(<root>, ... "X.cs" ))` → `SourcePin.TextParts(...,"X.cs")`;
     5 个本地 helper (Flat/Src/Source/ReadSrc) 的**函数体**改走 SourcePin (调用点不动)。
  3) 只改读法, 不改断言: 判据条数/测试条目数不变 (R526 基线 1755)。
"""
import os
import re
import subprocess
import sys

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
TESTS = os.path.join(ROOT, "src", "agent.tests")

SOURCE_PIN = '''using System;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;

namespace agent.tests;

/// <summary>
/// R527: 结构不变式 R526 起把「单类型单文件」放宽为「单类型 = 主文件 + 同名分片 (&lt;Type&gt;.&lt;Suffix&gt;.cs)」。
/// 于是所有**源级钉死**断言 (读某类型源码断言字符串) 必须读「该类型的全部分片」——否则分片拆完断言就假阴性
/// (R527 实测: ModelQueueRouter / ContextAssembler 拆分 ⇒ 全量 1755 中 8 条失败, 全部属这一族)。
///
/// 本类是**唯一入口**; 分片匹配口径严格: `^&lt;Stem&gt;\\..+\\.cs$`, 即必须多一个点 ——
/// 因此 `LlamaCppClientText.cs` 这种**另一个类型**绝不会被吸进 `LlamaCppClient` 的读取里。
/// </summary>
internal static class SourcePin
{
    /// <summary>仓库根 (含 agent.sln 的目录)。</summary>
    public static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        for (var i = 0; i < 12 && dir is not null; i++)
        {
            if (File.Exists(Path.Combine(dir.FullName, "agent.sln"))) return dir.FullName;
            dir = dir.Parent;
        }
        return ".";
    }

    /// <summary>某类型源码全量 = 主文件 + 同名分片 (按文件名序拼接)。</summary>
    public static string Text(string relativePath)
    {
        var main = Path.Combine(RepoRoot(), relativePath.Replace('/', Path.DirectorySeparatorChar));
        var dir = Path.GetDirectoryName(main);
        if (dir is null || !Directory.Exists(dir) || !File.Exists(main)) return File.ReadAllText(main!);

        var stem = Path.GetFileNameWithoutExtension(main);
        var rx = new Regex("^" + Regex.Escape(stem) + @"\\..+\\.cs$");
        var files = Directory.EnumerateFiles(dir, "*.cs")
            .Where(f => Path.GetFileName(f) == stem + ".cs" || rx.IsMatch(Path.GetFileName(f)))
            .OrderBy(f => Path.GetFileName(f), StringComparer.Ordinal)
            .ToArray();
        if (files.Length == 0) files = new[] { main };
        return string.Join("\\n", files.Select(File.ReadAllText));
    }

    /// <summary>路径分段形式。</summary>
    public static string TextParts(params string[] parts) => Text(Path.Combine(parts).Replace(Path.DirectorySeparatorChar, '/'));
}
'''

HELPER_EDITS = [
    ("UserFacingFailureTests.cs",
     "        => string.Join(' ', File.ReadAllText(Path.Combine(RepoRoot(), relative))\n",
     "        => string.Join(' ', SourcePin.Text(relative)\n"),
    ("R475AccountingTests.cs",
     "        => File.ReadAllText(Path.Combine(new[] { RepoRoot() }.Concat(parts).ToArray()));\n",
     "        => SourcePin.TextParts(parts);\n"),
    ("R524PrefixStabilityTests.cs",
     "    private static string Source(string relative) => File.ReadAllText(Path.Combine(RepoRoot(), relative));\n",
     "    private static string Source(string relative) => SourcePin.Text(relative.Replace(Path.DirectorySeparatorChar, '/'));\n"),
    ("R497FingerprintAndSynonymTests.cs",
     "    private static string ReadSrc(params string[] parts) =>\n        File.ReadAllText(Path.Combine(new[] { RepoRoot() }.Concat(parts).ToArray()));\n",
     "    private static string ReadSrc(params string[] parts) => SourcePin.TextParts(parts);\n"),
    ("EmptyBodyDiagnosisTests.cs",
     "    private static string Flat(params string[] relative)\n        => string.Join(' ', File.ReadAllText(Path.Combine(new[] { RepoRoot() }.Concat(relative).ToArray()))\n",
     "    private static string Flat(params string[] relative)\n        => string.Join(' ', SourcePin.TextParts(relative)\n"),
]

DECISION_PIN_OLD = '        Assert.Equal(new[] { "ModelQueueRouter.cs" }, names);   // 只在调用方 (不是端口实现里) 钉死\n'
DECISION_PIN_NEW = ('        // R527: 单一类型允许分片 (ModelQueueRouter.<Suffix>.cs) ⇒ 判「全部落在该类型的分片上」, 禁别的类型\n'
                    '        Assert.All(names, n => Assert.True(\n'
                    '            n == "ModelQueueRouter.cs" || n.StartsWith("ModelQueueRouter.", StringComparison.Ordinal),\n'
                    '            $"缓存钉死泄漏到非决策路径文件: {n}"));\n'
                    '        Assert.NotEmpty(names);\n')


def rewrite_reads(text):
    """File.ReadAllText(Path.Combine(<root>, "a", "b", "X.cs" ) [, Encoding.UTF8] ) → SourcePin.TextParts("a","b","X.cs")"""
    out, i, n = [], 0, 0
    while True:
        k = text.find("File.ReadAllText(Path.Combine(", i)
        if k < 0:
            out.append(text[i:])
            break
        start_args = k + len("File.ReadAllText(")
        depth, j = 0, start_args
        while j < len(text):
            if text[j] == '(':
                depth += 1
            elif text[j] == ')':
                depth -= 1
                if depth == 0:
                    break
            elif text[j] == '"':
                j += 1
                while j < len(text) and text[j] != '"':
                    j += 2 if text[j] == '\\' else 1
            j += 1
        call = text[start_args:j + 1]
        inner = call[len("Path.Combine("):-1]
        # 顶层逗号切分
        parts, cur, d = [], "", 0
        for ch in inner:
            if ch in "([{":
                d += 1
            elif ch in ")]}":
                d -= 1
            if ch == "," and d == 0:
                parts.append(cur)
                cur = ""
            else:
                cur += ch
        parts.append(cur)
        lits = [p.strip() for p in parts if p.strip().startswith('"') and p.strip().endswith('"')]
        if not lits or not lits[-1].endswith('.cs"'):
            out.append(text[i:j + 1])
            i = j + 1
            continue
        out.append(text[i:k])
        out.append("SourcePin.TextParts(" + ", ".join(lits) + ")")
        # 吃掉 File.ReadAllText( ... ) 的收尾括号 (含 `, Encoding.UTF8` 形态)
        d2, m = 1, j + 1
        while m < len(text) and d2 > 0:
            if text[m] == '(':
                d2 += 1
            elif text[m] == ')':
                d2 -= 1
            m += 1
        i = m
        n += 1
    return "".join(out), n


def main():
    apply = "--apply" in sys.argv
    changed, total_reads = [], 0
    for name in sorted(os.listdir(TESTS)):
        if not name.endswith(".cs") or name == "SourcePin.cs":
            continue
        p = os.path.join(TESTS, name)
        t0 = open(p, encoding="utf-8").read()
        t = t0
        t, n = rewrite_reads(t)
        total_reads += n
        for fn, old, new in HELPER_EDITS:
            if fn == name and old in t:
                t = t.replace(old, new)
        if name == "DecisionCachePinTests.cs" and DECISION_PIN_OLD in t:
            t = t.replace(DECISION_PIN_OLD, DECISION_PIN_NEW)
        if t != t0:
            changed.append((name, n))
            if apply:
                open(p, "w", encoding="utf-8", newline="").write(t)
    sp = os.path.join(TESTS, "SourcePin.cs")
    if apply and not os.path.exists(sp):
        open(sp, "w", encoding="utf-8", newline="").write(SOURCE_PIN)
    print(f"mode={'apply' if apply else 'dry'}  改写内联读={total_reads}  改动文件={len(changed)}")
    for nm, n in changed:
        print(f"  {nm}: 读法改写 {n}")
    if apply:
        leftover = subprocess.run(["grep", "-rn", "-e", "File.ReadAllText(Path.Combine(", "src/agent.tests/"], cwd=ROOT, capture_output=True, text=True).stdout
        print("残留 File.ReadAllText(Path.Combine(")
        print(leftover or "  (无)")


if __name__ == "__main__":
    main()
