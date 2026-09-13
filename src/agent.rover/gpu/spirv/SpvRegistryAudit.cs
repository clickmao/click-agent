using System.Globalization;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace agent.rover.gpu.spirv;

/// <summary>
/// 手写常量表的独立 oracle: 以 Khronos 权威 registry (core grammar + GLSL.std.450 grammar) 逐条核对
/// <c>Spv.cs</c> / <c>SpirvValidator.cs</c> 中的 opcode / 枚举 / 扩展指令号。
///
/// 必要性 (R389-vulkan 真机实证): 汇编器 / 结构校验器 / 反汇编器**共用同一张手写表** ⇒ 三者互相印证同一个错误。
/// 实证案例: <c>OpUGreaterThanEqual</c> 抄成 179 (规范 174 = OpSLessThanEqual)、<c>OpConvertUToF</c> 抄成 111
/// (规范 112 = OpConvertSToF) —— 结构校验报 valid、反汇编"逐字正确", 而设备执行的是另一条指令,
/// 守卫失效导致动态索引写全部越界不可见。只有独立 registry 能发现这一类错误。
///
/// 零反射 (JsonDocument + 正则), AOT 可用, 不参与内核执行路径。
/// </summary>
public static class SpvRegistryAudit
{
    /// <summary>一条与权威 registry 不符的常量。</summary>
    public sealed record Mismatch(string File, int Line, string Constant, string Registry, uint Ours, uint Expected);

    /// <summary>审计结果: 已核对条数 / 不符项 / 无法核对项 (无法核对必须为空, 否则"没测到"会被当成"测过")。</summary>
    public sealed record Report(int Checked, IReadOnlyList<Mismatch> Mismatches, IReadOnlyList<string> Unverified)
    {
        public bool Ok => Mismatches.Count == 0 && Unverified.Count == 0;
    }

    /// <summary>自写名 → 权威枚举 (kind, enumerant)。名字与 SPIR-V 枚举不同名者必须在此显式绑定。</summary>
    static readonly Dictionary<string, (string Kind, string Name)> Aliases = new(StringComparer.Ordinal)
    {
        ["CapShader"] = ("Capability", "Shader"),
        ["MemLogical"] = ("AddressingModel", "Logical"),
        ["MemGLSL450"] = ("MemoryModel", "GLSL450"),
        ["ExecGLCompute"] = ("ExecutionModel", "GLCompute"),
        ["ScInput"] = ("StorageClass", "Input"),
        ["ScWorkgroup"] = ("StorageClass", "Workgroup"),
        ["ScStorageBuffer"] = ("StorageClass", "StorageBuffer"),
        // R393: BGE 矩阵乘内核的函数局部变量 (累加器/循环计数器) 用 Function 存储类
        ["ScFunction"] = ("StorageClass", "Function"),
        ["DecBlock"] = ("Decoration", "Block"),
        ["DecArrayStride"] = ("Decoration", "ArrayStride"),
        ["DecDescriptorSet"] = ("Decoration", "DescriptorSet"),
        ["DecBinding"] = ("Decoration", "Binding"),
        ["DecBuiltIn"] = ("Decoration", "BuiltIn"),
        ["DecOffset"] = ("Decoration", "Offset"),
        ["BuiltInGlobalInvocationId"] = ("BuiltIn", "GlobalInvocationId"),
        ["ExModeLocalSize"] = ("ExecutionMode", "LocalSize"),
    };

    /// <summary>不属于 registry 的常量 (模块头字段等), 显式豁免 —— 豁免必须具名, 不给"悄悄放过"留口子。</summary>
    static readonly HashSet<string> NotInRegistry = new(StringComparer.Ordinal) { "Magic" };

