using System.Collections.Generic;

namespace WebAppMvc.Models;

public class FolderNode
{
    public string Name { get; set; } = string.Empty;
    public string FullPath { get; set; } = string.Empty;
    public bool IsSelected { get; set; }
    public List<FolderNode> Children { get; set; } = new();
}

public class FileItem
{
    public string Name { get; set; } = string.Empty;
    public string FullPath { get; set; } = string.Empty;
}

public class FileExplorerViewModel
{
    public string RootPath { get; set; } = string.Empty;
    public string? SelectedFolderPath { get; set; }
    public string? SelectedFilePath { get; set; }
    public FolderNode RootFolder { get; set; } = new();
    public List<FileItem> Files { get; set; } = new();
    public string? FileContent { get; set; }
}

