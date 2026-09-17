// R526 重构器具: 基于 Roslyn 语法树的「顶层类型单一化 (Move Type to own file)」.
// 仅开发期使用; 不属于 agent.sln, 不参与 AOT 产物.
using System.Text;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

namespace RefTool;

internal static class Program
{
    private static int Main(string[] args)
    {
        string mode = args.Length > 0 ? args[0] : "report";
        if (mode is "-h" or "--help")
        {
            Console.WriteLine("用法: reftool report|extract [--apply] [--manifest PATH] [路径...]");
            return 0;
        }

        bool apply = args.Contains("--apply");
        string? manifestPath = null;
        int mi = Array.IndexOf(args, "--manifest");
        if (mi >= 0 && mi + 1 < args.Length)
        {
            manifestPath = args[mi + 1];
        }
        if (mode == "members")
        {
            return Members(args);
        }
        if (mode == "split")
        {
            return Split(args, apply, manifestPath);
        }

        var roots = args.Skip(1)
            .Where(a => !a.StartsWith("--") && a != manifestPath)
            .ToList();
        if (roots.Count == 0)
        {
            roots.Add("src");
        }

        var files = Collect(roots);
        var manifest = new List<string>();
        int movedTotal = 0, touched = 0, deleted = 0, skipped = 0;
        var fileScopedSkip = new List<string>();

        foreach (string f in files.OrderBy(x => x, StringComparer.Ordinal))
        {
            string text = File.ReadAllText(f, Encoding.UTF8);
            var root = CSharpSyntaxTree.ParseText(text,
                new CSharpParseOptions(LanguageVersion.Preview)).GetRoot() as CompilationUnitSyntax;
            if (root is null)
            {
                continue;
            }

            var (types, nsForm, nsText) = TopTypes(root);
            if (types.Count < 2)
            {
                continue;
            }

            string stem = Path.GetFileNameWithoutExtension(f);
            var byStem = types.FirstOrDefault(t => Name(t) == stem);
            var primary = byStem ?? types.OrderByDescending(t => t.FullSpan.Length).First();
            bool deletable = byStem is null;
            var others = types.Where(t => !ReferenceEquals(t, primary)).ToList();

            var movable = new List<BaseTypeDeclarationSyntax>();
            foreach (var t in others)
            {
                if (t.Modifiers.Any(m => m.IsKind(SyntaxKind.FileKeyword)))
                {
                    fileScopedSkip.Add($"{f}:{Name(t)}");
                    continue;
                }
                movable.Add(t);
            }
            if (movable.Count == 0)
            {
                continue;
            }

            string dir = Path.GetDirectoryName(f)!;
            var newFiles = new List<string>();
            var plan = new List<(BaseTypeDeclarationSyntax Type, string Dst, string Text)>();
            foreach (var t in movable)
            {
                string dst = Path.Combine(dir, Name(t) + ".cs");
                if (File.Exists(dst) || File.Exists(dst.Replace(".cs", "") + ".cs"))
                {
                    // 同名文件已存在 => 保留原处 (不写, 不删)
                    skipped++;
                    Console.WriteLine($"  [跳过] {dst} 已存在");
                    continue;
                }
                string body = t.ToFullString().TrimEnd('\r', '\n');
                string outText = BuildFile(root.Usings, nsForm, nsText, body);
                plan.Add((t, dst, outText));
            }
            if (plan.Count == 0)
            {
                continue;
            }

            // 重写源文件: 删除已外移类型的全文
            string residual = text;
            foreach (var (t, _, _) in plan.OrderByDescending(p => p.Type.FullSpan.Start))
            {
                residual = residual.Remove(t.FullSpan.Start, t.FullSpan.Length);
            }

            bool residualMeaningful = HasCode(residual);
            Console.WriteLine($"  {f}: 外移 {string.Join(", ", plan.Select(p => Name(p.Type)))}"
                + (deletable && !residualMeaningful ? "  [并删除原文件]" : residualMeaningful ? "  [保留原文件]" : ""));
            if (apply)
            {
                foreach (var (_, dst, outText) in plan)
                {
                    File.WriteAllText(dst, outText, new UTF8Encoding(false));
                    newFiles.Add(dst);
                }
                if (!residualMeaningful)
                {
                    File.Delete(f);
                    deleted++;
                }
                else
                {
                    File.WriteAllText(f, residual, new UTF8Encoding(false));
                }
                touched++;
            }

            movedTotal += plan.Count;
            manifest.Add("{\"src\":" + Json(f) + ",\"new\":["
                + string.Join(",", plan.Select(p => Json(p.Dst))) + "],\"deleted\":"
                + (residualMeaningful ? "false" : "true") + "}");
        }

        if (fileScopedSkip.Count > 0)
        {
            Console.WriteLine($"[file 作用域跳过] {fileScopedSkip.Count}: {string.Join(", ", fileScopedSkip.Take(10))}");
        }
        if (skipped > 0)
        {
            Console.WriteLine($"[同名文件跳过] {skipped} 个类型");
        }
        if (manifestPath is not null && apply)
        {
            File.WriteAllText(manifestPath, "[" + string.Join(",", manifest) + "]", new UTF8Encoding(false));
            Console.WriteLine($"[清单] {manifestPath} ({manifest.Count} 个源文件)");
        }
        Console.WriteLine($"[{(apply ? "已写入" : "演练")}] 外移 {movedTotal} 个类型, 改写 {touched} 个源文件, 删除 {deleted} 个");
        return 0;
    }

