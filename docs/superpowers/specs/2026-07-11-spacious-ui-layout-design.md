# Spacious UI Layout Design

Date: 2026-07-11

## Context

The current Vue/Vite frontend already uses Tailwind CSS, shadcn-style UI primitives, lucide icons, and a collapsible sidebar. Screenshots show that several control surfaces feel crowded:

- The top command search button sits too close to the sidebar trigger and compresses its text and shortcut hint.
- The icon-only sidebar state leaves little visual breathing room around navigation icons.
- The model management page places the title and action buttons on a single tight row, causing actions such as "回测" and "训练新模型" to feel stacked or cramped at narrower widths.

The requested direction is a more spacious and elegant interface with more whitespace, while preserving the professional control-console character of the product.

## Goals

- Increase perceived whitespace in shared navigation and page chrome.
- Prevent button text, icons, shortcut hints, and page titles from visually colliding.
- Keep the UI practical for repeated operational use, not marketing-like or decorative.
- Improve the screenshots' problem areas through shared layout patterns where reasonable.

## Non-Goals

- No business logic changes.
- No redesign of charts, tables, data fetching, authentication, or model APIs.
- No new design system dependency.
- No full visual rebrand.

## Proposed Approach

Use a focused shared-layout refinement:

1. Update the app shell spacing so the header has more horizontal rhythm, the command search trigger has a stable pill width, and the main content sits in a calmer page container.
2. Tune the sidebar expanded and collapsed states so icon-only navigation is centered, text is hidden cleanly when collapsed, and expanded navigation rows have more comfortable hit targets.
3. Refine button and model page header composition so action buttons keep stable internal spacing and wrap below the title when width is constrained.

This approach gives the visible screenshots a clear improvement while keeping the change set small and reusable.

## Detailed Design

### App Layout

- Increase header height slightly from the current compact 56px feel to a more relaxed 64px feel.
- Keep the sidebar trigger, divider, search trigger, and theme toggle aligned on a single center line.
- Make the command search trigger a stable pill-shaped control with a desktop width around 220-260px and a compact icon-only or shorter width on small screens.
- Use a main content wrapper with responsive padding:
  - Mobile and narrow screens keep moderate padding.
  - Desktop screens get larger padding.
  - Very wide screens use a max-width container so content does not stretch into an overly sparse line length.

### Sidebar

- Keep the existing `collapsible="icon"` behavior.
- Increase collapsed sidebar width from 48px to a calmer 56-64px target if needed by the existing component geometry.
- Center icons in collapsed state and prevent hidden text from affecting layout.
- Give expanded nav items a slightly taller row and clearer active state without adding visual noise.
- Keep tooltips for collapsed navigation items.

### Buttons

- Preserve the existing button variants.
- Ensure slot content remains an inline flex row so icons and text use the base button gap consistently.
- Avoid local `mr-1` spacing where the shared button gap can handle icon/text separation.
- Keep action labels on one line with `whitespace-nowrap`.

### Model Page Header

- Replace the single rigid `items-center justify-between` row with a responsive page header:
  - Title group stays together with icon and heading.
  - Action group uses `flex-wrap`, comfortable gap, and aligned buttons.
  - On narrow widths, actions move below the title instead of squeezing text.
- Use slightly larger action buttons or consistent minimum widths for "回测" and "训练新模型".

## Testing And Verification

- Run the frontend build command to catch Vue and TypeScript regressions.
- Start the Vite development server and inspect the affected screens.
- Verify at desktop and narrow widths that:
  - Top search no longer overlaps or appears cramped.
  - Collapsed sidebar icons are centered and readable.
  - Model page title and action buttons do not overlap, wrap awkwardly, or stack text inside buttons.

## Acceptance Criteria

- The screenshots' crowded elements are visibly more spacious.
- The model page action buttons keep icon and label on one line.
- The model page header wraps gracefully when width is constrained.
- The command search trigger has stable dimensions and spacing.
- The sidebar collapsed state shows clean centered icons and no clipped text.
- `npm run build` in `frontend` completes successfully.
