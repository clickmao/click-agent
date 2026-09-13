namespace clickrover.gpu.spirv;

/// <summary>GPU 内核目录: 显式构造的 SPIR-V (见 <see cref="Spv"/>)。</summary>
public static class Kernels
{
    /// <summary>内核描述: 名字 + SPIR-V 字 + 工作组大小 + 缓冲绑定数 (binding 0..n-1 全部是 f32 runtime array)。</summary>
    public sealed record Kernel(string Name, uint[] Words, uint LocalSizeX, int BufferCount);

    /// <summary>y[i] = a[i] * x[i] + y[i]  (逐元素, 用于残差/缩放融合)</summary>
    public static Kernel FmaVec() => Build("fma_vec", outPrologue: false, body: (s, c) =>
    {
        var a = c.Take(0); var x = c.Take(1); var y = c.Take(2);
        var va = s.Load(c.F32, Elem(s, c, a, c.I));
        var vx = s.Load(c.F32, Elem(s, c, x, c.I));
        var vy = s.Load(c.F32, Elem(s, c, y, c.I));
        var res = s.Bin(Spv.OpFAdd, c.F32, s.Bin(Spv.OpFMul, c.F32, va, vx), vy);
        s.Store(Elem(s, c, y, c.I), res);
    }, buffers: 3);

    /// <summary>out[i] = silu(g[i]) * u[i] = g/(1+exp(-g)) * u  (SwiGLU 激活, 逐元素)</summary>
    public static Kernel SiluMul() => Build("silu_mul", outPrologue: false, body: (s, c) =>
    {
        var g = c.Take(0); var u = c.Take(1); var o = c.Take(2);
        var vg = s.Load(c.F32, Elem(s, c, g, c.I));
        var vu = s.Load(c.F32, Elem(s, c, u, c.I));
        var neg = s.Bin(Spv.OpFNegate, c.F32, vg, vg);
        var e = s.Ext(c.F32, c.Glsl, Spv.GlslExp, neg);           // GLSL.std.450 Exp (常量须过 SpvRegistryAudit)
        var one = s.ConstF32(1f);
        var den = s.Bin(Spv.OpFAdd, c.F32, one, e);
        var sig = s.Bin(Spv.OpFDiv, c.F32, vg, den);
        s.Store(Elem(s, c, o, c.I), s.Bin(Spv.OpFMul, c.F32, sig, vu));
    }, buffers: 3);

    /// <summary>v[i] = x[i] * s  (标量缩放, 用于 RMSNorm 的 1/rms 与 rope 的 mscale)</summary>
    public static Kernel ScaleInPlace() => Build("scale_inplace", outPrologue: false, body: (s, c) =>
    {
        var x = c.Take(0); var xs = c.Take(1);
        var vx = s.Load(c.F32, Elem(s, c, x, c.I));
        var vs = s.Load(c.F32, Elem(s, c, xs, c.Zero));
        s.Store(Elem(s, c, x, c.I), s.Bin(Spv.OpFMul, c.F32, vx, vs));
    }, buffers: 2);

    /// <summary>
    /// 诊断探针 (机制分解, v4): 把"动态索引"与"缓冲绑定位置"两个变量彻底解耦 ——
    ///   cst[0..3] = 101..104  常量索引 store 进 binding 1   ⇒ 该绑定是否可写
    ///   dyn[I]    = 7.0f      动态索引 store 进 binding 2   ⇒ 动态索引本身 (binding 2 已知可写)
    ///   dync[I]   = float(I)  动态索引 store 进 binding 3   ⇒ 动态索引 + 值来自调用 id
    ///   diag[0]   = ArrayLength(src)  diag[1] = 42f  diag[2] = src[0]   (binding 4: 可写性 + 常量索引读)
    /// 变量声明顺序即 host 缓冲顺序: 0=src 1=cst 2=dyn 3=dync 4=diag (错位必致读数张冠李戴)。
    /// 三态可判: 全部落空 / 只落 binding 2 / 全部落地 ⇒ 定位到"绑定"还是"索引"。
    /// </summary>
    public static Kernel DiagProbe() => Build("diag_probe", outPrologue: false, body: (s, c) =>
    {
        var src = c.Take(0); var cst = c.Take(1); var dyn = c.Take(2); var dync = c.Take(3); var diag = c.Take(4);
        var one = s.ConstU32(1);
        var two = s.ConstU32(2);
        var three = s.ConstU32(3);
        s.Store(Elem(s, c, cst, c.Zero), s.ConstF32(101f));
        s.Store(Elem(s, c, cst, one), s.ConstF32(102f));
        s.Store(Elem(s, c, cst, two), s.ConstF32(103f));
        s.Store(Elem(s, c, cst, three), s.ConstF32(104f));
        s.Store(Elem(s, c, dyn, c.I), s.ConstF32(7f));
        s.Store(Elem(s, c, dync, c.I), s.UToF(c.F32, c.I));
        s.Store(Elem(s, c, diag, c.Zero), s.UToF(c.F32, s.ArrayLength(src, 0)));
        s.Store(Elem(s, c, diag, one), s.ConstF32(42f));
        s.Store(Elem(s, c, diag, two), s.Load(c.F32, Elem(s, c, src, c.Zero)));
        // 关键鉴别: 用**常量索引**写出调用 id 自身 —— 若动态寻址坏而此值正确(∈[0,pe)) ⇒ 索引值无误、坏在寻址;
        // 若此值是巨值/垃圾 ⇒ 内置变量供给或守卫比较失效 (二者都表现为"动态写不可见")。
        s.Store(Elem(s, c, diag, three), s.UToF(c.F32, c.I));
    }, buffers: 5);

