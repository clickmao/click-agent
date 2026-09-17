using System.Collections.Generic;

namespace agent.rover.gpu.spirv;

/// <summary>
/// 极简 SPIR-V 结构校验器 (零依赖 / 零反射, 可随 agent 测试工程同源编译)。
/// 存在的理由: 把内核交给驱动前, 必须先用**独立于汇编器**的不变量检查抓结构性错误
/// (魔数/版本/ID 上界/指令长度/入口点/执行模式/描述符计数/引用定义性)。
/// 与汇编器同源的自证只会互证同一错误 —— 故这里按 SPIR-V 字面规范独立重写, 并配负向控制用例。
/// </summary>
public static class SpirvValidator
{
    public const uint Magic = 0x07230203;

    const uint OpExtInstImport = 11, OpExtInst = 12, OpMemoryModel = 14, OpEntryPoint = 15,
        OpExecutionMode = 16, OpCapability = 17, OpTypeVoid = 19, OpTypeBool = 20, OpTypeInt = 21,
        OpTypeFloat = 22, OpTypeVector = 23, OpTypeRuntimeArray = 29, OpTypeStruct = 30,
        OpTypePointer = 32, OpTypeFunction = 33, OpConstant = 43, OpFunction = 54,
        OpFunctionEnd = 56, OpVariable = 59, OpLoad = 61, OpAccessChain = 65, OpArrayLength = 68,
        OpDecorate = 71, OpCompositeExtract = 81, OpBitcast = 124, OpFNegate = 127,
        OpIAdd = 128, OpFAdd = 129, OpISub = 130, OpFSub = 131, OpIMul = 132, OpFMul = 133,
        OpFDiv = 136, OpSelect = 169, OpUGreaterThanEqual = 174, OpLabel = 248;

    const uint CapShader = 1, MemLogical = 0, ExecGLCompute = 5, DecBinding = 33, ExModeLocalSize = 17;

    /// <summary>opcode → 结果 id 在其操作数中的下标 (仅列本汇编器会产出的指令; 未列出的不检查结果 id)。</summary>
    static readonly Dictionary<uint, int> ResultIdAt = new()
    {
        [OpExtInstImport] = 0, [OpTypeVoid] = 0, [OpTypeBool] = 0, [OpTypeInt] = 0, [OpTypeFloat] = 0,
        [OpTypeVector] = 0, [OpTypeRuntimeArray] = 0, [OpTypeStruct] = 0, [OpTypePointer] = 0,
        [OpTypeFunction] = 0, [OpLabel] = 0,
        [OpExtInst] = 1, [OpConstant] = 1, [OpVariable] = 1, [OpLoad] = 1, [OpAccessChain] = 1,
        [OpArrayLength] = 1, [OpCompositeExtract] = 1, [OpBitcast] = 1, [OpFNegate] = 1,
        [OpIAdd] = 1, [OpFAdd] = 1, [OpISub] = 1, [OpFSub] = 1, [OpIMul] = 1, [OpFMul] = 1,
        [OpFDiv] = 1, [OpSelect] = 1, [OpUGreaterThanEqual] = 1, [OpFunction] = 1,
    };

