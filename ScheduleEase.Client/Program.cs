using Microsoft.AspNetCore.Components.Web;
using Microsoft.AspNetCore.Components.WebAssembly.Hosting;
using Microsoft.AspNetCore.Components.WebAssembly.Http; // Required for SetBrowser...
using ScheduleEase.Client;
using Radzen; // Add this
using Microsoft.Extensions.Http;

var builder = WebAssemblyHostBuilder.CreateDefault(args);
builder.RootComponents.Add<App>("#app");
builder.RootComponents.Add<HeadOutlet>("head::after");

// Register the CookieHandler
builder.Services.AddTransient<CookieHandler>();

// Register the HttpClient, set the BaseAddress, and attach the CookieHandler
builder.Services.AddHttpClient("API", client =>
{
    // This is the base URL of your Python backend
    client.BaseAddress = new Uri("http://127.0.0.1:8000");
})
.AddHttpMessageHandler<CookieHandler>();

// Make the named "API" HttpClient available as the default injected HttpClient
builder.Services.AddScoped(sp => sp.GetRequiredService<IHttpClientFactory>().CreateClient("API"));

// Add Radzen Services
builder.Services.AddScoped<DialogService>();
builder.Services.AddScoped<NotificationService>();
builder.Services.AddScoped<TooltipService>();
builder.Services.AddScoped<ContextMenuService>();

await builder.Build().RunAsync();