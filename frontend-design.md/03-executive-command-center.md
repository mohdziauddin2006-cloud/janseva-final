# Prompt 3 of 5: Executive Command Center (master login)

Depends on: Prompt 1 (design system). Requires the auth/routing from Prompt 5
to gate this behind the Commissioner/Admin role — build this assuming
`st.session_state["role"] == "admin"` is already guaranteed by the time this
page renders.

## Who sees this
Zonal Commissioners, Central Government admin. This is oversight and control,
not fieldwork.

## Pages / sections
1. **All-Wards Ticket Overview**
   - Full table of every citizen-submitted ticket, across all wards, with
     server-side filter/sort by ward, category, status, SLA-deadline
     proximity (flag anything close to breaching the 21-day target).
   - Row-level action: **Verify** a newly-lodged complaint before it's
     released to a ward officer's queue (approve / reject-as-duplicate-or-
     invalid). This is the one write action this role has on individual
     tickets.
2. **Budget Allocation**
   - Per-ward budget input (this role sets the number that Ward Officer
     portals later display as read-only). Simple form: select ward, set/edit
     allocated amount, save. Show allocation history (who changed it, when).
3. **Ward Assignment**
   - Reassign a ticket to a different ward/officer if the AI's geofencing
     routed it wrong. Simple dropdown + confirm, not a drag-and-drop board.
4. **Analytics Overview**
   - Resolution-rate trend over time, ward leaderboard (fastest/slowest
     average resolution), category breakdown. Charts, not raw tables.

## Hard constraint — enforce this in the UI, not just the backend
This role must **never** see a "Mark Resolved" or "Upload Proof Photo" control
anywhere in this portal. Don't grey these out or hide-with-CSS — literally
don't render them for this role. Resolution and proof-of-work belong
exclusively to the Ward Officer portal (Prompt 4). If you're tempted to add a
"resolve on behalf of officer" override for convenience, don't — that
constraint is intentional, flag it back to me in your output notes instead of
building around it.

## Animation notes
- Table interactions (sort/filter) should update without a full page flash —
  use Streamlit's native rerun behavior but keep the design system's fade-in
  on the refreshed rows.
- Budget save action: a brief inline success state (checkmark + "Saved", fades
  after ~1.5s), no modal/toast that blocks the screen.
