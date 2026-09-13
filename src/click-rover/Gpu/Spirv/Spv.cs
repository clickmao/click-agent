using System.Text;

namespace clickrover.gpu.spirv;

/// <summary>
/// 极简 SPIR-V 汇编器: 本机与发布环境都没有 glslangValidator/glslc, 而 GPU 路径必须有 SPIR-V。
/// 故内核以指令级显式构造 (零外部工具链, AOT 友好), 由 gpu-check 在真实驱动上跑通并数值对账。
/// 严格按 SPIR-V 逻辑布局分段输出: 头 / 前置(能力·内存模型·导入·入口点·执行模式) /
/// 注解(装饰) / 模块级(类型·常量·全局变量) / 函数体。这样"先定义后使用"天然成立。
/// 只实现本引擎用到的子集; 未实现的一律抛错 (不静默)。
/// </summary>
public sealed class Spv
{
    readonly uint[] _header = { 0x07230203, 0x00010300, 0, 0, 0 };
    readonly List<uint> _pre = new(), _ann = new(), _main = new(), _fn = new();
    List<uint> _t;
    int _bound = 1;

    public Spv() => _t = _main;
    void Emit(List<uint> into, uint opcode, params uint[] ops)
    {
        into.Add(((uint)ops.Length + 1) << 16 | opcode);
        into.AddRange(ops);
    }
    void E(uint opcode, params uint[] ops) => Emit(_t, opcode, ops);
    void EP(uint opcode, params uint[] ops) => Emit(_pre, opcode, ops);
    void EA(uint opcode, params uint[] ops) => Emit(_ann, opcode, ops);

    public uint NewId() => (uint)_bound++;
    public uint ReserveId() => NewId();

    uint Res(uint type, uint opcode, params uint[] rest)
    {
        uint id = NewId();
        var ops = new uint[rest.Length + 2];
        ops[0] = type; ops[1] = id;
        Array.Copy(rest, 0, ops, 2, rest.Length);
        E(opcode, ops);
        return id;
    }
    public uint[] Build()
    {
        var total = _header.Length + _pre.Count + _ann.Count + _main.Count + _fn.Count;
        var w = new uint[total];
        int p = 0;
        _header.CopyTo(w, p); p += _header.Length;
        _pre.CopyTo(w, p); p += _pre.Count;
        _ann.CopyTo(w, p); p += _ann.Count;
        _main.CopyTo(w, p); p += _main.Count;
        _fn.CopyTo(w, p);
        w[3] = (uint)_bound;
        return w;
    }

    // ---- opcode / 枚举 ----
    public const uint OpCapability = 17, OpMemoryModel = 14, OpEntryPoint = 15, OpExecutionMode = 16,
        OpTypeVoid = 19, OpTypeBool = 20, OpTypeInt = 21, OpTypeFloat = 22, OpTypeVector = 23,
        OpTypeRuntimeArray = 29, OpTypeStruct = 30, OpTypePointer = 32, OpTypeFunction = 33,
        OpConstant = 43, OpFunction = 54, OpFunctionEnd = 56, OpVariable = 59,
        OpLoad = 61, OpStore = 62, OpAccessChain = 65, OpArrayLength = 68,
        OpDecorate = 71, OpMemberDecorate = 72, OpCompositeExtract = 81,
        OpExtInstImport = 11, OpExtInst = 12, OpLabel = 248, OpReturn = 253,
        OpConvertUToF = 112,
        OpFNegate = 127, OpIAdd = 128, OpFAdd = 129, OpISub = 130, OpFSub = 131, OpIMul = 132,
        OpFMul = 133, OpFDiv = 136, OpBitcast = 124,
        OpUGreaterThanEqual = 174, OpBranch = 249, OpBranchConditional = 250, OpSelectionMerge = 247,
        OpSelect = 169;

