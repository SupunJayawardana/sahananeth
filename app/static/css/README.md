# Tailwind CSS build (offline-safe)

`tailwind.css` in this folder is a **compiled, static** file — it is committed/shipped
with the app and does **not** require an internet connection to work. It replaces the
old `<script src="https://cdn.tailwindcss.com">` approach, which generated all styling
live in the browser and broke completely with no internet connection.

## Files
- `input.css` — source file: Tailwind's `@tailwind` directives plus the project's
  custom component classes (`.ledger-card`, `.btn-primary`, `.status-pill`, etc.)
- `tailwind.css` — the **built** output. This is what `base.html` actually links to.
- `../../../tailwind.config.js` (project root) — theme customisation (brand colors,
  font stacks). Mirrors what used to be the inline `tailwind.config = {...}` script.

## When you need to rebuild
Any time you add a new Tailwind utility class to a template that wasn't used before
(e.g. a new `bg-`, `grid-cols-`, `p-` value), you must rebuild `tailwind.css` — the
build only includes CSS for classes it can find by scanning `app/templates/**/*.html`.

```bash
# Install the Tailwind CLI once (requires internet, only for this step):
npm install -D tailwindcss@3

# Rebuild after any template change:
npx tailwindcss -i app/static/css/input.css -o app/static/css/tailwind.css -c tailwind.config.js --minify
```

Rebuilding does **not** require the app itself to be online at runtime — only this
one-time (or per-change) build step needs npm/internet access, typically on a
developer's machine before deploying.

## Fonts
`base.html` still links to Google Fonts (Fraunces / IBM Plex Sans / IBM Plex Mono) as
a progressive enhancement — nicer typography when the device is online. If that
request fails (no internet), the browser automatically falls back to the system fonts
configured in `tailwind.config.js` (`Georgia`, `system-ui`, etc.), so the app still
looks reasonable rather than breaking.

To make the fonts work fully offline too, self-host them:
1. Download the three font families (Fraunces, IBM Plex Sans, IBM Plex Mono) as
   `.woff2` files, e.g. from Google Fonts or fonts.google.com/download.
2. Place them under `app/static/fonts/`.
3. Add `@font-face` rules for each at the top of `input.css`, then rebuild.
4. Remove the two `<link>`/`<preconnect>` tags to `fonts.googleapis.com` in
   `base.html` once self-hosted fonts are in place.