    private static string Json(string s) => "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";

    private static bool HasCode(string text)
    {
        foreach (string raw in text.Split('\n'))
        {
            string l = raw.Trim();
            if (l.Length == 0 || l.StartsWith("//") || l.StartsWith("using ") || l.StartsWith("global using ")
                || l.StartsWith("namespace ") || l == "}" || l == "{" || l.StartsWith("#") || l.StartsWith("["))
            {
                continue;
            }
            return true;
        }
        return false;
    }

    private static string BuildFile(SyntaxList<UsingDirectiveSyntax> usings, string nsForm, string nsText, string body)
    {
        var sb = new StringBuilder();
        foreach (var u in usings)
        {
            sb.Append(u.ToFullString().TrimEnd('\r', '\n')).Append('\n');
        }
        if (usings.Count > 0)
        {
            sb.Append('\n');
        }
        if (nsForm == "file")
        {
            sb.Append(nsText).Append("\n\n").Append(body).Append('\n');
        }
        else if (nsForm == "block")
        {
            sb.Append(nsText).Append("\n{\n").Append(body).Append("\n}\n");
        }
        else
        {
            sb.Append(body).Append('\n');
        }
        return sb.ToString();
    }

    private static (List<BaseTypeDeclarationSyntax> Types, string NsForm, string NsText) TopTypes(CompilationUnitSyntax root)
    {
        var ns = root.Members.OfType<BaseNamespaceDeclarationSyntax>().FirstOrDefault();
        var list = new List<BaseTypeDeclarationSyntax>();
        if (ns is null)
        {
            list.AddRange(root.Members.OfType<BaseTypeDeclarationSyntax>());
            return (list, "none", "");
        }
        list.AddRange(ns.Members.OfType<BaseTypeDeclarationSyntax>());
        string text = (ns.Name?.ToString() ?? "").Trim();
        if (ns is FileScopedNamespaceDeclarationSyntax)
        {
            return (list, "file", $"namespace {text};");
        }
        return (list, "block", $"namespace {text}");
    }

    private static string Name(BaseTypeDeclarationSyntax t) => t switch
    {
        TypeDeclarationSyntax d => d.Identifier.Text,
        EnumDeclarationSyntax e => e.Identifier.Text,
        _ => t.ToString()
    };

    private static List<string> Collect(List<string> roots)
    {
        var outp = new List<string>();
        foreach (string r in roots)
        {
            if (File.Exists(r))
            {
                if (r.EndsWith(".cs", StringComparison.Ordinal))
                {
                    outp.Add(r);
                }
                continue;
            }
            if (!Directory.Exists(r))
            {
                continue;
            }
            foreach (string f in Directory.EnumerateFiles(r, "*.cs", SearchOption.AllDirectories))
            {
                string p = f.Replace('\\', '/');
                if (p.Contains("/obj/") || p.Contains("/bin/"))
                {
                    continue;
                }
                outp.Add(f);
            }
        }
        return outp;
    }

