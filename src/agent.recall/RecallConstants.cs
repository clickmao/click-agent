namespace agent.recall;


internal static class RecallConstants
{
    public const int Version = 1;
    public const int PostingBlockDocs = 128;   // 块 = block-max WAND 的跳过单位
    public const int TermTopStride = 1024;     // 词表二级跳表粒度 (常驻面 O(termCount/stride))
    public const double Bm25K1 = 1.2;
    public const double Bm25B = 0.75;

    public const string SegmentFile = "seg.meta";
    public const string TermsFile = "terms.bin";
    public const string PostingsFile = "postings.bin";
    public const string DocsFile = "docs.bin";
    public const string DocsLenFile = "lens.bin";
    public const string TextFile = "text.bin";
    public const string TombFile = "tomb.bin";
    public const string IndexMetaFile = "index.meta";
    public const string FingerprintFile = "fingerprints.bin";
    public const string SegmentPrefix = "seg_";

    public static ReadOnlySpan<byte> IndexMagic => "ARECIDX1"u8;
    public static ReadOnlySpan<byte> SegmentMagic => "ARECSEG1"u8;
    public static ReadOnlySpan<byte> DocsMagic => "ARECDOC1"u8;
    public static ReadOnlySpan<byte> LensMagic => "ARECLEN1"u8;
    public static ReadOnlySpan<byte> TombMagic => "ARECTOM1"u8;
    public static ReadOnlySpan<byte> FpMagic => "ARECFP01"u8;
    public static ReadOnlySpan<byte> LinksMagic => "ARECLNK1"u8;
    public const string LinksFile = "links.bin";
}
