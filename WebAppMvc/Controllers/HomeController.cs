using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using Microsoft.AspNetCore.Mvc;
using WebAppMvc.Models;
using WebAppMvc.Services;

namespace WebAppMvc.Controllers;

public class HomeController : Controller
{
    private readonly ILogger<HomeController> _logger;
    private readonly IFileSystemService _fileSystemService;
    private readonly string _rootPath;

    public HomeController(
        ILogger<HomeController> logger,
        IFileSystemService fileSystemService,
        IWebHostEnvironment environment)
    {
        _logger = logger;
        _fileSystemService = fileSystemService;

        // Use the solution directory (parent of the WebAppMvc project) as the root.
        var contentRoot = environment.ContentRootPath;
        _rootPath = Directory.GetParent(contentRoot)?.FullName ?? contentRoot;
    }

    public IActionResult Index(string? folderPath = null, string? filePath = null)
    {
        var effectiveRoot = _rootPath;

        folderPath ??= effectiveRoot;
        folderPath = EnsureWithinRoot(folderPath, effectiveRoot);

        if (!string.IsNullOrWhiteSpace(filePath))
        {
            filePath = EnsureWithinRoot(filePath, effectiveRoot);
        }

        // Increase maxDepth so deeper subfolders are visible in the tree.
        var folderTree = _fileSystemService.GetFolderTree(effectiveRoot, folderPath, maxDepth: 15);
        var files = _fileSystemService.GetFiles(folderPath);
        var fileContent = string.IsNullOrWhiteSpace(filePath)
            ? null
            : _fileSystemService.GetFileContent(filePath);

        var viewModel = new FileExplorerViewModel
        {
            RootPath = effectiveRoot,
            SelectedFolderPath = folderPath,
            SelectedFilePath = filePath,
            RootFolder = folderTree,
            Files = files,
            FileContent = fileContent
        };

        return View(viewModel);
    }

    public IActionResult Privacy()
    {
        return View();
    }

    [HttpGet]
    public IActionResult Search(string q)
    {
        var effectiveRoot = _rootPath;
        q = (q ?? string.Empty).Trim();

        if (q.Length < 2)
        {
            return Json(new { query = q, folders = Array.Empty<string>(), matches = Array.Empty<object>() });
        }

        var hits = _fileSystemService.SearchFileContent(effectiveRoot, q, maxResults: 60);

        var folders = hits
            .Select(h => Path.GetDirectoryName(h.filePath) ?? string.Empty)
            .Where(p => !string.IsNullOrWhiteSpace(p))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .Take(60)
            .ToArray();

        var matches = hits.Select(h => new
        {
            filePath = h.filePath,
            fileName = Path.GetFileName(h.filePath),
            folderPath = Path.GetDirectoryName(h.filePath),
            lineNumber = h.lineNumber,
            lineText = h.lineText
        });

        return Json(new { query = q, folders, matches });
    }

    [HttpGet]
    public IActionResult FolderData(string? folderPath)
    {
        var effectiveRoot = _rootPath;
        folderPath ??= effectiveRoot;
        folderPath = EnsureWithinRoot(folderPath, effectiveRoot);

        var files = _fileSystemService.GetFiles(folderPath);

        var payload = new
        {
            folderPath,
            files = files.Select(f => new
            {
                name = f.Name,
                fullPath = f.FullPath,
                directory = Path.GetDirectoryName(f.FullPath)
            })
        };

        return Json(payload);
    }

    [HttpGet]
    public IActionResult FileContent(string filePath)
    {
        var effectiveRoot = _rootPath;
        filePath = EnsureWithinRoot(filePath, effectiveRoot);

        var content = _fileSystemService.GetFileContent(filePath);

        var payload = new
        {
            filePath,
            fileName = Path.GetFileName(filePath),
            content
        };

        return Json(payload);
    }

    [ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
    public IActionResult Error()
    {
        return View(new ErrorViewModel { RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier });
    }

    private static string EnsureWithinRoot(string path, string rootPath)
    {
        try
        {
            var normalizedRoot = Path.GetFullPath(rootPath);
            var normalizedPath = Path.GetFullPath(path);

            if (!normalizedPath.StartsWith(normalizedRoot, StringComparison.OrdinalIgnoreCase))
            {
                return normalizedRoot;
            }

            return normalizedPath;
        }
        catch
        {
            return rootPath;
        }
    }
}

