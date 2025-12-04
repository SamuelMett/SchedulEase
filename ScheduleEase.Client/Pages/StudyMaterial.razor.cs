using Microsoft.AspNetCore.Components;
using Microsoft.AspNetCore.Components.WebAssembly.Http;
using Microsoft.JSInterop;
using ScheduleEase.Client.Models;
using Radzen;
using System.Net.Http.Json;

namespace ScheduleEase.Client.Pages
{
    public partial class StudyMaterial
    {
        [Inject]
        private HttpClient Http { get; set; }

        [Inject]
        private IJSRuntime JSRuntime { get; set; }

        protected IEnumerable<GoogleCalendarEvent> events;
        protected string errorMessage;
        protected bool isGenerating = false;
        protected GoogleCalendarEvent selectedEvent;
        protected Models.StudyMaterial generatedMaterial;

        protected override async Task OnInitializedAsync()
        {
            await LoadEvents();
        }

        private async Task LoadEvents()
        {
            try
            {
                var request = new HttpRequestMessage(HttpMethod.Get, "http://127.0.0.1:8000/calendar/events");
                request.SetBrowserRequestCredentials(BrowserRequestCredentials.Include);

                var response = await Http.SendAsync(request);

                if (response.IsSuccessStatusCode)
                {
                    events = await response.Content.ReadFromJsonAsync<List<GoogleCalendarEvent>>();
                }
                else
                {
                    errorMessage = $"Error loading events: {response.ReasonPhrase}. Please ensure you are logged in.";
                }
            }
            catch (Exception ex)
            {
                errorMessage = $"Error loading events: {ex.Message}. Is the backend running?";
            }
        }

        private async Task GenerateStudyMaterial(GoogleCalendarEvent calendarEvent)
        {
            try
            {
                isGenerating = true;
                selectedEvent = calendarEvent;
                generatedMaterial = null;
                errorMessage = null;
                StateHasChanged();

                var requestData = new GenerateStudyMaterialRequest
                {
                    EventTitle = calendarEvent.Title,
                    EventStart = calendarEvent.Start,
                    EventEnd = calendarEvent.End
                };

                var request = new HttpRequestMessage(HttpMethod.Post, "http://127.0.0.1:8000/api/study-material/generate")
                {
                    Content = JsonContent.Create(requestData)
                };
                request.SetBrowserRequestCredentials(BrowserRequestCredentials.Include);

                var response = await Http.SendAsync(request);

                if (response.IsSuccessStatusCode)
                {
                    generatedMaterial = await response.Content.ReadFromJsonAsync<Models.StudyMaterial>();
                    
                    NotificationService.Notify(new NotificationMessage
                    {
                        Severity = NotificationSeverity.Success,
                        Summary = "Success",
                        Detail = "Study material generated successfully!",
                        Duration = 4000
                    });
                }
                else
                {
                    errorMessage = $"Failed to generate study material: {response.ReasonPhrase}";
                    
                    NotificationService.Notify(new NotificationMessage
                    {
                        Severity = NotificationSeverity.Error,
                        Summary = "Generation Failed",
                        Detail = errorMessage,
                        Duration = 4000
                    });
                }
            }
            catch (Exception ex)
            {
                errorMessage = $"Error generating study material: {ex.Message}";
                
                NotificationService.Notify(new NotificationMessage
                {
                    Severity = NotificationSeverity.Error,
                    Summary = "Error",
                    Detail = errorMessage,
                    Duration = 4000
                });
            }
            finally
            {
                isGenerating = false;
                selectedEvent = null;
                StateHasChanged();
            }
        }

        private async Task CopyToClipboard()
        {
            if (generatedMaterial != null)
            {
                await JSRuntime.InvokeVoidAsync("navigator.clipboard.writeText", generatedMaterial.Content);
                
                NotificationService.Notify(new NotificationMessage
                {
                    Severity = NotificationSeverity.Info,
                    Summary = "Copied",
                    Detail = "Study material copied to clipboard!",
                    Duration = 2000
                });
            }
        }
    }
}