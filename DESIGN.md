---
name: Atlas
description: Agentic customer operations assistant — grounded answers, auditable traces, role-enforced actions.
colors:
  ink-deep: "#23232B"
  ink-dark: "#1C1C23"
  accent: "#FFE600"
  bg-canvas: "#F4F4F7"
  surface: "#FFFFFF"
  border: "#E6E6EC"
  border-subtle: "#EDEDF1"
  text-secondary: "#9A9AA6"
  text-muted: "#6B6B78"
  text-body: "#3A3A44"
  semantic-green: "#1F7A4D"
  semantic-green-bg: "#E7F4EC"
  semantic-amber: "#C2410C"
  semantic-amber-bg: "#FFF4ED"
  semantic-red: "#B4232A"
  semantic-red-bg: "#FBEAEA"
  semantic-blue: "#2A5BC0"
  semantic-blue-bg: "#E7EEFB"
  risk-high: "#9A6B00"
  risk-high-bg: "#FBF1DF"
typography:
  display:
    fontFamily: "Manrope, system-ui, sans-serif"
    fontSize: "21px"
    fontWeight: 800
    lineHeight: 1.28
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Manrope, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 800
    lineHeight: 1.3
  title:
    fontFamily: "Manrope, system-ui, sans-serif"
    fontSize: "13.5px"
    fontWeight: 700
    lineHeight: 1.4
  body:
    fontFamily: "Manrope, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Manrope, system-ui, sans-serif"
    fontSize: "10.5px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.06em"
  mono:
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: 1.4
rounded:
  xs: "5px"
  sm: "8px"
  md: "11px"
  lg: "13px"
  xl: "16px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "14px"
  lg: "20px"
  xl: "28px"
  "2xl": "40px"
components:
  button-primary:
    backgroundColor: "{colors.ink-deep}"
    textColor: "{colors.surface}"
    rounded: "{rounded.sm}"
    padding: "9px 16px"
  button-primary-hover:
    backgroundColor: "#3A3A44"
    textColor: "{colors.surface}"
    rounded: "{rounded.sm}"
    padding: "9px 16px"
  button-disabled:
    backgroundColor: "#C7C7CF"
    textColor: "{colors.surface}"
    rounded: "{rounded.sm}"
    padding: "9px 16px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-deep}"
    rounded: "{rounded.lg}"
    padding: "16px 17px"
  card-dark:
    backgroundColor: "{colors.ink-dark}"
    textColor: "{colors.surface}"
    rounded: "{rounded.lg}"
    padding: "14px 15px"
  nav-item-active:
    backgroundColor: "transparent"
    textColor: "{colors.surface}"
    rounded: "{rounded.sm}"
    padding: "10px 16px"
  nav-item-inactive:
    backgroundColor: "transparent"
    textColor: "#9A9AA6"
    rounded: "{rounded.sm}"
    padding: "10px 16px"
  chip:
    backgroundColor: "{colors.bg-canvas}"
    textColor: "{colors.text-muted}"
    rounded: "{rounded.pill}"
    padding: "5px 12px"
---

# Design System: Atlas

## 1. Overview

**Creative North Star: "The Ops Room"**

Atlas is where calm intelligence meets operational urgency. The interface is built for people in motion — a support rep mid-call, an account manager preparing for a review — who need the right answer fast and the evidence to back it up. Every screen reduces cognitive load rather than adding to it. The charcoal-on-light shell recedes so that the agent's output — escalation risk levels, grounded citations, tool traces — can do the communicating.

The system pairs a dark sidebar and topbar with a light content canvas. Color is reserved: the yellow accent (`#FFE600`) appears only on active states, risk levels, and trace highlights. Semantic colors (green, amber, orange, red) carry status meaning and are never used decoratively. The JetBrains Mono typeface marks machine-generated content (IDs, latencies, tool names, citations) so users can immediately distinguish agent output from UI chrome.

This system explicitly rejects the chatbot consumer aesthetic — no rounded-everything, no pastel palette, no bubble chat. It equally rejects the generic SaaS dashboard template: no navy sidebar, no blue primary button, no chart-heavy homepage that looks like Salesforce. Atlas is an ops tool. Its visual language earns trust through precision, not through decoration.

**Key Characteristics:**
- Dark shell, light canvas — sidebar and topbar in charcoal; content area in `#F4F4F7`
- Yellow accent used sparingly — active nav, risk HIGH badge, trace highlights only
- Monospace as a semantic signal — JetBrains Mono marks agent/machine content exclusively
- Flat by default — no shadows except subtle `0 1px 3px` on interactive cards on hover
- Semantic color is functional — green/amber/red/blue only for status, never decoration

## 2. Colors

A restrained two-tone palette: charcoal foundations with a single yellow accent. Semantic colors carry all status meaning.

### Primary
- **Ink Deep** (`#23232B`): Primary text, active UI elements, filled buttons, sidebar background. The visual anchor of every screen.
- **Ink Dark** (`#1C1C23`): Dark panel backgrounds (sidebar, agent trace, dark cards). Deeper than Ink Deep; used for surfaces, not text.

