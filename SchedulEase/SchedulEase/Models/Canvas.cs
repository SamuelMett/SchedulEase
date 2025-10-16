using SchedulEase.Models;

namespace SchedulEase.Models;

public class CanvasCourse
{
    public string Id { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Code { get; set; } = string.Empty;
    public string Term { get; set; } = string.Empty;
    public int AssignmentCount { get; set; }
}

public class CanvasAssignment
{
    public string Id { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public DateOnly Date { get; set; }
    public string? Time { get; set; }
    public string? Description { get; set; }
    public CalendarEventType Type { get; set; }
    public string CourseCode { get; set; } = string.Empty;
    public string CourseName { get; set; } = string.Empty;
}