    private static List<BaseTypeDeclarationSyntax> AllTypes(CompilationUnitSyntax root)
    {
        var ns = root.Members.OfType<BaseNamespaceDeclarationSyntax>().FirstOrDefault();
        return ns is null
            ? root.Members.OfType<BaseTypeDeclarationSyntax>().ToList()
            : ns.Members.OfType<BaseTypeDeclarationSyntax>().ToList();
    }

    private static int LineOf(string text, int offset)
    {
        int n = 1;
        for (int i = 0; i < offset && i < text.Length; i++)
        {
            if (text[i] == '\n') n++;
        }
        return n;
    }

    private static string FlatFirstLine(MemberDeclarationSyntax m)
    {
        string head = m.ToFullString().TrimStart().Split('\n')[0].Trim();
        return head.Length > 96 ? head.Substring(0, 96) : head;
    }

    private static int Members(string[] args)
    {
        var rest = args.Skip(1).Where(a => !a.StartsWith("--")).ToList();
        if (rest.Count < 2)
        {
            Console.WriteLine("用法: reftool members <file> <Type>");
            return 2;
        }
        string text = File.ReadAllText(rest[0], Encoding.UTF8);
        var root = (CompilationUnitSyntax)CSharpSyntaxTree.ParseText(text,
            new CSharpParseOptions(LanguageVersion.Preview)).GetRoot();
        var type = AllTypes(root).FirstOrDefault(t => Name(t) == rest[1]);
        if (type is null)
        {
            Console.WriteLine("未找到类型: " + rest[1]);
            return 2;
        }
        Console.WriteLine($"// {rest[0]} :: {rest[1]}  行 {LineOf(text, type.SpanStart)}-{LineOf(text, type.Span.End)}");
        if (type is not TypeDeclarationSyntax tds)
        {
            Console.WriteLine("(非 class/record/struct, 无成员列表)");
            return 0;
        }
        foreach (var m in tds.Members)
        {
            Console.WriteLine($"{LineOf(text, m.FullSpan.Start),5}-{LineOf(text, m.FullSpan.End),5} {m.Kind(),-20} {FlatFirstLine(m)}");
        }
        return 0;
    }

    private static string MemberName(MemberDeclarationSyntax m) => m switch
    {
        MethodDeclarationSyntax x => x.Identifier.Text,
        PropertyDeclarationSyntax x => x.Identifier.Text,
        ConstructorDeclarationSyntax x => x.ParameterList.Parameters.Count == 0 ? ".ctor0" : ".ctor" + x.ParameterList.Parameters.Count,
        FieldDeclarationSyntax x => x.Declaration.Variables.FirstOrDefault()?.Identifier.Text ?? "",
        EventFieldDeclarationSyntax x => x.Declaration.Variables.FirstOrDefault()?.Identifier.Text ?? "",
        BaseTypeDeclarationSyntax x => Name(x),
        _ => ""
    };

    private static int FirstBrace(string text, int from)
    {
        for (int i = from; i < text.Length; i++)
        {
            if (text[i] == '{') return i;
        }
        return text.Length;
    }