    /// <summary>
    /// 存储缓冲元素指针: 缓冲变量类型是 `%ptr StorageBuffer %struct{ %arr }`,
    /// 故索引链必须是 (成员索引=0 常量, 元素索引) —— 少了成员索引就是**指向 runtime array 的指针**,
    /// 与结果类型 (ptr f32) 不符 (真机 CreateComputePipelines 直接失败; 结构合法≠语义合法)。
    /// </summary>
    static uint Elem(Spv s, Ctx c, uint buf, uint idx) => s.AccessChain(c.PF32, buf, c.Zero, idx);

    sealed class Ctx
    {
        public uint F32, U32, Bool, V3U, Gid, Glsl, PF32, I, Zero;
        public uint[] Bufs = Array.Empty<uint>();
        public uint Take(int i) => Bufs[i];
    }

    static Kernel Build(string name, bool outPrologue, Action<Spv, Ctx> body, int buffers, uint localSize = 256)
    {
        var s = new Spv();
        s.Cap(Spv.CapShader);
        s.MemoryModel();
        uint fnId = s.ReserveId();
        var c = new Ctx();
        c.F32 = s.TypeF32(); c.U32 = s.TypeU32(); c.Bool = s.TypeBool();
        c.V3U = s.TypeVec(c.U32, 3);
        c.Zero = s.ConstU32(0);
        c.Glsl = s.ExtInstImport("GLSL.std.450");
        uint pIn = s.TypePtr(Spv.ScInput, c.V3U);
        c.Gid = s.Var(pIn, Spv.ScInput);
        s.BuiltIn(c.Gid, Spv.BuiltInGlobalInvocationId);
        var arr = s.TypeRuntimeArray(c.F32);
        s.ArrayStride(arr, 4);
        var str = s.TypeStruct(arr);
        s.MemberDecorate(str, 0, Spv.DecOffset, 0);
        s.Decorate(str, Spv.DecBlock);
        var pStr = s.TypePtr(Spv.ScStorageBuffer, str);
        c.PF32 = s.TypePtr(Spv.ScStorageBuffer, c.F32);
        c.Bufs = new uint[buffers];
        for (int i = 0; i < buffers; i++)
        {
            c.Bufs[i] = s.Var(pStr, Spv.ScStorageBuffer);
            s.Descriptor(c.Bufs[i], 0, (uint)i);
        }
        s.EntryPoint(Spv.ExecGLCompute, fnId, "main", c.Gid);
        s.ExecMode(fnId, Spv.ExModeLocalSize, localSize, 1, 1);
        var fnTy = s.TypeFn(s.TypeVoid());
        s.Function(fnId, s.TypeVoid(), fnTy);
        var entry = s.Label();
        c.I = s.Extract(c.U32, s.Load(c.V3U, c.Gid), 0);
        var n = s.ArrayLength(c.Bufs[0], 0);
        var oob = s.Bin(Spv.OpUGreaterThanEqual, c.Bool, c.I, n);
        var retL = s.LabelFor();
        var merge = s.LabelFor();
        s.SelectionMerge(merge);
        s.BranchCond(oob, retL, merge);
        s.Place(retL); s.Return();
        s.Place(merge);
        body(s, c);
        s.Return();
        s.FnEnd();
        return new Kernel(name, s.Build(), localSize, buffers);
    }
}