    public const uint CapShader = 1, MemLogical = 0, MemGLSL450 = 1, ExecGLCompute = 5,
        ScInput = 1, ScWorkgroup = 4, ScStorageBuffer = 12,
        DecBlock = 2, DecArrayStride = 6, DecDescriptorSet = 34, DecBinding = 33, DecBuiltIn = 11,
        DecOffset = 35, BuiltInGlobalInvocationId = 28, ExModeLocalSize = 17;

    /// <summary>GLSL.std.450 扩展指令号 (命名约定 Glsl&lt;Name&gt;: 由 SpvRegistryAudit 对权威 extinst grammar 核对)。</summary>
    public const uint GlslExp = 27;

    // ---- 前置段 ----
    public uint Cap(uint c) { EP(OpCapability, c); return c; }
    public uint MemoryModel() { EP(OpMemoryModel, MemLogical, MemGLSL450); return 0; }
    public uint EntryPoint(uint exec, uint fn, string name, params uint[] iface)
    {
        var bytes = Encoding.ASCII.GetBytes(name);
        int nw = (bytes.Length + 4) / 4;
        var ops = new uint[2 + nw + iface.Length];
        ops[0] = exec; ops[1] = fn;
        for (int i = 0; i < bytes.Length; i++) ops[2 + i / 4] |= (uint)bytes[i] << (8 * (i % 4));
        Array.Copy(iface, 0, ops, 2 + nw, iface.Length);
        EP(OpEntryPoint, ops);
        return fn;
    }
    public uint ExecMode(uint fn, uint mode, params uint[] args)
    {
        // SPIR-V 规范: OpExecutionMode 操作数 = EntryPoint(id), Execution Mode(literal), Literal...
        // (旧实现漏写 mode → 驱动必然拒收; 由独立结构校验器 SpirvValidator 抓出)
        var ops = new uint[2 + args.Length];
        ops[0] = fn; ops[1] = mode;
        Array.Copy(args, 0, ops, 2, args.Length);
        EP(OpExecutionMode, ops);
        return fn;
    }

    // ---- 注解段 ----
    public uint Decorate(uint target, uint dec, params uint[] args) { EA(OpDecorate, Pre(target, Pre(dec, args))); return target; }
    public uint MemberDecorate(uint target, uint member, uint dec, params uint[] args)
    { EA(OpMemberDecorate, Pre(target, Pre(member, Pre(dec, args)))); return target; }
    public uint ArrayStride(uint arrType, uint stride) => Decorate(arrType, DecArrayStride, stride);
    public uint Descriptor(uint varId, uint set, uint binding) { Decorate(varId, DecDescriptorSet, set); return Decorate(varId, DecBinding, binding); }
    public uint BuiltIn(uint varId, uint builtin) => Decorate(varId, DecBuiltIn, builtin);

    // ---- 模块级 (始终写入模块段: 即便在函数体构造期内被惰性创建, 也必须落在函数段之前) ----
    void EM(uint opcode, params uint[] ops) => Emit(_main, opcode, ops);
    uint ResM(uint type, uint opcode, params uint[] rest)
    {
        uint id = NewId();
        var ops = new uint[rest.Length + 2];
        ops[0] = type; ops[1] = id;
        Array.Copy(rest, 0, ops, 2, rest.Length);
        EM(opcode, ops);
        return id;
    }
    public uint TypeVoid() { uint id = NewId(); EM(OpTypeVoid, id); return id; }
    public uint TypeBool() { uint id = NewId(); EM(OpTypeBool, id); return id; }
    public uint TypeU32() { uint id = NewId(); EM(OpTypeInt, id, 32, 0); return id; }
    public uint TypeF32() { uint id = NewId(); EM(OpTypeFloat, id, 32); return id; }
    public uint TypeVec(uint comp, uint n) { uint id = NewId(); EM(OpTypeVector, id, comp, n); return id; }
    public uint TypePtr(uint storage, uint type) { uint id = NewId(); EM(OpTypePointer, id, storage, type); return id; }
    public uint TypeRuntimeArray(uint elem) { uint id = NewId(); EM(OpTypeRuntimeArray, id, elem); return id; }
    public uint TypeStruct(params uint[] members) { uint id = NewId(); EM(OpTypeStruct, Pre(id, members)); return id; }
    public uint TypeFn(uint ret) { uint id = NewId(); EM(OpTypeFunction, id, ret); return id; }
    public uint ConstU32(uint v) { uint id = NewId(); EM(OpConstant, TypeU32(), id, v); return id; }
    public uint ConstF32(float v) { uint id = NewId(); EM(OpConstant, TypeF32(), id, BitConverter.SingleToUInt32Bits(v)); return id; }
    public uint Var(uint ptrType, uint storage) { uint id = NewId(); EM(OpVariable, ptrType, id, storage); return id; }

