# Cooperative Redesign Implementation Plan

## Overview
Complete frontend visual/interaction layer rebuild for the Milking Monitor Platform. Keeps all routes, components, API contracts, DB schema, and data-flow intact. Replaces the current navy/teal/mint aesthetic with a calm, minimal, premium-cooperative design: deep forest green sidebar, cream canvas, Schibsted Grotesk single typeface, and the Seal Ring as the signature component.

## Design Tokens Summary

| Token | Current | New |
|---|---|---|
| Canvas | `#f7f8fa` | `#F7F5EF` |
| Surface | `#ffffff` | `#FFFFFF` |
| Sidebar | `#0f1729` (navy) | `#1F4D3A` (forest green) |
| Sidebar text | `#c7cdd9` | `#D8E6DC` |
| Active nav | `#3ee8b5` bg fill | `rgba(255,255,255,0.14)` fill |
| Text primary | `#111827` | `#20261F` |
| Text secondary | `#6b7280` | `#5C6B5D` |
| Text muted | `#9ca3af` | `#8B968B` |
| Border | `#e5e7eb` | `#E4E0D2` |
| Accent | `#0f7a52` | `#1F4D3A` |
| Accent soft | `#e6f7f0` | `#E3ECE5` |
| Warning | `#f59e0b` | `#C98A2B` |
| Danger | `#ba1a1a` | `#B4432E` |
| Radius card | 16px | 12px |
| Radius button | 10px | 8px |
| Font family | Manrope + Inter | Schibsted Grotesk only |

## Implementation Phases

### Phase 1: Foundation (globals.css)
**File:** `apps/web/app/globals.css`
- Replace ALL CSS custom properties with new design tokens
- Add Google Fonts import for Schibsted Grotesk (weights 400, 500, 600, 700)
- Rewrite `.card` to use `border: 1px solid #E4E0D2` instead of shadow
- Add `.accent-panel` class (green bg, cream text, no border-radius change)
- Rewrite `.status-pill` → `.status-tag` with pill-radius and new color variants
- Rewrite `.button` variants: primary (green fill), secondary (white fill), danger (terracotta outline)
- Rewrite `.input`/`.select` with pill-radius and soft focus ring
- Rewrite `.metric` to use Schibsted Grotesk 700 with `tabular-nums`
- Rewrite `.label` to uppercase Schibsted Grotesk 600
- Rewrite `.section-title` to 15px 600 weight
- Rewrite `.live-dot` to breathing animation (1→0.6→1 over 2.4s)
- Rewrite `.video-frame` to flat neutral placeholder (no stripes)
- Add `.seal-ring` SVG styles
- Add page load animation: staggered fade-up (320ms, 40ms stagger)
- Remove `.dark-panel` (replaced by `.accent-panel`)
- Remove `.donut` / `.donut-inner` (replaced by SealRing component)
- Update responsive breakpoint rules

### Phase 2: New Components
**Files to create:**

1. `apps/web/components/ui/seal-ring.tsx` — SVG circular progress ring
   - Props: `value: number`, `size?: number`, `label?: string`, `variant?: 'success'|'warning'|'danger'`
   - Flat SVG with `stroke-dasharray` arc, no needle/tick marks
   - Animated fill from 0 to value on mount (700ms ease-out)
   - Metric value centered inside in tabular-nums
   - Small status label beneath

2. `apps/web/components/ui/status-tag.tsx` — Replaces status-pill
   - Props: `variant: 'success'|'warning'|'danger'|'neutral'`, `children`, `pulse?: boolean`

### Phase 3: Layout Components

