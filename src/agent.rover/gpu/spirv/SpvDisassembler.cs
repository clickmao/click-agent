using System.Text;

namespace agent.rover.gpu.spirv;

/// <summary>
/// 独立 SPIR-V 反汇编转储 (诊断用, 不参与执行路径)。
/// 目的: 当"结构合法但数值错"时, 把模块里**真实写下的字**逐条解码出来,
/// 以便与规范逐字对账 —— 而不是凭对汇编器源码的推测下结论。
/// 与 <see cref="Spv"/> 是两套独立实现: 这里只按"字面含义"解码, 不共享任何生成侧假设。
/// </summary>
public static class SpvDisassembler
{
    private static string Name(uint op) => op switch
    {
        Spv.OpCapability => "OpCapability",
        Spv.OpMemoryModel => "OpMemoryModel",
        Spv.OpEntryPoint => "OpEntryPoint",
        Spv.OpExecutionMode => "OpExecutionMode",
        Spv.OpTypeVoid => "OpTypeVoid",
        Spv.OpTypeBool => "OpTypeBool",
        Spv.OpTypeInt => "OpTypeInt",
        Spv.OpTypeFloat => "OpTypeFloat",
        Spv.OpTypeVector => "OpTypeVector",
        Spv.OpTypeRuntimeArray => "OpTypeRuntimeArray",
        Spv.OpTypeStruct => "OpTypeStruct",
        Spv.OpTypePointer => "OpTypePointer",
        Spv.OpTypeFunction => "OpTypeFunction",
        Spv.OpConstant => "OpConstant",
        Spv.OpExtInstImport => "OpExtInstImport",
        Spv.OpExtInst => "OpExtInst",
        Spv.OpFunction => "OpFunction",
        Spv.OpFunctionEnd => "OpFunctionEnd",
        Spv.OpVariable => "OpVariable",
        Spv.OpLoad => "OpLoad",
        Spv.OpStore => "OpStore",
        Spv.OpAccessChain => "OpAccessChain",
        Spv.OpArrayLength => "OpArrayLength",
        Spv.OpDecorate => "OpDecorate",
        Spv.OpMemberDecorate => "OpMemberDecorate",
        Spv.OpCompositeExtract => "OpCompositeExtract",
        Spv.OpLabel => "OpLabel",
        Spv.OpReturn => "OpReturn",
        Spv.OpConvertUToF => "OpConvertUToF",
        Spv.OpFNegate => "OpFNegate",
        Spv.OpIAdd => "OpIAdd",
        Spv.OpFAdd => "OpFAdd",
        Spv.OpISub => "OpISub",
        Spv.OpFSub => "OpFSub",
        Spv.OpIMul => "OpIMul",
        Spv.OpFMul => "OpFMul",
        Spv.OpFDiv => "OpFDiv",
        Spv.OpBitcast => "OpBitcast",
        Spv.OpUGreaterThanEqual => "OpUGreaterThanEqual",
        Spv.OpBranch => "OpBranch",
        Spv.OpBranchConditional => "OpBranchConditional",
        Spv.OpSelectionMerge => "OpSelectionMerge",
        Spv.OpSelect => "OpSelect",
        _ => $"Op#{op}",
    };

    /// <summary>把整个模块解码为逐行文本 (含头 5 字与每条指令的字数/操作数)。</summary>
    public static string Decode(uint[] w)
    {
        var sb = new StringBuilder();
        if (w.Length < 5) { sb.AppendLine("spv{too_short}"); return sb.ToString(); }
        sb.AppendLine($"spv{{magic=0x{w[0]:X8} version=0x{w[1]:X8} generator=0x{w[2]:X8} bound={w[3]} schema={w[4]} words={w.Length}}}");
        int p = 5, n = 0;
        while (p < w.Length)
        {
            int wc = (int)(w[p] >> 16);
            uint op = w[p] & 0xFFFFu;
            if (wc == 0) { sb.AppendLine($"  [{p}] MALFORMED word_count=0"); break; }
            if (p + wc > w.Length) { sb.AppendLine($"  [{p}] TRUNCATED {Name(op)} wc={wc} remaining={w.Length - p}"); break; }
            var args = new StringBuilder();
            for (int i = 1; i < wc; i++) { if (i > 1) args.Append(", "); args.Append(w[p + i]); }
            sb.AppendLine($"  [{p,5}] #{n++,4} {Name(op),-22} wc={wc,2} args=[{args}]");
            p += wc;
        }
        return sb.ToString();
    }
}