    // ---- 函数段 ----
    public uint Function(uint ret, uint fnType) { _t = _fn; uint id = NewId(); E(OpFunction, ret, id, 0, fnType); return id; }
    public uint Function(uint existingId, uint ret, uint fnType) { _t = _fn; E(OpFunction, ret, existingId, 0, fnType); return existingId; }
    public uint FnEnd() { E(OpFunctionEnd); _t = _main; return 0; }
    public uint Label() { uint id = NewId(); E(OpLabel, id); return id; }
    /// <summary>预约一个块标签 id (稍后用 <see cref="Place"/> 落位, 以便前向分支)。</summary>
    public uint LabelFor() => NewId();
    public uint Place(uint label) { E(OpLabel, label); return label; }
    public uint Un(uint op, uint type, uint a) => Res(type, op, a);
    public uint Return() { E(OpReturn); return 0; }
    public uint Load(uint type, uint ptr) => Res(type, OpLoad, ptr);
    public uint Store(uint ptr, uint val) { E(OpStore, ptr, val); return 0; }
    public uint AccessChain(uint ptrType, uint baseVar, params uint[] idx) => Res(ptrType, OpAccessChain, Pre(baseVar, idx));
    public uint ArrayLength(uint structPtr, uint member) => Res(TypeU32(), OpArrayLength, structPtr, member);
    /// <summary>uint → f32 位值转换 (诊断用; 复用调用方给的 f32 类型 id, 不新建类型)。</summary>
    public uint UToF(uint f32Type, uint u) => Res(f32Type, OpConvertUToF, u);
    public uint Extract(uint type, uint composite, params uint[] idx) => Res(type, OpCompositeExtract, Pre(composite, idx));
    public uint Bin(uint op, uint type, uint a, uint b) => Res(type, op, a, b);
    public uint Ext(uint type, uint set, uint inst, params uint[] ops) => Res(type, OpExtInst, Pre(set, Pre(inst, ops)));
    public uint Select(uint type, uint cond, uint a, uint b) => Res(type, OpSelect, cond, a, b);
    public uint Branch(uint label) { E(OpBranch, label); return 0; }
    public uint BranchCond(uint cond, uint thenL, uint elseL) { E(OpBranchConditional, cond, thenL, elseL); return 0; }
    public uint SelectionMerge(uint merge) { E(OpSelectionMerge, merge, 0); return 0; }
    public uint ExtInstImport(string name)
    {
        uint id = NewId();
        var bytes = Encoding.ASCII.GetBytes(name + "\0");
        int nw = (bytes.Length + 3) / 4;
        var ops = new uint[1 + nw];
        ops[0] = id;
        for (int i = 0; i < bytes.Length; i++) ops[1 + i / 4] |= (uint)bytes[i] << (8 * (i % 4));
        EP(OpExtInstImport, ops);
        return id;
    }
    static uint[] Pre(uint head, uint[] xs) { var a = new uint[xs.Length + 1]; a[0] = head; Array.Copy(xs, 0, a, 1, xs.Length); return a; }
}
