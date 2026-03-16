using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using AI_File_Explorer_MVC.Models;

namespace AI_File_Explorer_MVC.Services;

public class FileSystemService : IFileSystemService
{
    public FolderNode GetFolderTree(string rootPath, string? selectedFolderPath = null, int maxDepth = 10)
    {
        if (string.IsNullOrWhiteSpace(rootPath))
        {
            throw new ArgumentException("Root path must be provided.", nameof(rootPath));
        }

        selectedFolderPath ??= rootPath;

        return BuildFolderNode(rootPath, selectedFolderPath, maxDepth, 0);
    }

    public List<FileItem> GetFiles(string folderPath)
    {
        var files = new List<FileItem>();

        if (string.IsNullOrWhiteSpace(folderPath) || !Directory.Exists(folderPath))
        {
            return files;
        }

        try
        {
            foreach (var file in Directory.GetFiles(folderPath))
            {
                files.Add(new FileItem
                {
                    Name = Path.GetFileName(file),
                    FullPath = file
                });
            }
        }
        catch (Exception)
        {
            // Intentionally ignore IO/security issues for now.
        }

        return files;
    }

    public string? GetFileContent(string filePath, int maxChars = 8000)
    {
        if (string.IsNullOrWhiteSpace(filePath) || !File.Exists(filePath))
        {
            return null;
        }

        try
        {
            using var reader = new StreamReader(filePath);
            char[] buffer = new char[maxChars];
            int read = reader.Read(buffer, 0, maxChars);
            return new string(buffer, 0, read);
        }
        catch (Exception)
        {
            return "Unable to read file content.";
        }
    }

    public List<(string filePath, int lineNumber, string lineText)> SearchFileContent(
        string rootPath,
        string query,
        int maxResults = 50)
    {
        var results = new List<(string filePath, int lineNumber, string lineText)>();

        if (string.IsNullOrWhiteSpace(rootPath) || !Directory.Exists(rootPath))
        {
            return results;
        }

        query = query.Trim();
        if (query.Length == 0)
        {
            return results;
        }

        IEnumerable<string> files;
        try
        {
            files = Directory.EnumerateFiles(rootPath, "*.*", SearchOption.AllDirectories);
        }
        catch (Exception)
        {
            return results;
        }

        foreach (var file in files)
        {
            if (results.Count >= maxResults)
            {
                break;
            }

            if (ShouldSkipPath(file))
            {
                continue;
            }

            try
            {
                var info = new FileInfo(file);
                if (!info.Exists || info.Length > 1_000_000)
                {
                    continue;
                }

                using var reader = new StreamReader(file);
                int lineNumber = 0;
                while (!reader.EndOfStream && results.Count < maxResults)
                {
                    var line = reader.ReadLine();
                    lineNumber++;
                    if (line is null)
                    {
                        continue;
                    }

                    if (line.IndexOf(query, StringComparison.OrdinalIgnoreCase) >= 0)
                    {
                        results.Add((file, lineNumber, Truncate(line, 220)));
                        break; // one hit per file is enough for UI
                    }
                }
            }
            catch (Exception)
            {
                // Ignore unreadable/binary/locked files.
            }
        }

        return results;
    }

    private static FolderNode BuildFolderNode(string path, string selectedFolderPath, int maxDepth, int currentDepth)
    {
        var node = new FolderNode
        {
            Name = Path.GetFileName(path).Length == 0 ? path : Path.GetFileName(path),
            FullPath = path,
            IsSelected = string.Equals(
                NormalizePath(path),
                NormalizePath(selectedFolderPath),
                StringComparison.OrdinalIgnoreCase)
        };

        if (currentDepth >= maxDepth)
        {
            return node;
        }

        try
        {
            foreach (var directory in Directory.GetDirectories(path).OrderBy(d => d))
            {
                node.Children.Add(BuildFolderNode(directory, selectedFolderPath, maxDepth, currentDepth + 1));
            }
        }
        catch (Exception)
        {
            // Ignore IO/security issues for child enumeration.
        }

        return node;
    }

    private static string NormalizePath(string path) =>
        Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);

    private static bool ShouldSkipPath(string path)
    {
        var p = path.Replace(Path.AltDirectorySeparatorChar, Path.DirectorySeparatorChar);
        return p.Contains($"{Path.DirectorySeparatorChar}bin{Path.DirectorySeparatorChar}", StringComparison.OrdinalIgnoreCase)
               || p.Contains($"{Path.DirectorySeparatorChar}obj{Path.DirectorySeparatorChar}", StringComparison.OrdinalIgnoreCase)
               || p.Contains($"{Path.DirectorySeparatorChar}.git{Path.DirectorySeparatorChar}", StringComparison.OrdinalIgnoreCase)
               || p.Contains($"{Path.DirectorySeparatorChar}node_modules{Path.DirectorySeparatorChar}", StringComparison.OrdinalIgnoreCase)
               || p.EndsWith(".dll", StringComparison.OrdinalIgnoreCase)
               || p.EndsWith(".exe", StringComparison.OrdinalIgnoreCase)
               || p.EndsWith(".pdb", StringComparison.OrdinalIgnoreCase);
    }

    private static string Truncate(string s, int max)
    {
        if (s.Length <= max) return s;
        return s[..max] + "…";
    }
}