### Secondary
- **Accent Yellow** (`#FFE600`): Active sidebar indicator bar, risk-HIGH badge background, agent trace highlights, "verdict" label. Used on ≤8% of any screen. Its rarity signals importance.

### Neutral
- **Canvas** (`#F4F4F7`): Main content area background. Slightly cool tint to distinguish from pure white surfaces.
- **Surface** (`#FFFFFF`): Cards, panels, input backgrounds. The resting state of all interactive containers.
- **Border** (`#E6E6EC`): Card borders, dividers between list items.
- **Border Subtle** (`#EDEDF1`): Internal dividers, table row separators. One step lighter than Border.
- **Text Secondary** (`#9A9AA6`): Labels, column headers, metadata. Check contrast on Canvas: 3.8:1 — use only for large labels (11px+ bold) or non-critical metadata.
- **Text Muted** (`#6B6B78`): Supporting text, sub-labels. Minimum 4.5:1 contrast required; do not use on tinted backgrounds.
- **Text Body** (`#3A3A44`): Prose body text in answer cards and descriptions.

### Semantic
- **Green** (`#1F7A4D` / `#E7F4EC`): Healthy status, PASS badge, grounded=yes. Never used for branding.
- **Amber** (`#C2410C` / `#FFF4ED`): At-risk status, warning state.
- **Red** (`#B4232A` / `#FBEAEA`): Critical status, FAIL badge, RBAC denied, error states.
- **Blue** (`#2A5BC0` / `#E7EEFB`): Customer name links, note badges, informational states.
- **Gold/Risk** (`#9A6B00` / `#FBF1DF`): Risk MEDIUM badge, issue history note. Distinct from Accent Yellow.

### Named Rules
**The Accent Scarcity Rule.** `#FFE600` is used on ≤2 elements per screen. If it appears on three or more elements simultaneously, one of them is wrong. The accent signals "here is what matters now" — diluting it destroys the signal.

**The Semantic Purity Rule.** Green, amber, red, and blue are status colors only. They are never used for decorative borders, section dividers, background washes, or branding elements.

## 3. Typography

**UI Font:** Manrope (Google Fonts; fallback: `system-ui, sans-serif`)
**Data/Agent Font:** JetBrains Mono (Google Fonts; fallback: `'Fira Code', monospace`)

**Character:** Manrope's humanist geometry reads as both precise and approachable — confident without corporate stiffness. JetBrains Mono carries the machine voice: IDs, latencies, tool names, and citations are immediately distinguishable from human-authored content without a color shift.

### Hierarchy
- **Display** (800, 21px, 1.28, −0.01em): Issue titles, page H2s, assistant answer headers. Never in sidebar or topbar.
- **Headline** (800, 16px, 1.3): Section headers ("Recent traces", "Actions"), panel titles.
- **Title** (700, 13.5px, 1.4): Card headings, list item primary labels, user names.
- **Body** (400, 13px, 1.55): Description text, issue notes, answer body prose. Max 72ch.
- **Label** (700, 10.5px, 1.2, 0.06em, uppercase): Column headers, KPI labels, section eyebrows. Used sparingly — only for true structural labels.
- **Mono** (JetBrains Mono 600, 11px, 1.4): All agent-generated content: trace IDs, tool call names, latency values, issue IDs (`ISS-0001`), role badges, citation chips.

### Named Rules
**The Two-Voice Rule.** Manrope is the human voice; JetBrains Mono is the machine voice. Never use Mono for UI labels, button text, or prose. Never use Manrope for IDs, latencies, or tool names. The distinction must be audible at a glance.

## 4. Elevation

Atlas is flat by default. Depth is communicated through tonal layering (dark sidebar against light canvas, white cards against `#F4F4F7`) rather than shadows. This keeps the interface feeling precise and uncluttered.

Shadows appear only as a response to interactive state — hover on a login card, a floating dropdown — never at rest on static surfaces.

### Shadow Vocabulary
- **Interactive lift** (`0 1px 4px rgba(0,0,0,.06)`): Login persona cards on hover. Signals "this is clickable and ready."
- **Dropdown float** (`0 18px 50px -18px rgba(0,0,0,.32)`): TopBar user menu, any floating overlay. Strong directional shadow for clearly elevated layers.

### Named Rules
**The Flat-By-Default Rule.** Cards, panels, and list items have no shadow at rest. The border (`1px solid #E6E6EC`) is the only depth signal at rest. Shadows appear on hover or for floating overlays only.

## 5. Components

### Buttons
- **Shape:** Gently rounded (8px radius)
- **Primary:** Ink Deep background (`#23232B`), white text, `9px 16px` padding, 12.5px 700-weight Manrope. Disabled: `#C7C7CF` background.
- **Hover:** Background shifts to `#3A3A44`. No transform, no shadow — stays flat.
- **Focus:** `outline: 2px solid #FFE600; outline-offset: 2px`
- **Ghost/Unset:** Many interactive elements use `all: unset` + cursor pointer. This is intentional for list items and nav items; full button treatment for primary actions only.

