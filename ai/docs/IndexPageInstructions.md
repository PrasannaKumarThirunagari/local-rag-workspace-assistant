Create a file-system browsing feature for the index page with a clean separation of concerns.

File system service

Define an interface, e.g. IFileSystemService, and a concrete implementation class.
The service must be able to:
Return a folder tree for a given root path.
List files within a selected folder.
Optionally read file content for a selected file.
Dependency injection

Register the service in Program.cs so it can be injected using ASP.NET Core’s DI container.
Controller integration

Inject IFileSystemService into HomeController.
In the Index action, use the service to fetch the initial folder and file data for the view.
If needed, create additional actions (e.g. GetFiles for a folder, GetFileContent for a file) that call the same service.
Index page binding and interactions

Bind the service data to the existing three-pane Tailwind layout on the Index page:
Folder tree pane shows folders.
Files list pane shows files for the selected folder.
File viewer pane shows the selected file’s content.
Add actionable UI elements (e.g. clickable folders and files) so that selecting a folder updates the file list, and selecting a file updates the file viewer.