**File:** `apps/web/components/layout/dashboard-shell.tsx`
- Update sidebar: green background (#1F4D3A), soft rounded nav items (8px radius), no letter icons (remove icon field from navItems)
- Nav item active: `rgba(255,255,255,0.14)` fill, white text, font-weight 600
- New Session button: cream-outlined on green sidebar, 999px radius
- Profile card: transparent bg, round avatar (999px), white name
- Topbar: white bg, no backdrop blur, simpler border
- Page title: 26px, normal case (not uppercase)
- Subtitle: 13px, secondary color (no live clock)
- Search: pill-radius (999px), canvas background
- Icon buttons: pill-radius (999px)
- Emergency Stop: plain terracotta outlined button, word "Stop"
- Update `pageTitle()` mapping to canonical routes

### Phase 4: Auth Pages

**File:** `apps/web/app/sign-in/[[...sign-in]]/page.tsx`
- Left pane: white bg, leaf/drop brand mark (32x32, radius 8px, bg rgba(255,255,255,0.12) on green, or cream bg on white), "Welcome back" title (32px, sentence case), shorter subtitle, `EmailSignInForm`, "Create one" link
- Right pane: accent-panel (deep green), photo.png at 0.25 opacity blended into green, headline "Every session, verified." (40px, cream, no text-shadow), small SealRing card floating bottom-left

**File:** `apps/web/app/sign-up/[[...sign-up]]/page.tsx`
- Same split, "Create your account" title, "Built for the whole cooperative." headline

**File:** `apps/web/components/auth/email-sign-in-form.tsx`
- Pill-radius inputs, standard bordered style, button "Sign in" / "Signing in..."

**File:** `apps/web/components/auth/email-sign-up-form.tsx`
- Same pill-radius inputs, button "Create account" / "Creating account..."

### Phase 5: Dashboard Pages

**File:** `apps/web/app/(dashboard)/page.tsx` (Overview)
- Hero: accent-panel card, StatusTag + live-dot, 32px session title, SealRing for compliance score
- Metrics: grid-3, plain .metric numbers (no rings here)
- Main grid: dashboard-grid, 2 position cards with video-frame + ROI + 6 plain check rows
- Sidebar: alert-items rail-list, secondary "Open Live View" button

**File:** `apps/web/app/(dashboard)/live/page.tsx` (Live)
- LiveSessionBanner: accent-panel, breathing live-dot, tabular-nums timer
- grid-2 position cards with video-frame + task rows with StatusTag
- LiveSessionStream: plain readable event rows, not raw JSON
- TaskChecklist with secondary Override buttons
- Sidebar: alerts + small SealRing at bottom

**File:** `apps/web/app/(dashboard)/analytics/page.tsx` (Analytics)
- Absorbs /statistics and /reports
- Top: reporting period selector + ReportGenerator button
- Compliance Score: large SealRing + side stats
- Missed Task Frequency: plain horizontal bar list
- Efficiency: horizontal progress bars with benchmark tick
- Human Factors: employee table with small SealRing chips (32px)
- Insight panel: accent-panel with calm copy + cream secondary button

**File:** `apps/web/app/(dashboard)/logs/page.tsx` (Logs)
- Absorbs /alerts via severity column
- Filter row: pill toggle buttons (All/Critical/Warning) with functional state
- Table with StatusTag severity

**File:** `apps/web/app/(dashboard)/equipment/page.tsx` (Equipment)
- StatusTag rows for 4 services
- Configuration data-rows

**File:** `apps/web/app/(dashboard)/scheduler/page.tsx` (Scheduler)
- Simple table with StatusTag

**File:** `apps/web/app/(dashboard)/scheduler/new/page.tsx` (New Session)
- MultiStepSessionForm with numbered circle step indicator

**File:** `apps/web/app/(dashboard)/settings/page.tsx` (Settings)
- Plain range slider (green track/thumb)
- StatusTag rows for notification/escalation status

**File:** `apps/web/app/(dashboard)/sessions/[sessionId]/page.tsx` (Session Detail)
- Session info + StatusTag + SessionActions
- Absorbs /recommendations as Clinical Guidance panel (StatusTag + copy)
- Audit trail

**File:** `apps/web/app/(dashboard)/sessions/[sessionId]/live/page.tsx`
- Same structure, re-themed

### Phase 6: Dashboard Components

**File:** `apps/web/components/dashboard/live-session-banner.tsx`
- Convert to client component (needs timer)
- accent-panel bg, breathing live-dot, tabular-nums MM:SS timer

**File:** `apps/web/components/dashboard/live-session-stream.tsx`
- Plain readable event rows instead of raw `<pre>` JSON
- Small dot (success/danger) + "Connected"/"Reconnecting"

**File:** `apps/web/components/dashboard/task-checklist.tsx`
- Plain data-rows with StatusTag
- Override as secondary button

**File:** `apps/web/components/dashboard/override-modal.tsx`
- **FIX:** True centered dialog with backdrop, focus trap, Escape-to-close
- White card, 12px radius, elevated shadow
- Pill-radius select and textarea inputs

**File:** `apps/web/components/dashboard/session-actions.tsx`
- Plain pill-radius input

**File:** `apps/web/components/dashboard/equipment-status.tsx`
- StatusTag rows instead of pill variants

**File:** `apps/web/components/forms/multi-step-session-form/index.tsx`
- Keep numbered circle step indicators (already clean)
- Fill active circle in accent green
- Pill-radius inputs

**File:** `apps/web/components/reports/report-generator.tsx`
- Plain primary button, no special styling

### Phase 7: Route Consolidation

- `app/(dashboard)/sessions/new/page.tsx` → redirect to `/scheduler/new` (307)
- Remove standalone pages: `/monitoring`, `/alerts`, `/recommendations`, `/reports`, `/statistics` from nav (keep files but don't link from sidebar)
- The sidebar nav stays at 7 canonical items: Overview, Live, Unit Logs, Equipment, Analytics, Scheduler, Settings

### Phase 8: Cleanup

- Delete dead code: `components/forms/multi-step-session-form/step-1.tsx` through `step-4.tsx`
- Delete unused: `components/statistics/charts/index.tsx`
- Update `frontend.json` to match new design

## Verification

1. Run `npx tsc --noEmit` in `apps/web` — zero errors
2. Run `npm run build` in `apps/web` — no build errors
3. Visual check: all 7 canonical nav items work, active state highlights correctly
4. OverrideModal opens as a centered dialog with backdrop, closes on Escape
5. SealRing renders with animated fill on dashboard and analytics pages
6. Auth pages show split-screen with green right pane and photo.png blended
7. All status indicators use the new StatusTag styling
8. Responsive layout works below 980px breakpoint

## Files to Modify (in order)
1. `apps/web/app/globals.css`
2. `apps/web/components/ui/seal-ring.tsx` (NEW)
3. `apps/web/components/ui/status-tag.tsx` (NEW)
4. `apps/web/components/layout/dashboard-shell.tsx`
5. `apps/web/app/sign-in/[[...sign-in]]/page.tsx`
6. `apps/web/app/sign-up/[[...sign-up]]/page.tsx`
7. `apps/web/components/auth/email-sign-in-form.tsx`
8. `apps/web/components/auth/email-sign-up-form.tsx`
9. `apps/web/app/(dashboard)/page.tsx`
10. `apps/web/app/(dashboard)/live/page.tsx`
11. `apps/web/app/(dashboard)/analytics/page.tsx`
12. `apps/web/app/(dashboard)/logs/page.tsx`
13. `apps/web/app/(dashboard)/equipment/page.tsx`
14. `apps/web/app/(dashboard)/scheduler/page.tsx`
15. `apps/web/app/(dashboard)/scheduler/new/page.tsx`
16. `apps/web/app/(dashboard)/settings/page.tsx`
17. `apps/web/app/(dashboard)/sessions/[sessionId]/page.tsx`
18. `apps/web/app/(dashboard)/sessions/[sessionId]/live/page.tsx`
19. `apps/web/components/dashboard/live-session-banner.tsx`
20. `apps/web/components/dashboard/live-session-stream.tsx`
21. `apps/web/components/dashboard/task-checklist.tsx`
22. `apps/web/components/dashboard/override-modal.tsx`
23. `apps/web/components/dashboard/session-actions.tsx`
24. `apps/web/components/dashboard/equipment-status.tsx`
25. `apps/web/components/forms/multi-step-session-form/index.tsx`
26. `apps/web/components/reports/report-generator.tsx`
27. `apps/web/app/(dashboard)/sessions/new/page.tsx` (redirect)
28. Dead code cleanup (step stubs, unused charts component)