    static readonly Regex Pair = new(@"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(0x[0-9A-Fa-f]+|\d+)",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    /// <summary>以审计报告形式核对若干源码文件。</summary>
    public static Report Run(string coreGrammarJson, string glslGrammarJson, params (string File, string Source)[] sources)
    {
        var opcodes = new Dictionary<string, uint>(StringComparer.Ordinal);
        var kinds = new Dictionary<string, Dictionary<string, uint>>(StringComparer.Ordinal);

        using (var doc = JsonDocument.Parse(coreGrammarJson))
        {
            foreach (var ins in doc.RootElement.GetProperty("instructions").EnumerateArray())
                opcodes[ins.GetProperty("opname").GetString()!] = ins.GetProperty("opcode").GetUInt32();
            foreach (var k in doc.RootElement.GetProperty("operand_kinds").EnumerateArray())
            {
                if (!k.TryGetProperty("category", out var cat) || cat.GetString() != "ValueEnum") continue;
                var m = new Dictionary<string, uint>(StringComparer.Ordinal);
                foreach (var e in k.GetProperty("enumerants").EnumerateArray())
                    m[e.GetProperty("enumerant").GetString()!] = e.GetProperty("value").GetUInt32();
                kinds[k.GetProperty("kind").GetString()!] = m;
            }
        }

        var glsl = new Dictionary<string, uint>(StringComparer.Ordinal);
        using (var doc = JsonDocument.Parse(glslGrammarJson))
            foreach (var ins in doc.RootElement.GetProperty("instructions").EnumerateArray())
                glsl[ins.GetProperty("opname").GetString()!] = ins.GetProperty("opcode").GetUInt32();

        int checkedCount = 0;
        var bad = new List<Mismatch>();
        var unverified = new List<string>();

        foreach (var (file, source) in sources)
            foreach (var (name, value, line) in Extract(source))
            {
                if (NotInRegistry.Contains(name)) continue;

                if (name.StartsWith("Op", StringComparison.Ordinal))
                {
                    if (opcodes.TryGetValue(name, out var want))
                    {
                        checkedCount++;
                        if (want != value) bad.Add(new(file, line, name, name, value, want));
                    }
                    else unverified.Add($"{file}:{line} {name} (core opcode 表无此名)");
                    continue;
                }

                if (name.StartsWith("Glsl", StringComparison.Ordinal))
                {
                    var n = name[4..];
                    if (glsl.TryGetValue(n, out var want))
                    {
                        checkedCount++;
                        if (want != value) bad.Add(new(file, line, name, $"GLSL.std.450/{n}", value, want));
                    }
                    else unverified.Add($"{file}:{line} {name} (GLSL.std.450 表无此名)");
                    continue;
                }

                if (Aliases.TryGetValue(name, out var alias))
                {
                    if (kinds.TryGetValue(alias.Kind, out var km) && km.TryGetValue(alias.Name, out var want))
                    {
                        checkedCount++;
                        if (want != value) bad.Add(new(file, line, name, $"{alias.Kind}/{alias.Name}", value, want));
                    }
                    else unverified.Add($"{file}:{line} {name} (枚举 {alias.Kind}/{alias.Name} 不存在)");
                    continue;
                }

                var hits = kinds.Where(kv => kv.Value.ContainsKey(name)).Select(kv => (kv.Key, kv.Value[name])).ToList();
                if (hits.Count == 1)
                {
                    checkedCount++;
                    if (hits[0].Item2 != value) bad.Add(new(file, line, name, $"{hits[0].Item1}/{name}", value, hits[0].Item2));
                }
                else unverified.Add($"{file}:{line} {name} (命中 {hits.Count} 个枚举 kind)");
            }

        return new Report(checkedCount, bad, unverified);
    }

    /// <summary>
    /// 只扫常量声明块 (<c>const uint ... ;</c>)。避开局部变量 (如 <c>for (int i = 0; ...)</c>) 造成的假命中 ——
    /// 审计器自身的判别力同样要被约束, 否则噪声会淹没真信号。
    /// </summary>
    public static IEnumerable<(string Name, uint Value, int Line)> Extract(string source)
    {
        var lines = source.Replace("\r\n", "\n").Split('\n');
        bool inBlock = false;
        for (int i = 0; i < lines.Length; i++)
        {
            var line = lines[i];
            var t = line.TrimStart();
            if (!inBlock)
            {
                if (t.StartsWith("//", StringComparison.Ordinal) || !t.Contains("const uint", StringComparison.Ordinal)) continue;
                inBlock = true;
            }
            else if (t.StartsWith("//", StringComparison.Ordinal) || t.Length == 0) continue;

            foreach (Match m in Pair.Matches(line))
            {
                var raw = m.Groups[2].Value;
                uint v = raw.StartsWith("0x", StringComparison.OrdinalIgnoreCase)
                    ? Convert.ToUInt32(raw[2..], 16)
                    : uint.Parse(raw, CultureInfo.InvariantCulture);
                yield return (m.Groups[1].Value, v, i + 1);
            }

            if (line.Contains(';')) inBlock = false;
        }
    }
}
