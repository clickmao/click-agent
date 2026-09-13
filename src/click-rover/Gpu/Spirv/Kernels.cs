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
        var va = s.Load(c.F32, s.AccessChain(c.PF32, a, c.I));
        var vx = s.Load(c.F32, s.AccessChain(c.PF32, x, c.I));
        var vy = s.Load(c.F32, s.AccessChain(c.PF32, y, c.I));
        var res = s.Bin(Spv.OpFAdd, c.F32, s.Bin(Spv.OpFMul, c.F32, va, vx), vy);
        s.Store(s.AccessChain(c.PF32, y, c.I), res);
    }, buffers: 3);

    /// <summary>out[i] = silu(g[i]) * u[i] = g/(1+exp(-g)) * u  (SwiGLU 激活, 逐元素)</summary>
    public static Kernel SiluMul() => Build("silu_mul", outPrologue: false, body: (s, c) =>
    {
        var g = c.Take(0); var u = c.Take(1); var o = c.Take(2);
        var vg = s.Load(c.F32, s.AccessChain(c.PF32, g, c.I));
        var vu = s.Load(c.F32, s.AccessChain(c.PF32, u, c.I));
        var neg = s.Bin(Spv.OpFNegate, c.F32, vg, vg);
        var e = s.Ext(c.F32, c.Glsl, 27, neg);                    // GLSL.std.450 Exp
        var one = s.ConstF32(1f);
        var den = s.Bin(Spv.OpFAdd, c.F32, one, e);
        var sig = s.Bin(Spv.OpFDiv, c.F32, vg, den);
        s.Store(s.AccessChain(c.PF32, o, c.I), s.Bin(Spv.OpFMul, c.F32, sig, vu));
    }, buffers: 3);

    /// <summary>v[i] = x[i] * s  (标量缩放, 用于 RMSNorm 的 1/rms 与 rope 的 mscale)</summary>
    public static Kernel ScaleInPlace() => Build("scale_inplace", outPrologue: false, body: (s, c) =>
    {
        var x = c.Take(0); var xs = c.Take(1);
        var vx = s.Load(c.F32, s.AccessChain(c.PF32, x, c.I));
        var vs = s.Load(c.F32, s.AccessChain(c.PF32, xs, s.ConstU32(0)));
        s.Store(s.AccessChain(c.PF32, x, c.I), s.Bin(Spv.OpFMul, c.F32, vx, vs));
    }, buffers: 2);

    sealed class Ctx
    {
        public uint F32, U32, Bool, V3U, Gid, Glsl, PF32, I;
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
