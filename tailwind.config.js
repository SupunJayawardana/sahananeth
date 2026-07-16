/** Tailwind config — compiled locally so the app no longer depends on
 *  the cdn.tailwindcss.com script at runtime (see app/static/css/README.md).
 *  This mirrors the inline `tailwind.config` that used to live in base.html.
 */
module.exports = {
  content: [
    "./app/templates/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        ink: '#14213D',
        slate: '#46566B',
        civic: '#2456A6',
        amber: '#D98A2B',
        relief: '#1F7A6C',
        rust: '#B5432E',
        paper: '#F2F4F3',
        line: '#DCE1E0',
      },
      fontFamily: {
        // Google-Fonts name first (used when online), with sane
        // offline-safe fallbacks so the app still looks reasonable
        // with no internet connection.
        display: ['"Fraunces"', 'Georgia', 'serif'],
        sans: ['"IBM Plex Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
    }
  },
  plugins: [],
}
