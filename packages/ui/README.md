# @evolve/ui — évolvé design system v4 (docs/09)

Workspace package consumed by the apps through Next `transpilePackages: ["@evolve/ui"]`. No build step.

## Use
```css
/* app globals.css */
@import "tailwindcss";
@import "@evolve/ui/tokens.css";   /* CSS variables: brand, neutral 50–950, signals, surfaces 0–3, spacing, radius, elevation, type, motion */
@import "@evolve/ui/theme.css";    /* Tailwind v4 @theme bridge */
@import "@evolve/ui/base.css";     /* focus rings, textures, keyframes, reduced motion, Ledger ink fix */
@source "../../../packages/ui/src";
```
```tsx
<EvolveUIProvider locale dir labels={messages.ui} Link={AppLink}>…</EvolveUIProvider>
```
Components never hard-code user-facing text: their own strings come from `labels` (English defaults in `src/provider.tsx`), and content comes in through props.

## Tokens moved
The token source of truth is `packages/ui/tokens/`. `design/tokens.css` and `design/tailwind-theme.css` are now one-line re-exports, kept for older references. Themes are `:root`/`[data-theme="clinic"]` and `[data-theme="ledger"]`, and they can be nested.

## Inventory (docs/09 §5)
- **Primitives:** Button (primary/secondary/ghost/danger/danger-outline/lime/link; sm/md/lg; loading), IconButton, ChamferCTA, FormField, Input, Textarea, Select, Checkbox, RadioGroup, Switch, Card/CardHeader, StatCard, Badge, StatusChip, VisibilityChip, Avatar, Alert, EmptyState, Skeleton, LoadingRegion, ErrorState, OfflineBanner, StaleNotice, PermissionState, GuardBanner, Notice, EnvironmentBanner, SimulatedBadge, Toast (ToastProvider/useToast/ToastPreview), Dialog, ConfirmDialog, Drawer, Tooltip, DropdownMenu, Popover, Tabs, Stepper, Accordion, Breadcrumbs, Pagination
- **Data and patterns:** DataTable (TanStack Table v9), AuditTable, ConsentTable, FindingCard, Timeline, CareTimeline, MessageThread
- **Locked numbers:** LockedNumber (+ provenance; `formatLocked` is the single formatter, DECISIONS #29), SourceCaption, DetectionBar, IconArray, OverlapCircles, SunburstProgress
- **Shell:** AppShell, Sidebar, TopBar, ContextStrip, BottomTabs, NotificationBell, LangSwitch, ProfileMenu, ShellFooter, PageHeader
- **Pedigree:** PedigreeGraph (`src/pedigree/`, built and owned by the counselor instance by agreement)

The living style guide is `/[locale]/design-system` in apps/citizen. It is also the Playwright visual-regression target.

## Rules
- Numbers only through LockedNumber; no arithmetic on probabilities (P-01/P-02).
- Logical properties only (RTL-safe).
- Every control has a 44 px target.
- Signal colors are always paired with an icon and text.
- No `any`.