### Status & Role Badges (Chips)
- Pill shape (999px radius), 10–10.5px Mono, 700-weight
- Each semantic color pair (fg/bg): green `#1F7A4D`/`#E7F4EC`, amber `#C2410C`/`#FFF4ED`, red `#B4232A`/`#FBEAEA`, blue `#2A5BC0`/`#E7EEFB`
- Used inline in tables, list items, and detail panels. Never stacked.

### Cards / Containers
- **Corner Style:** 13px radius (lg) for standard cards; 16px (xl) for login persona cards
- **Background:** White (`#FFFFFF`) on canvas (`#F4F4F7`)
- **Dark variant:** `#1C1C23` background, used for agent trace panel and Architecture dark cards
- **Border:** `1px solid #E6E6EC` on white cards; none on dark cards
- **Internal Padding:** `16px 17px` standard; `14px 15px` compact (dark cards)
- **Shadow:** None at rest; `0 1px 4px rgba(0,0,0,.06)` on hover for interactive cards

### Inputs / Fields
- **Style:** `1.5px solid #E0E0E6` border, 9px radius, `9px 12px` padding, Manrope 13px
- **Focus:** Border shifts to `#23232B`. No glow, no color fill — restrained.
- **Disabled:** `opacity: 0.5`. The field is visually present to show what the role would allow.
- **Placeholder:** `#9A9AA6` — verify 4.5:1 contrast on white background at 13px (borderline; use `#6B6B78` if failing).

### Navigation (Sidebar)
- **Shell:** `#1C1C23` background, 248px wide, full-height
- **Nav items:** 10px 16px padding, 13.5px Manrope 600, inactive text `#9A9AA6`, active text `#FFFFFF`
- **Active indicator:** 3px `#FFE600` bar flush to left edge, `position: absolute`
- **Icons:** 16px SVG, stroke-based, `currentColor`
- **Hover:** Background `rgba(255,255,255,0.06)`

### Agent Trace Panel (Signature Component)
The collapsible trace footer is Atlas's most distinctive component. It sits below every assistant answer in a dark (`#1C1C23`) container, collapsed to a single line showing tool count and latency, expandable to reveal the full step-by-step tool call waterfall with args, outputs, and a plan header. The collapse toggle uses a `▸`/`▾` triangle — no animated accordion, instant toggle. Trace metadata (tool names, latency, IDs) exclusively uses JetBrains Mono.

### Escalation Skill Card (Signature Component)
A dark-header card (Ink Deep background, white `SKILL` pill label) with a risk badge (HIGH/MEDIUM/LOW/CRITICAL using semantic colors). Inside: executive summary prose, two-column Risk Rationale + Missing Information grid, a yellow-tinted `RECOMMENDED NEXT ACTION` box, and an Urgency + Owner footer row. This card is the primary output surface for the Customer Escalation Skill.

## 6. Do's and Don'ts

### Do:
- **Do** use `#FFE600` only for: active nav indicator, risk HIGH badge, agent trace highlight, and verdict labels. Maximum 2 instances per screen.
- **Do** use JetBrains Mono for every piece of machine-generated content: IDs, latencies, tool names, role badges, citation chips, trace spans.
- **Do** use `#3A3A44` for body prose and `#9A9AA6` only for labels ≥11px bold where contrast is acceptable (structural metadata, not reading content).
- **Do** keep cards flat at rest — `1px solid #E6E6EC` border, no shadow. Shadow only on hover or for floating overlays.
- **Do** show RBAC constraints in-context: disable the input field at 50% opacity and display a `read-only role` label inline. Never surprise users with a permission error after they attempt an action.
- **Do** use `#F4F4F7` canvas + white card surfaces for all content areas. The color contrast between canvas and card is the primary depth signal.

### Don't:
- **Don't** use bubble-style chat UI, rounded-everything aesthetics, or pastel colors. Atlas is not a consumer chatbot or support widget.
- **Don't** build a generic SaaS dashboard: no navy sidebar, no blue primary buttons, no chart-heavy homepage that resembles Salesforce or HubSpot.
- **Don't** use semantic colors (green, amber, red, blue) decoratively — no colored section dividers, background washes, or branding accents.
- **Don't** use gradient text, glassmorphism, or hero-metric templates (big number + small label + gradient).
- **Don't** use `border-left` greater than 1px as a colored accent stripe on cards or list items.
- **Don't** use JetBrains Mono for UI labels, button text, navigation, or prose — it is the machine voice only.
- **Don't** add decorative motion. Transitions are 150–200ms, state-driven only. No page-load sequences, no choreographed entrances.
- **Don't** use `#9A9AA6` for body text or any text the user reads for meaning — only for structural metadata labels at adequate size and weight.
