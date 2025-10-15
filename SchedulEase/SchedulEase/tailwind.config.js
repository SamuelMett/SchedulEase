/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: 'class',
    content: [
        './**/*.razor',  // Scans all your Blazor component files
        './**/*.html'   // Scans your App.razor or index.html
    ],
    theme: {
        extend: {},
    },
    plugins: [],
}