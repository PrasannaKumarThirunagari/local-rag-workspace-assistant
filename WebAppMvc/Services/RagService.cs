using System.Net.Http.Json;
using System.Text.Json;

namespace AI_File_Explorer_MVC.Services;

public class RagService : IRagService
{
    private readonly HttpClient _http;
    private readonly ILogger<RagService> _logger;
    private readonly string _baseUrl;

    public RagService(HttpClient http, IConfiguration config, ILogger<RagService> logger)
    {
        _http = http;
        _logger = logger;
        _baseUrl = config["Rag:BaseUrl"] ?? "http://localhost:8000";
        _http.BaseAddress = new Uri(_baseUrl.TrimEnd('/') + "/");
        _http.Timeout = TimeSpan.FromSeconds(120);
    }

    public async Task<string?> AskAsync(string question, string? pathFilter = null, int topK = 8, CancellationToken ct = default)
    {
        if (string.IsNullOrWhiteSpace(question))
            return null;

        try
        {
            var body = new { question = question.Trim(), top_k = topK, path_filter = pathFilter };
            var res = await _http.PostAsJsonAsync("api/ask", body, ct);
            res.EnsureSuccessStatusCode();
            var json = await res.Content.ReadFromJsonAsync<JsonElement>(ct);
            return json.TryGetProperty("answer", out var a) ? a.GetString() : null;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "RAG ask failed: {Message}", ex.Message);
            return null;
        }
    }
}
