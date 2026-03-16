using System.Collections.Generic;
using AI_File_Explorer_MVC.Models;

namespace AI_File_Explorer_MVC.Services;

public interface IFileSystemService
{
    FolderNode GetFolderTree(string rootPath, string? selectedFolderPath = null, int maxDepth = 10);

    List<FileItem> GetFiles(string folderPath);

    string? GetFileContent(string filePath, int maxChars = 8000);

    List<(string filePath, int lineNumber, string lineText)> SearchFileContent(
        string rootPath,
        string query,
        int maxResults = 50);
}