    /// <summary>
    /// 校验一个计算内核。要求: 唯一 GLCompute 入口 / LocalSize == <paramref name="expectedLocalSize"/> /
    /// 描述符绑定数 == <paramref name="expectedBuffers"/> / 所有结果 id 与引用 id 均 &lt; bound 且已定义。
    /// </summary>
    public static IReadOnlyList<SpirvIssue> Validate(
        IReadOnlyList<uint> words, int expectedLocalSize, int expectedBuffers)
    {
        var issues = new List<SpirvIssue>();
        if (words.Count < 5) { issues.Add(new("HEADER_TRUNCATED", 0, $"words={words.Count} need>=5")); return issues; }
        if (words[0] != Magic) issues.Add(new("BAD_MAGIC", 0, $"0x{words[0]:X8}"));

        uint version = words[1];
        if ((version >> 16) != 1) issues.Add(new("BAD_VERSION", 1, $"major={version >> 16}"));

        // SPIR-V 头: word0=magic, word1=version, word2=generator, word3=bound, word4=reserved(schema=0)
        uint bound = words[3];
        if (bound == 0) issues.Add(new("BAD_BOUND", 3, "bound=0"));

        var defined = new HashSet<uint>();
        var references = new List<(uint Id, int Word, string What)>();
        uint maxId = 0;
        int functionCount = 0, endCount = 0, entryCount = 0, localSizeSeen = 0, bindingCount = 0;
        bool shaderCapability = false, memoryModel = false, entryIsCompute = false;
        uint entryFn = 0, localSizeX = 0;

        int i = 5;
        while (i < words.Count)
        {
            uint head = words[i];
            uint wc = head >> 16, op = head & 0xFFFF;
            if (wc == 0) { issues.Add(new("INSTRUCTION_ZERO_LENGTH", i, $"op={op}")); break; }
            if (i + (int)wc > words.Count)
            {
                issues.Add(new("INSTRUCTION_TRUNCATED", i, $"op={op} wc={wc} remaining={words.Count - i}"));
                break;
            }

            if (ResultIdAt.TryGetValue(op, out int resultAt))
            {
                uint resId = words[i + 1 + resultAt];
                if (resId == 0) issues.Add(new("RESULT_ID_ZERO", i, $"op={op}"));
                else { defined.Add(resId); if (resId > maxId) maxId = resId; }
            }

            switch (op)
            {
                case OpCapability:
                    if (words[i + 1] == CapShader) shaderCapability = true;
                    break;
                case OpMemoryModel:
                    if (words[i + 1] == MemLogical) memoryModel = true;
                    break;
                case OpEntryPoint:
                {
                    entryCount++;
                    if (words[i + 1] == ExecGLCompute) entryIsCompute = true;
                    entryFn = words[i + 2];
                    references.Add((entryFn, i, "entry_point_function"));
                    // 名字字面量 (以 0 结尾, 按 4 字节补齐) 之后是接口变量 id 列表
                    int nameStart = i + 3;
                    int nameWords = 0;
                    while (nameStart + nameWords < words.Count)
                    {
                        uint lw = words[nameStart + nameWords];
                        nameWords++;
                        if ((lw & 0xFF) == 0 || (lw & 0xFF00) == 0 || (lw & 0xFF0000) == 0 || (lw & 0xFF000000) == 0) break;
                    }
                    int iface = nameStart + nameWords;
                    while (iface < i + (int)wc) { references.Add((words[iface], i, "entry_point_interface")); iface++; }
                    break;
                }
                case OpExecutionMode:
                    if (words[i + 2] == ExModeLocalSize) { localSizeSeen++; localSizeX = words[i + 3]; }
                    break;
                case OpDecorate:
                    references.Add((words[i + 1], i, "decorate_target"));
                    if (words[i + 2] == DecBinding) bindingCount++;
                    break;
                case OpFunction:
                    functionCount++;
                    break;
                case OpFunctionEnd:
                    endCount++;
                    break;
            }
            i += (int)wc;
        }

        if (i != words.Count && i < words.Count) issues.Add(new("TRAILING_WORDS", i, $"consumed={i} total={words.Count}"));
        if (maxId == 0) issues.Add(new("NO_RESULT_ID", 5, "模块未定义任何 id"));
        if (bound != 0 && maxId >= bound) issues.Add(new("ID_BOUND_TOO_SMALL", 3, $"bound={bound} max_id={maxId}"));
        if (!shaderCapability) issues.Add(new("MISSING_CAPABILITY_SHADER", 5, "未声明 Shader 能力"));
        if (!memoryModel) issues.Add(new("MISSING_MEMORY_MODEL_LOGICAL", 5, "未声明 Logical 内存模型"));
        if (entryCount == 0) issues.Add(new("NO_ENTRY_POINT", 5, "缺少 OpEntryPoint"));
        else if (entryCount > 1) issues.Add(new("MULTIPLE_ENTRY_POINTS", 5, $"count={entryCount}"));
        if (entryCount > 0 && !entryIsCompute) issues.Add(new("ENTRY_POINT_NOT_GLCOMPUTE", 5, "入口点执行模型不是 GLCompute"));
        if (localSizeSeen == 0) issues.Add(new("NO_EXECUTION_MODE_LOCAL_SIZE", 5, "缺少 LocalSize 执行模式"));
        else if (localSizeSeen > 1) issues.Add(new("MULTIPLE_EXECUTION_MODES", 5, $"count={localSizeSeen}"));
        else if (localSizeX != expectedLocalSize)
            issues.Add(new("LOCAL_SIZE_MISMATCH", 5, $"local_size_x={localSizeX} expected={expectedLocalSize}"));
        if (functionCount == 0) issues.Add(new("NO_FUNCTION", 5, "缺少 OpFunction"));
        else if (functionCount > 1) issues.Add(new("MULTIPLE_FUNCTIONS", 5, $"count={functionCount}"));
        if (endCount == 0) issues.Add(new("MISSING_FUNCTION_END", 5, "缺少 OpFunctionEnd"));
        else if (endCount > 1) issues.Add(new("MULTIPLE_FUNCTION_END", 5, $"count={endCount}"));
        if (bindingCount != expectedBuffers)
            issues.Add(new("DESCRIPTOR_COUNT_MISMATCH", 5, $"bindings={bindingCount} expected={expectedBuffers}"));

        foreach (var (id, word, what) in references)
            if (id != 0 && !defined.Contains(id)) issues.Add(new("UNDEFINED_ID_REFERENCE", word, $"{what} id={id}"));

        return issues;
    }

    /// <summary>便捷判定 (无问题 == 结构合法)。</summary>
    public static bool IsValid(IReadOnlyList<uint> words, int expectedLocalSize, int expectedBuffers)
        => Validate(words, expectedLocalSize, expectedBuffers).Count == 0;
}
