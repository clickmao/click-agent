using Microsoft.Extensions.Logging;
using agent.core;
using agent.workspace;
using agent.codegen;
using agent.recovery;
using agent.vectormemory;
using agent.memory;
using agent.templates;
using agent.search;
using agent.subagent;
using agent.session;
using agent.userinteraction;
using agent.context;
using agent.rag;
using agent.tendency;
using agent.tokencompression;
using agent.registry;

using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text;

using agent.intent;

namespace agent;


/// <summary>
/// OpenAI LLM 调用器示例
/// </summary>
public class OpenAILLMCaller : ILLMCaller
{
    private readonly HttpClient _httpClient;
    private readonly string _apiKey;
    private readonly string _model;
    
    private readonly string _baseUrl;

    public OpenAILLMCaller(
        HttpClient httpClient,
        string apiKey,
        string model = "gpt-4",
        string baseUrl = "https://api.openai.com/v1")
    {
        _httpClient = httpClient;
        _apiKey = apiKey;
        _model = model;
        _baseUrl = baseUrl.TrimEnd('/');
    }
    
    public async Task<LLMResponse> CallAsync(Prompt prompt, CancellationToken ct = default)
    {
        try
        {
            var messages = new List<OpenAIChatMessage>();
            
            // System
            if (!string.IsNullOrEmpty(prompt.SystemPrompt))
            {
                messages.Add(new OpenAIChatMessage { Role = "system", Content = prompt.SystemPrompt });
            }
            
            // Context as system context
            if (!string.IsNullOrEmpty(prompt.ContextPrompt))
            {
                var contextMessage = $"以下是你可以参考的相关上下文信息，请结合这些信息回答用户问题：\n\n{prompt.ContextPrompt}";
                messages.Add(new OpenAIChatMessage { Role = "system", Content = contextMessage });
            }
            
            // History
            foreach (var msg in prompt.History)
            {
                messages.Add(new OpenAIChatMessage
                {
                    Role = msg.Role == MessageRole.User ? "user" : "assistant",
                    Content = msg.Content
                });
            }
            
            // Current message
            // v0.12.0 A2: 图像附件 → user 消息多段 content (text + image_url × N)
            var userMsg = new OpenAIChatMessage { Role = "user", Content = prompt.UserMessage };
            if (prompt.ImageUrls.Count > 0)
            {
                userMsg.ImageUrls = prompt.ImageUrls
                    .Select(u => u.StartsWith("data:") || u.StartsWith("http", StringComparison.OrdinalIgnoreCase)
                        ? u
                        : VisionChatHelper.ToDataUrl(u))
                    .ToList();
            }
            messages.Add(userMsg);
            
            // v0.11.0 R21: 显式 DTO (source-gen 零反射) + 推理档位 (简单任务 low 档轻思考)
            var requestBody = new OpenAIChatRequest
            {
                Model = _model,
                Messages = messages,
                // v0.11.0 R19 修复: reasoning 模型 (glm/deepseek) 的思维链计入 max_tokens,
                // 2000 曾被 reasoning 吃满 → content 空回复 (C03 实测 2000 tok 全 reasoning)。
                // 上限只是截断保护, 实际输出长度由 System Prompt 输出纪律约束。
                MaxTokens = 8192,
                Temperature = 0.7,
                ReasoningEffort = prompt.ReasoningEffort,
            };
            
            // v0.12.0 A2: 任一消息带图 → 多段形态序列化 (VisionJsonContext, 手写 converter AOT 安全)
            string jsonBody;
            if (messages.Any(m => m.HasImages))
            {
                jsonBody = JsonSerializer.Serialize(requestBody, VisionJsonContext.Default.OpenAIChatRequest);
            }
            else
            {
                jsonBody = JsonSerializer.Serialize(requestBody, LLMJsonContext.Default.OpenAIChatRequest);
            }
            var request = new HttpRequestMessage(HttpMethod.Post, _baseUrl + "/chat/completions");
            request.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", _apiKey);
            request.Content = new StringContent(jsonBody, Encoding.UTF8, "application/json");
            
            var httpResponse = await _httpClient.SendAsync(request, ct);
            var responseJson = await httpResponse.Content.ReadAsStringAsync(ct);
            
            if (!httpResponse.IsSuccessStatusCode)
            {
                return new LLMResponse
                {
                    Success = false,
                    Error = $"API Error: {httpResponse.StatusCode} - {responseJson}"
                };
            }
            
            using var doc = System.Text.Json.JsonDocument.Parse(responseJson);
            var content = doc.RootElement
                .GetProperty("choices")[0]
                .GetProperty("message")
                .GetProperty("content")
                .GetString() ?? "";
            
            var usage = doc.RootElement.GetProperty("usage");
            
            // 提取额外字段
            var responseId = doc.RootElement.TryGetProperty("id", out var idProp) ? idProp.GetString() : null;
            var finishReason = doc.RootElement.TryGetProperty("choices", out var choices) && 
                              choices.GetArrayLength() > 0 &&
                              choices[0].TryGetProperty("finish_reason", out var fr) ? fr.GetString() : null;
            
            return new LLMResponse
            {
                Content = content,
                Success = true,
                Model = _model,
                TokensUsed = usage.TryGetProperty("total_tokens", out var total) ? total.GetInt32() : 0,
                PromptTokens = usage.TryGetProperty("prompt_tokens", out var pt) ? pt.GetInt32() : 0,
                CacheHitTokens = usage.TryGetProperty("prompt_cache_hit_tokens", out var ch) ? ch.GetInt32() : null,
                CacheMissTokens = usage.TryGetProperty("prompt_cache_miss_tokens", out var cm) ? cm.GetInt32() : null,
                CompletionTokens = usage.TryGetProperty("completion_tokens", out var completion) ? completion.GetInt32() : 0,
                ResponseId = responseId,
                FinishReason = finishReason,
                Timestamp = DateTime.UtcNow
            };
        }
        catch (Exception ex)
        {
            return new LLMResponse
            {
                Success = false,
                Error = ex.Message
            };
        }
    }
}
