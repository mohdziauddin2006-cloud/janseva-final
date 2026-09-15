# Prompt 1 of 5: Design System Foundation (do this one FIRST)

App: JanSeva civic grievance platform (Streamlit, live at janseva-final.onrender.com).
This prompt only builds the shared design system — no page content yet. Every
other prompt depends on this one being done first.

## Goal
A professional, restrained visual language. Reference point: modern civic-tech
/ fintech dashboards (think Linear, Notion, a well-designed government digital
service like UK's GOV.UK or Singapore's LifeSG) — NOT the cluttered, dense,
primary-color-everywhere look of typical Indian government portals. Whitespace,
restraint, one accent color used sparingly for actions/status, not decoration.

## Color & theme tokens
- Define CSS custom properties for both light and dark themes: background
  (base + elevated/card surface), text (primary + muted), border, and a single
  accent color used for primary actions and status. Avoid the tricolor/saffron
  cliché — go with a deep blue or teal accent instead, feels civic without
  being kitsch.
- Status colors (used sparingly, only on badges/indicators, not backgrounds):
  green (Disposed), amber (Pending), red (Emergency/Poor rating appeal).
- Implement the toggle: a session_state flag `theme` ("light"/"dark"),
  persisted across reloads via `st.query_params` (not just session_state, which
  resets on refresh). Inject the corresponding CSS variable block via
  `st.markdown(..., unsafe_allow_html=True)` at the top of every page. Provide
  a small sun/moon icon toggle button, not a text-heavy control.

## Typography
- One clean sans-serif (Inter or similar via Google Fonts import), two weights
  max (regular + semibold). Clear type scale: page title, section header, body,
  caption. No default Streamlit heading styles — override them.

## Component primitives (build these once, reuse everywhere)
- Card: subtle border + elevated surface color, 8–12px radius, gentle shadow
  only in light mode (avoid shadows looking muddy in dark mode — use a
  1px border instead there).
- Status badge: small pill, colored per status token above.
- Button: primary (accent fill), secondary (outline), both with a subtle
  hover state — background lightens/darkens ~8%, no scale/bounce.
- Skeleton loader: for anything that fetches from Supabase, show a pulsing
  skeleton block instead of Streamlit's default spinner.

## Animation rules (apply globally, keep it restrained)
- Page/card content: fade + 8px upward slide on load, 200–250ms ease-out.
  Nothing longer than 300ms anywhere.
- Hover states: background/border color transition only, 150ms. No scale
  transforms, no shadows popping in, no bounce/elastic easing.
- Theme toggle: the color transition on switching light/dark should itself be
  a smooth 200ms transition on the CSS variables, not an instant snap.
- Explicitly avoid: spinning loaders, confetti/celebration effects, parallax,
  anything that moves on scroll.

## Output
A `theme.py` (or `assets/theme.css` + a small injector function) that every
other page imports, plus the reusable component helper functions (card,
badge, button wrapper) other prompts will call. Don't build any actual page
content in this prompt — just the system.
