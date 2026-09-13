using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace agent.rover.token;

/// <summary>
/// 分词器表快照装载 (eval/rover/tokref/tables/*) —— 供无需 4.2 GB 模型的复跑/对账路径使用。
/// 与 GGUF 同源: meta.json 登记源模型 sha256 与各表 sha256, 装载时逐项校验 (缺项即失败, 不静默)。
/// 纯 BCL (GZipStream + JsonDocument), 与 CLI/测试同源编译。
/// </summary>
public static class TableSnapshot
{
    public static bool TryLoad(string dir, out BpeTokenizer? tokenizer, out string provenance, out string error)
    {
        tokenizer = null;
        if (!TryLoadRaw(dir, out List<string> tokens, out List<int> types, out List<string> merges, out provenance, out error))
        {
            return false;
        }

        tokenizer = new BpeTokenizer(tokens, types, merges);
        return true;
    }

    /// <summary>装载原始表 (tokens/types/merges), 供构建变体 (负控) 使用。</summary>
    public static bool TryLoadRaw(string dir, out List<string> tokens, out List<int> types, out List<string> merges,
        out string provenance, out string error)
    {
        tokens = [];
        types = [];
        merges = [];
        provenance = string.Empty;
        error = string.Empty;
        try
        {
            string metaPath = Path.Combine(dir, "meta.json");
            string mergesPath = Path.Combine(dir, "merges.txt");
            string tokensPath = Path.Combine(dir, "tokens.jsonl.gz");
            foreach (string p in new[] { metaPath, mergesPath, tokensPath })
            {
                if (!File.Exists(p))
                {
                    error = $"缺文件: {p}";
                    return false;
                }
            }

            using JsonDocument meta = JsonDocument.Parse(File.ReadAllText(metaPath, Encoding.UTF8));
            JsonElement root = meta.RootElement;
            int nTokens = root.GetProperty("n_tokens").GetInt32();
            int nMerges = root.GetProperty("n_merges").GetInt32();

            string mergesSha = Sha256File(mergesPath);
            if (mergesSha != root.GetProperty("merges_txt_sha256").GetString())
            {
                error = $"merges.txt sha256 不符: {mergesSha[..16]}";
                return false;
            }

            string tokensSha = Sha256File(tokensPath);
            if (tokensSha != root.GetProperty("tokens_jsonl_gz_sha256").GetString())
            {
                error = $"tokens.jsonl.gz sha256 不符: {tokensSha[..16]}";
                return false;
            }

            merges = new List<string>(nMerges);
            foreach (string line in File.ReadLines(mergesPath, Encoding.UTF8))
            {
                merges.Add(line);
            }

            if (merges.Count != nMerges)
            {
                error = $"merges 行数不符: {merges.Count} != {nMerges}";
                return false;
            }

            tokens = new List<string>(nTokens);
            types = new List<int>(nTokens);
            using (FileStream fs = File.OpenRead(tokensPath))
            using (GZipStream gz = new(fs, CompressionMode.Decompress))
            using (StreamReader sr = new(gz, Encoding.UTF8))
            {
                string? line;
                while ((line = sr.ReadLine()) != null)
                {
                    if (line.Length == 0)
                    {
                        continue;
                    }

                    using JsonDocument d = JsonDocument.Parse(line);
                    int id = d.RootElement.GetProperty("id").GetInt32();
                    if (id != tokens.Count)
                    {
                        error = $"token id 非连续: 期望 {tokens.Count}, 实得 {id}";
                        return false;
                    }

                    tokens.Add(d.RootElement.GetProperty("t").GetString()!);
                    types.Add(d.RootElement.GetProperty("type").GetInt32());
                }
            }

            if (tokens.Count != nTokens)
            {
                error = $"tokens 条数不符: {tokens.Count} != {nTokens}";
                return false;
            }

            string mer = BpeTokenizer.DigestLines(merges);
            string? wantMer = root.TryGetProperty("merges_sha256", out JsonElement me) ? me.GetString() : null;
            if (wantMer != null && mer != wantMer)
            {
                error = $"合并表摘要不符 (与 GGUF 来源): {mer[..16]} != {wantMer[..16]}";
                return false;
            }

            provenance = $"tables={dir} tokens={tokens.Count} merges={merges.Count} " +
                         $"tokens_sha256={BpeTokenizer.DigestLines(tokens)[..16]} merges_sha256={mer[..16]} " +
                         $"source_gguf={root.GetProperty("source_gguf_sha256").GetString()![..16]}";
            return true;
        }
        catch (Exception ex)
        {
            error = $"{ex.GetType().Name}: {ex.Message}";
            return false;
        }
    }

    private static string Sha256File(string path)
    {
        using FileStream fs = File.OpenRead(path);
        return Convert.ToHexStringLower(SHA256.HashData(fs));
    }
}
