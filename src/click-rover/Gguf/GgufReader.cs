using System.Text;

namespace clickrover.gguf;

/// <summary>GGUF 元数据值的类型标签 (数值对齐 GGUF 规范 v3)。</summary>
public enum GgufValueKind : uint
{
    UInt8 = 0, Int8 = 1, UInt16 = 2, Int16 = 3, UInt32 = 4, Int32 = 5,
    Float32 = 6, Bool = 7, String = 8, Array = 9, UInt64 = 10, Int64 = 11, Float64 = 12,
}

/// <summary>元数据值 (联合体; 数组只存引用, 字符串数组按需物化 — 10 万词表不预读)。</summary>
public readonly struct GgufValue
{
    public GgufValueKind Kind { get; init; }
    public long I { get; init; }
    public double F { get; init; }
    public string? S { get; init; }
    public GgufArray? A { get; init; }

    /// <summary>整数类值 (排除浮点/串/数组) — cfg 取值时用来区分 raw=u 与 raw=f。</summary>
    public bool IsInteger => Kind is not (GgufValueKind.Float32 or GgufValueKind.Float64
        or GgufValueKind.String or GgufValueKind.Array);

    public long AsLong() => Kind switch
    {
        GgufValueKind.UInt8 or GgufValueKind.Int8 or GgufValueKind.UInt16 or GgufValueKind.Int16
            or GgufValueKind.UInt32 or GgufValueKind.Int32 or GgufValueKind.UInt64 or GgufValueKind.Int64
            or GgufValueKind.Bool => I,
        GgufValueKind.Float32 or GgufValueKind.Float64 => (long)Math.Round(F),
        _ => throw new InvalidCastException($"kv_not_integer: {Kind}"),
    };

    public double AsDouble() => Kind switch
    {
        GgufValueKind.Float32 or GgufValueKind.Float64 => F,
        GgufValueKind.UInt8 or GgufValueKind.Int8 or GgufValueKind.UInt16 or GgufValueKind.Int16
            or GgufValueKind.UInt32 or GgufValueKind.Int32 or GgufValueKind.UInt64 or GgufValueKind.Int64 => I,
        _ => throw new InvalidCastException($"kv_not_number: {Kind}"),
    };
}

/// <summary>数组引用: 元素类型 + 个数 + 起始文件偏移 (用于按需物化, 尤其字符串数组)。</summary>
public sealed class GgufArray
{
    public required GgufValueKind ElemKind { get; init; }
    public required long Count { get; init; }
    public required long ElementsOffset { get; init; }
    /// <summary>已物化的标量数组 (字符串数组为 null, 需显式物化)</summary>
    public List<GgufValue>? Items { get; init; }
}

/// <summary>张量目录项 (数据永不预读 — 只有 offset/尺寸, 取用时才碰页)。</summary>
public sealed class GgufTensorInfo
{
    public required string Name { get; init; }
    public required long[] Dims { get; init; }
    public required GgmlType Type { get; init; }
    /// <summary>相对数据段起点的偏移</summary>
    public required long Offset { get; init; }
    /// <summary>元素总数 (dims 连乘)</summary>
    public required long ElementCount { get; init; }
    /// <summary>字节总数 (按块布局算, 非 dims 连乘)</summary>
    public required long ByteSize { get; init; }
    /// <summary>行元素数 (ggml ne[0] = dims[0])</summary>
    public long RowElems => Dims.Length > 0 ? Dims[0] : 1;
    public long Rows => ElementCount / Math.Max(1, RowElems);
}

/// <summary>
/// GGUF 读取器: 头部元数据 + 张量目录立即解析 (头部只有几 MB);
/// 权重数据保持 mmap 惰性, 通过 <see cref="TensorWindow"/> 零拷贝取用。
/// 解析严格: 魔数/版本/类型不支持均即时报错, 不静默降级。
/// </summary>
public sealed unsafe class GgufReader : IDisposable
{
    public const uint Magic = 0x46554747; // "GGUF" LE

    private readonly GgufMappedFile _file;
    private readonly Dictionary<string, GgufValue> _kv = new(StringComparer.Ordinal);
    private readonly Dictionary<string, GgufTensorInfo> _tensors = new(StringComparer.Ordinal);
    private readonly List<string> _tensorOrder = new();

    public string Path { get; }
    public uint Version { get; private set; }
    public long TensorCount { get; private set; }
    public long KvCount { get; private set; }
    /// <summary>数据段起始偏移 (元数据尾按 general.alignment 对齐)</summary>
    public long DataSectionOffset { get; private set; }
    public int Alignment { get; private set; } = 32;
    /// <summary>元数据解析耗时 (ms)</summary>
    public long ParseMs { get; private set; }
    public GgufMappedFile Mapped => _file;

