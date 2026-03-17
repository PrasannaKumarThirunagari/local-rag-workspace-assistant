namespace AI_File_Explorer_MVC.Services;

public interface IRagService
{
    Task<string?> AskAsync(string question, string? pathFilter = null, int topK = 8, CancellationToken ct = default);
}