    private static int Split(string[] args, bool apply, string? manifestPath)
    {
        var pos = args.Skip(1).Where(a => !a.StartsWith("--") && a != manifestPath).ToList();
        if (pos.Count < 3)
        {
            Console.WriteLine("用法: reftool split <file> <Type> 后缀=成员名 [更多...] [--apply] [--manifest P]");
            return 2;
        }
        string file = pos[0], typeName = pos[1];
        var specs = new List<(string Suffix, string Member)>();
        foreach (string s in pos.Skip(2))
        {
            int eq = s.IndexOf('=');
            if (eq <= 0)
            {
                Console.WriteLine("非法分段说明: " + s);
                return 2;
            }
            specs.Add((s.Substring(0, eq), s.Substring(eq + 1)));
        }

        string text = File.ReadAllText(file, Encoding.UTF8);
        var root = (CompilationUnitSyntax)CSharpSyntaxTree.ParseText(text,
            new CSharpParseOptions(LanguageVersion.Preview)).GetRoot();
        var (types, nsForm, nsText) = TopTypes(root);
        var type = types.FirstOrDefault(t => Name(t) == typeName);
        if (type is not TypeDeclarationSyntax tds)
        {
            Console.WriteLine("未找到 class/record/struct 类型: " + typeName);
            return 2;
        }

        // 分段: 字段/事件字段/嵌套类型强制留在主文件 (保静态初始值顺序与声明序)
        int seg = 0;
        var segs = new List<List<MemberDeclarationSyntax>> { new() };
        var names = new List<string> { "" };
        foreach (var m in tds.Members)
        {
            string mname = MemberName(m);
            int idx = specs.FindIndex(s => s.Member == mname);
            bool pinned = m is FieldDeclarationSyntax or EventFieldDeclarationSyntax or BaseTypeDeclarationSyntax;
            if (idx >= 0 && !pinned)
            {
                seg = segs.Count;
                segs.Add(new List<MemberDeclarationSyntax>());
                names.Add(specs[idx].Suffix);
            }
            segs[seg].Add(m);
        }
        if (segs.Count < 2)
        {
            Console.WriteLine("未匹配到任何分段起点 (成员名需精确相等)");
            return 2;
        }
        Console.WriteLine($"分段成员数: 主文件={segs[0].Count} " +
            string.Join(" ", segs.Skip(1).Select((x, i) => $"{names[i + 1]}={x.Count}")));
        if (!apply)
        {
            return 0;
        }

        var movedMembers = segs.Skip(1).SelectMany(x => x).ToList();
        foreach (var m in movedMembers)
        {
            int ob = m.DescendantTokens().Count(tk => tk.IsKind(SyntaxKind.OpenBraceToken));
            int cb = m.DescendantTokens().Count(tk => tk.IsKind(SyntaxKind.CloseBraceToken));
            if (ob != cb)
            {
                Console.WriteLine($"!! 成员花括号不平衡 ({MemberName(m)}: {ob}/{cb}) — 拒绝写入");
                return 3;
            }
        }

        string dir = Path.GetDirectoryName(file)!;
        string stem = Path.GetFileNameWithoutExtension(file);
        string declText = text.Substring(type.SpanStart, FirstBrace(text, type.SpanStart) - type.SpanStart).TrimEnd();
        if (!System.Text.RegularExpressions.Regex.IsMatch(declText, @"\bpartial\b"))
        {
            declText = System.Text.RegularExpressions.Regex.Replace(declText, @"\b(class|record|struct)\b", "partial $1", System.Text.RegularExpressions.RegexOptions.None, TimeSpan.FromSeconds(2));
        }

        string primary = text;
        foreach (var m in movedMembers.OrderByDescending(m => m.FullSpan.Start))
        {
            primary = primary.Remove(m.FullSpan.Start, m.FullSpan.End - m.FullSpan.Start);
        }
        primary = System.Text.RegularExpressions.Regex.Replace(primary, @"\n{3,}", "\n\n");
        // 主文件自身声明也要 partial 化 (声明在所有被移成员之前 ⇒ 偏移未变)
        int braceStart = FirstBrace(text, type.SpanStart);
        int braceLineStart = text.LastIndexOf('\n', braceStart) + 1;
        string braceIndent = text.Substring(braceLineStart, braceStart - braceLineStart);
        primary = primary.Substring(0, type.SpanStart) + declText + "\n" + braceIndent + primary.Substring(braceStart);

        var written = new List<string>();
        for (int k = 1; k < segs.Count; k++)
        {
            string body = string.Join("\n", segs[k].Select(m => m.ToFullString().TrimEnd('\r', '\n')));
            string outText = BuildFile(root.Usings, nsForm, nsText, declText + "\n{\n" + body + "\n}");
            string dst = Path.Combine(dir, stem + "." + names[k] + ".cs");
            File.WriteAllText(dst, outText, new UTF8Encoding(false));
            written.Add(dst);
            Console.WriteLine("  写出 " + dst);
        }
        File.WriteAllText(file, primary, new UTF8Encoding(false));
        Console.WriteLine("  主文件 " + file);
        if (manifestPath is not null)
        {
            File.WriteAllText(manifestPath, string.Join("\n", written), new UTF8Encoding(false));
        }
        return 0;
    }
}