    public IReadOnlyDictionary<string, GgufValue> Kv => _kv;
    public IReadOnlyList<string> TensorNames => _tensorOrder;

    private GgufReader(string path, GgufMappedFile file)
    {
        Path = path;
        _file = file;
    }

    public static GgufReader Open(string path)
    {
        var file = GgufMappedFile.Open(path);
        try
        {
            var r = new GgufReader(path, file);
            r.ParseHeader();
            return r;
        }
        catch
        {
            file.Dispose();
            throw;
        }
    }

    public GgufTensorInfo? Find(string name) => _tensors.TryGetValue(name, out var t) ? t : null;

    public GgufTensorInfo Require(string name) =>
        Find(name) ?? throw new KeyNotFoundException($"tensor_not_found: {name} (file={Path})");

    private void ParseHeader()
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var p = _file.Pointer;
        long pos = 0;
        long len = _file.Length;
        if (len < 32) throw new InvalidDataException($"gguf_too_small: {len} bytes");

        uint magic = ReadU32(p, ref pos, len);
        if (magic != Magic) throw new InvalidDataException($"gguf_bad_magic: 0x{magic:X8} (期望 0x{Magic:X8})");
        Version = ReadU32(p, ref pos, len);
        if (Version < 2 || Version > 3) throw new InvalidDataException($"gguf_unsupported_version: {Version}");
        TensorCount = (long)ReadU64(p, ref pos, len);
        KvCount = (long)ReadU64(p, ref pos, len);

        for (long i = 0; i < KvCount; i++)
        {
            var key = ReadString(p, ref pos, len);
            var kind = (GgufValueKind)ReadU32(p, ref pos, len);
            var val = ReadValue(p, ref pos, len, kind, materialize: true);
            _kv[key] = val;
        }

        if (_kv.TryGetValue("general.alignment", out var al) && al.Kind != GgufValueKind.Array)
            Alignment = (int)al.AsLong();

