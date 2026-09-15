# Prompt 2 of 5: Public Portal (no login)

Depends on: Prompt 1 (design system) must already be applied — import and use
its theme/component helpers, don't redefine styles here.

## Who sees this
Citizens, journalists, auditors. No login wall. This is the transparency
layer — it needs to load fast and feel trustworthy, not flashy.

## Pages
1. **Transparency Board (landing page)**
   - City-wide summary stats at the top: total grievances, % resolved, average
     resolution time vs the 21-day target — as clean stat cards, not a wall of
     numbers.
   - Interactive ward map (use pydeck or folium) color-coded by resolution
     rate per ward — click a ward to filter the rest of the page to it.
   - Savings ledger: a simple table/bar chart per ward showing budget
     allocated vs amount actually spent (from the Ward Officer's reported
     spend) — this is the accountability centerpiece, keep it legible at a
     glance, not buried in a data table.
2. **Grievance Gallery**
   - Grid of resolved tickets, each card showing before/after photos
     side-by-side (or a slider), category, ward, resolution time. Filter by
     ward/category/status. Lazy-load images, skeleton placeholder while
     loading (from the design system).
3. **Ticket Lookup**
   - Single search box: enter a registration number, see its current status
     (Pending/Disposed), department, and — if disposed — the Action Taken
     Report text and photos. This mirrors CPGRAMS' citizen tracking feature.

## Constraints
- Read-only throughout — no forms that write to the database except nothing
  (this whole portal has zero write access).
- Must work with zero authentication — don't gate any of this behind login.
- Mobile-responsive: this is the page a journalist or citizen opens on a
  phone, prioritize it over desktop.

## Animation notes (beyond the global rules in Prompt 1)
- Map: no animated fly-to on load, just render at the default zoom.
- Stat cards: the count-up-from-zero number animation is fine here (it's the
  one place a little polish helps), keep it under 600ms, ease-out.
- Gallery cards: fade-in on scroll into view (simple, one-time, not
  repeating), don't animate the before/after slider itself unless it's the
  user dragging it.
