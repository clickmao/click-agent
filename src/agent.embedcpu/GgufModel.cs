using System.Buffers.Binary;
using System.Text;

namespace agent.embedcpu;

/// <summary>
/// v0.20.5 R353 (用户钦定): GGUF 文件最小解析器 — 仅 bge bert 架构所需键值与张量表。
/// 零依赖 (无 LLamaSharp/ONNX); Q8_0/F32 张量; 词表 (WordPiece) 完整读入。
/// </summary>
public sealed class GgufModel
{
    public Dictionary<string, long> IntKv { get; } = new();
    public Dictionary<string, float> FloatKv { get; } = new();
    public List<string> Tokens { get; } = new();
    public List<sbyte> TokenTypes { get; } = new();
    public Dictionary<string, TensorInfo> Tensors { get; } = new();
    public Stream Data { get; set; } = Stream.Null;
    public long DataSectionOffset { get; set; }

    public sealed class TensorInfo
    {
        public required string Name { get; init; }
        public required long[] Dims { get; init; }
        public required int GgmlType { get; init; }
        public required long Offset { get; init; }
        public int ElementCount => (int)Dims.Aggregate(1L, (a, b) => a * b);
    }

    public static bool Trace;
    public static bool TraceQ;

    public static GgufModel Load(string path)
    {
        var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        var br = new BinaryReader(fs);
        var magic = br.ReadBytes(4);
        if (magic is not [(byte)'G', (byte)'G', (byte)'U', (byte)'F'])
            throw new InvalidDataException("非 GGUF 文件");
        var version = br.ReadUInt32();
        if (version < 2) throw new InvalidDataException($"GGUF v{version} 不支持");
        var nTensors = br.ReadUInt64();
        var nKv = br.ReadUInt64();
        var model = new GgufModel();

        for (ulong i = 0; i < nKv; i++)
        {
            var key = ReadString(br);
            var type = br.ReadUInt32();
            if (agent.embedcpu.GgufModel.Trace) Console.Error.WriteLine($"kv {key} t={type}");
            switch (type)
            {
                case 4: model.IntKv[key] = br.ReadInt32(); break;          // u32
                case 7: br.ReadByte(); break;                              // bool (仅跳过)
                case 5: model.IntKv[key] = br.ReadInt32(); break;          // i32
                case 6: model.FloatKv[key] = br.ReadSingle(); break;       // f32
                case 10: model.IntKv[key] = (int)br.ReadUInt64(); break;   // u64
                case 8: ReadString(br); break;                              // str (暂不存)
                case 9:                                                     // array
                {
                    var et = br.ReadUInt32();
                    var count = br.ReadUInt64();
                    if (key == "tokenizer.ggml.tokens" && et == 8)
                    {
                        for (ulong j = 0; j < count; j++) model.Tokens.Add(ReadString(br));
                    }
                    else if (key == "tokenizer.ggml.token_type" && et == 5)
                    {
                        for (ulong j = 0; j < count; j++) model.TokenTypes.Add((sbyte)br.ReadInt32());
                    }
                    else if (et == 8)
                    {
                        for (ulong j = 0; j < count; j++) { var n = br.ReadUInt64(); fs.Seek((long)n, SeekOrigin.Current); }
                    }
                    else if (Sizes.TryGetValue(et, out var sz)) fs.Seek((long)sz * (long)count, SeekOrigin.Current);
                    else throw new InvalidDataException($"kv array et={et}");
                    break;
                }
                default: throw new InvalidDataException($"kv type={type}");
            }
        }

        for (ulong i = 0; i < nTensors; i++)
        {
            var name = ReadString(br);
            var nd = br.ReadUInt32();
            var dims = new long[nd];
            for (var d = 0; d < nd; d++) dims[d] = br.ReadInt64();
            var ggmlType = (int)br.ReadUInt32();
            var offset = br.ReadInt64();
            model.Tensors[name] = new TensorInfo { Name = name, Dims = dims, GgmlType = ggmlType, Offset = offset };
        }

        var pos = fs.Position;
        var aligned = (pos + 31) / 32 * 32;
        model.DataSectionOffset = aligned;
        model.Data = fs;
        return model;
    }

    static readonly Dictionary<uint, int> Sizes = new()
    { [0] = 1, [1] = 1, [2] = 2, [3] = 2, [4] = 4, [5] = 4, [6] = 4, [7] = 1, [10] = 8 };

    static string ReadString(BinaryReader br)
    {
        var n = br.ReadUInt64();
        var bytes = br.ReadBytes((int)n);
        return Encoding.UTF8.GetString(bytes);
    }

    /// <summary>读取并反量化张量为 F32 (Q8_0: 每 32 个 f16 权重 + 1 个 f16 scale; F32 原样)。</summary>
    public float[] ReadTensor(TensorInfo ti)
    {
        var count = ti.ElementCount;
        var result = new float[count];
        lock (Data)
        {
            Data.Seek(DataSectionOffset + ti.Offset, SeekOrigin.Begin);
            if (ti.GgmlType == 0) // F32
            {
                for (var i = 0; i < count; i++) result[i] = ReadF32Le(Data);
                return result;
            }
            if (ti.GgmlType == 8) // Q8_0: block = 2B scale(f16) + 32B (32×i8)
            {
                var nBlocks = (count + 31) / 32;
                if (count > 600)
                {
                    var p0 = Data.Position;
                    var hex = new byte[6];
                    Data.ReadExactly(hex, 0, 6);
                    Data.Seek(p0, SeekOrigin.Begin);
                    Console.Error.WriteLine($"[RAW6] {ti.Name}: {Convert.ToHexString(hex)}");
                }
                for (var b = 0; b < nBlocks; b++)
                {
                    var scale = ReadF16Le(Data);
                    var remain = Math.Min(32, count - b * 32);
                    for (var i = 0; i < 32; i++)
                    {
                        var q = (sbyte)Data.ReadByte(); // int8 有符号 (245 → -11)
                        if (i < remain) result[b * 32 + i] = q * scale;
                    }
                }
                return result;
            }
            if (ti.GgmlType == 1) // F16
            {
                for (var i = 0; i < count; i++) result[i] = ReadF16Le(Data);
                return result;
            }
            throw new NotSupportedException($"ggml type {ti.GgmlType}");
        }
    }

    static float ReadF32Le(Stream s)
    {
        Span<byte> b = stackalloc byte[4];
        s.ReadExactly(b);
        return BitConverter.UInt32BitsToSingle(BinaryPrimitives.ReadUInt32LittleEndian(b));
    }

    static float ReadF16Le(Stream s)
    {
        Span<byte> b = stackalloc byte[2];
        s.ReadExactly(b);
        var half = BinaryPrimitives.ReadUInt16LittleEndian(b);
        // IEEE754 half → single
        var sign = (half & 0x8000) << 16;
        var exp = (half & 0x7C00) >> 10;
        var frac = half & 0x03FF;
        uint bits;
        if (exp == 0) bits = (uint)sign; // 零/次正规 (近似 0, 权重场景可接受)
        else if (exp == 0x1F) bits = (uint)(sign | 0x7F800000 | (frac << 13));
        else bits = (uint)(sign | ((exp - 15 + 127) << 23) | (frac << 13));
        return BitConverter.UInt32BitsToSingle(bits);
    }
}