        // 数据段起始 = **张量信息段之后**按 general.alignment 对齐 (在 KV 段之后算会少算整段张量信息字节)
        for (long i = 0; i < TensorCount; i++)
        {
            var name = ReadString(p, ref pos, len);
            uint nDims = ReadU32(p, ref pos, len);
            var dims = new long[nDims];
            for (int d = 0; d < nDims; d++) dims[d] = (long)ReadU64(p, ref pos, len);
            var type = (GgmlType)ReadU32(p, ref pos, len);
            long offset = (long)ReadU64(p, ref pos, len);

            long elems = 1;
            foreach (var d in dims) elems *= d;
            var info = new GgufTensorInfo
            {
                Name = name,
                Dims = dims,
                Type = type,
                Offset = offset,
                ElementCount = elems,
                ByteSize = BlockLayout.TensorBytes(type, dims),
            };
            if (Align(pos, Alignment) + offset + info.ByteSize > len)
                throw new InvalidDataException(
                    $"tensor_out_of_range: {name} end={Align(pos, Alignment) + offset + info.ByteSize} fileLen={len}");
            _tensors[name] = info;
            _tensorOrder.Add(name);
        }
        DataSectionOffset = Align(pos, Alignment);
        sw.Stop();
        ParseMs = sw.ElapsedMilliseconds;
    }

    /// <summary>张量的零拷贝窗口 (惰性: 只有这里才触碰权重页)。</summary>
    public ReadOnlySpan<byte> TensorWindow(GgufTensorInfo t)
    {
        if (t.ByteSize > int.MaxValue)
            throw new NotSupportedException($"tensor_too_large_for_span: {t.Name} {t.ByteSize} bytes");
        return _file.Window(DataSectionOffset + t.Offset, (int)t.ByteSize);
    }

    // ---- KV 取值 ----

    public bool TryGetLong(string key, out long value)
    {
        if (_kv.TryGetValue(key, out var v) && v.IsInteger)
        {
            value = v.I;
            return true;
        }
        value = 0;
        return false;
    }

    public long GetLong(string key, long fallback)
    {
        if (TryGetLong(key, out var v)) return v;
        return fallback;
    }

    public bool TryGetFloat(string key, out double value)
    {
        if (_kv.TryGetValue(key, out var v) && v.Kind != GgufValueKind.Array && v.Kind != GgufValueKind.String)
        {
            value = v.AsDouble();
            return true;
        }
        value = 0;
        return false;
    }

    public string? GetString(string key) =>
        _kv.TryGetValue(key, out var v) && v.Kind == GgufValueKind.String ? v.S : null;

    /// <summary>字符串数组按需物化 (词表 10 万条: 只在这里读一次)。</summary>
    public List<string> GetStringArray(string key)
    {
        if (!_kv.TryGetValue(key, out var v) || v.A is null)
            throw new KeyNotFoundException($"kv_not_string_array: {key}");
        if (v.A.Items is { } cached && cached.Count > 0 && cached[0].Kind == GgufValueKind.String)
            return cached.Select(x => x.S ?? string.Empty).ToList();

        var p = _file.Pointer;
        long pos = v.A.ElementsOffset;
        long len = _file.Length;
        var list = new List<string>((int)v.A.Count);
        for (long i = 0; i < v.A.Count; i++)
            list.Add(ReadString(p, ref pos, len));
        return list;
    }

    public bool HasKey(string key) => _kv.ContainsKey(key);

    // ---- 原语 ----

    private static long Align(long pos, int alignment) =>
        alignment <= 1 ? pos : (pos + alignment - 1) / alignment * alignment;

    private static unsafe uint ReadU32(byte* p, ref long pos, long len)
    {
        if (pos + 4 > len) throw new EndOfStreamException($"gguf_truncated_at: {pos}");
        uint v = (uint)(p[pos] | (p[pos + 1] << 8) | (p[pos + 2] << 16) | (p[pos + 3] << 24));
        pos += 4;
        return v;
    }

    private static unsafe ulong ReadU64(byte* p, ref long pos, long len)
    {
        if (pos + 8 > len) throw new EndOfStreamException($"gguf_truncated_at: {pos}");
        ulong lo = ReadU32(p, ref pos, len);
        ulong hi = ReadU32(p, ref pos, len);
        return lo | (hi << 32);
    }

    private static unsafe string ReadString(byte* p, ref long pos, long len)
    {
        ulong n = ReadU64(p, ref pos, len);
        if (n > int.MaxValue) throw new InvalidDataException($"gguf_string_too_long: {n}");
        if (pos + (long)n > len) throw new EndOfStreamException($"gguf_string_truncated_at: {pos}");
        var s = Encoding.UTF8.GetString(p + pos, (int)n);
        pos += (long)n;
        return s;
    }

    private static unsafe GgufValue ReadValue(byte* p, ref long pos, long len, GgufValueKind kind, bool materialize)
    {
        switch (kind)
        {
            case GgufValueKind.UInt8: return new GgufValue { Kind = kind, I = p[pos++] };
            case GgufValueKind.Int8: return new GgufValue { Kind = kind, I = (sbyte)p[pos++] };
            case GgufValueKind.UInt16:
            {
                ushort v = (ushort)(p[pos] | (p[pos + 1] << 8)); pos += 2;
                return new GgufValue { Kind = kind, I = v };
            }
            case GgufValueKind.Int16:
            {
                short v = (short)(p[pos] | (p[pos + 1] << 8)); pos += 2;
                return new GgufValue { Kind = kind, I = v };
            }
            case GgufValueKind.UInt32: return new GgufValue { Kind = kind, I = ReadU32(p, ref pos, len) };
            case GgufValueKind.Int32: return new GgufValue { Kind = kind, I = (int)ReadU32(p, ref pos, len) };
            case GgufValueKind.Float32:
            {
                uint bits = ReadU32(p, ref pos, len);
                return new GgufValue { Kind = kind, F = BitConverter.UInt32BitsToSingle(bits) };
            }
            case GgufValueKind.Bool: return new GgufValue { Kind = kind, I = p[pos++] };
            case GgufValueKind.String: return new GgufValue { Kind = kind, S = ReadString(p, ref pos, len) };
            case GgufValueKind.UInt64: return new GgufValue { Kind = kind, I = (long)ReadU64(p, ref pos, len) };
            case GgufValueKind.Int64: return new GgufValue { Kind = kind, I = (long)ReadU64(p, ref pos, len) };
            case GgufValueKind.Float64:
            {
                ulong bits = ReadU64(p, ref pos, len);
                return new GgufValue { Kind = kind, F = BitConverter.UInt64BitsToDouble(bits) };
            }
            case GgufValueKind.Array:
            {
                var elemKind = (GgufValueKind)ReadU32(p, ref pos, len);
                ulong count = ReadU64(p, ref pos, len);
                long elemStart = pos;
                bool stringElems = elemKind == GgufValueKind.String;
                bool bigStringArray = stringElems && (!materialize || count > 1024);
                var items = bigStringArray ? null : new List<GgufValue>((int)Math.Min(count, 4096));
                for (ulong i = 0; i < count; i++)
                {
                    var item = ReadValue(p, ref pos, len, elemKind, materialize: false);
                    if (bigStringArray) continue; // 只推进游标, 不物化 (10 万词表不进堆)
                    items!.Add(item);
                }
                return new GgufValue
                {
                    Kind = kind,
                    A = new GgufArray
                    {
                        ElemKind = elemKind,
                        Count = (long)count,
                        ElementsOffset = elemStart,
                        Items = items,
                    },
                };
            }
            default:
                throw new NotSupportedException($"gguf_kv_type_unsupported: {kind} at {pos}");
        }
    }

    public void Dispose() => _file.Dispose();
}
