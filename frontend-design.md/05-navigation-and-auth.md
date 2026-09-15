# Prompt 5 of 5: Navigation Shell & Role-Based Auth

Depends on: Prompt 1 (design system). This is the glue that connects Prompts
2, 3, and 4 — build this alongside or right after them, since it's what
decides which of those three portals a given visitor actually sees.

## Goal
One app, three distinct experiences, routed by role — using Streamlit's
`st.navigation` / `st.Page` (not the older `pages/` folder convention, which
can't do conditional per-role page lists).

## Structure
- **Public**: no login, always visible — Prompt 2's pages (Transparency
  Board, Gallery, Ticket Lookup).
- **Login page**: a single, simple login form (not tabbed by role — the
  backend determines role from credentials, the UI doesn't ask "which type of
  user are you"). On success, set `st.session_state["role"]` and, for ward
  officers, `st.session_state["assigned_ward"]`.
- **After login**: build the `st.Page` list conditionally —
  - `role == "admin"` → Prompt 3's pages only.
  - `role == "ward_officer"` → Prompt 4's pages only.
  - Public pages remain accessible to everyone regardless of role.
- **Logout**: clears session_state and returns to the public landing page.

## Nav chrome
- Simple top bar or slim sidebar (pick sidebar — plays nicer with Streamlit's
  layout model): org name/logo, current page links (only the ones the current
  role can see), theme toggle (sun/moon, from Prompt 1) always visible, login/
  logout control.
- Ward Officer portal should visibly show which ward they're scoped to (e.g.
  "North Ward" badge next to their name) — a constant visual reminder they're
  in a filtered view, not the full system.
- Collapse the sidebar to a hamburger/icon-only state below ~768px width.

## Security note to build in, not just visual
Role-based page hiding in the nav is a UX nicety, not the actual security
boundary — every data query in Prompts 3 and 4 must independently check
`st.session_state["role"]` (and `assigned_ward` for officers) before returning
data, so that directly navigating to a page URL without the right role/session
can't leak data even if the nav link was never shown.

## Animation notes
- Login: on success, fade out the login form and fade in the destination page
  — don't hard-cut.
- Sidebar collapse/expand: 200ms width transition, matches the global
  animation timing from Prompt 1.
