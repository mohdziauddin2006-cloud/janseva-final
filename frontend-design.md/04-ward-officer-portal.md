# Prompt 4 of 5: Ward Officer Branch Portal (filtered login)

Depends on: Prompt 1 (design system). Requires the auth/routing from Prompt 5
to gate this behind a ward-scoped officer role — build this assuming
`st.session_state["role"] == "ward_officer"` and
`st.session_state["assigned_ward"]` are already set by the time this page
renders. Every query on this page must filter by `assigned_ward` — an officer
should never be able to see or act on another ward's tickets, including by
guessing a URL/ticket ID.

## Who sees this
Local branch officers (e.g. Central Ward, North Ward officer).

## Pages / sections
1. **My Ward Queue**
   - Ticket list filtered to `assigned_ward` only, sorted by SLA deadline
     (closest-to-breach first). Status filter (Pending/In Progress/Disposed).
2. **Ticket Detail / Action**
   - View citizen's original complaint (transcript, photo, location).
   - Report amount spent: numeric input, on submit validate it doesn't exceed
     the ward's allocated budget (call the backend check, don't just trust the
     client-side number).
   - Upload proof-of-work photo (the "after" photo) — show it side-by-side
     with the citizen's original "before" photo once both exist.
   - Mark Disposed: only enabled once both spend-reported AND proof photo are
     present — don't let an officer close a ticket with text alone.
3. **Budget (read-only)**
   - Show the ward's allocated budget and running total spent so far, clearly
     styled as locked/non-editable — e.g. a muted background, a small lock
     icon next to the allocated-amount field, no input box at all for that
     number (rendering it as plain text, not a disabled input, removes any
     ambiguity about whether it's editable).

## Hard constraint
Budget allocation is set exclusively by the Executive Command Center
(Prompt 3). This portal must not expose any control, however indirect, that
changes the allocated amount — only the spent-so-far figure, which comes from
this role's own spend reports.

## Animation notes
- Photo upload: show a skeleton/progress state while uploading to Supabase
  storage, then fade the before/after pair in together once both are ready —
  don't pop them in separately.
- "Mark Disposed" button: stays visually disabled (muted, not clickable) until
  both required fields are filled — no error toast needed if the two
  conditions above make the invalid state impossible to reach.
