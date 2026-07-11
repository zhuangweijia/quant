# Spacious UI Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the app shell, collapsed sidebar, shared buttons, and model page header feel more spacious and elegant without changing business behavior.

**Architecture:** Use the existing Vue 3, Tailwind CSS, shadcn-style component primitives, and lucide icons. Apply the density improvements in shared layout primitives first, then tune the model page header where the screenshot shows page-specific crowding.

**Tech Stack:** Vue 3, TypeScript, Vite, Tailwind CSS v4, class-variance-authority, lucide-vue-next, reka-ui.

## Global Constraints

- No business logic changes.
- No redesign of charts, tables, data fetching, authentication, or model APIs.
- No new design system dependency.
- No full visual rebrand.
- The requested direction is a more spacious and elegant interface with more whitespace, while preserving the professional control-console character of the product.
- `npm run build` in `frontend` must complete successfully.

---

## File Structure

- Modify `frontend/src/components/layout/AppLayout.vue`: App shell header spacing, search trigger sizing, and main content container.
- Modify `frontend/src/components/app-sidebar/index.vue`: Sidebar header/footer/nav spacing and collapsed-state text behavior.
- Modify `frontend/src/components/ui/button/Button.vue`: Ensure slot content participates in inline-flex spacing so icons and labels do not visually stack.
- Modify `frontend/src/components/ui/sidebar/utils.ts`: Increase collapsed sidebar width token.
- Modify `frontend/src/components/ui/sidebar/index.ts`: Tune sidebar menu button size and collapsed icon centering.
- Modify `frontend/src/views/model/ModelView.vue`: Responsive page header and action button spacing.
- Modify `frontend/package.json`: Add a lightweight layout verification script.
- Create `frontend/scripts/verify-spacious-layout.mjs`: Static layout contract checks for the affected Vue component classes.

---

### Task 1: Spacious Shared Layout And Model Header

**Files:**
- Modify: `frontend/src/components/layout/AppLayout.vue`
- Modify: `frontend/src/components/app-sidebar/index.vue`
- Modify: `frontend/src/components/ui/button/Button.vue`
- Modify: `frontend/src/components/ui/sidebar/utils.ts`
- Modify: `frontend/src/components/ui/sidebar/index.ts`
- Modify: `frontend/src/views/model/ModelView.vue`
- Modify: `frontend/package.json`
- Create: `frontend/scripts/verify-spacious-layout.mjs`

**Interfaces:**
- Consumes: Existing `UiSidebarProvider`, `AppSidebar`, `CommandMenu`, `Button`, `UiSidebarMenuButton`, and model API handlers.
- Produces: Same component public interfaces and same user-facing actions; only class/layout output changes.

- [ ] **Step 1: Record the current build baseline**

Run:

```bash
cd frontend
npm run build
```

Expected: Either PASS, or an existing unrelated failure recorded before production edits. Do not edit production files until the baseline is known.

- [ ] **Step 2: Add the failing layout contract test**

In `frontend/scripts/verify-spacious-layout.mjs`, create:

```js
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = resolve(__dirname, '..')

const checks = [
  {
    file: 'src/components/layout/AppLayout.vue',
    expected: ['h-16', 'sm:w-64', 'max-w-7xl px-5 py-7'],
  },
  {
    file: 'src/components/app-sidebar/index.vue',
    expected: ['group-data-[collapsible=icon]:hidden', 'px-2 py-3', 'gap-3'],
  },
  {
    file: 'src/components/ui/button/Button.vue',
    expected: ['inline-flex items-center justify-center gap-2'],
  },
  {
    file: 'src/components/ui/sidebar/utils.ts',
    expected: ['SIDEBAR_WIDTH_ICON = "4rem"'],
  },
  {
    file: 'src/components/ui/sidebar/index.ts',
    expected: ['group-data-[collapsible=icon]:size-10!', 'default: "h-10 text-sm"'],
  },
  {
    file: 'src/views/model/ModelView.vue',
    expected: ['flex flex-col gap-5 sm:flex-row', 'min-w-32', '<span>训练新模型</span>'],
  },
]

const failures = []

for (const check of checks) {
  const contents = readFileSync(resolve(root, check.file), 'utf8')

  for (const expected of check.expected) {
    if (!contents.includes(expected)) {
      failures.push(`${check.file} is missing: ${expected}`)
    }
  }
}

if (failures.length > 0) {
  console.error('Spacious layout verification failed:')
  for (const failure of failures) {
    console.error(`- ${failure}`)
  }
  process.exit(1)
}

console.log('Spacious layout verification passed.')
```

In `frontend/package.json`, add a script entry after `"build"`:

```json
"test:layout": "node scripts/verify-spacious-layout.mjs",
```

Expected: The script exists but fails until the layout classes are implemented.

- [ ] **Step 3: Run layout test to verify it fails**

Run:

```bash
cd frontend
npm run test:layout
```

Expected: FAIL with messages such as `src/components/layout/AppLayout.vue is missing: h-16`.

- [ ] **Step 4: Update shared button slot layout**

In `frontend/src/components/ui/button/Button.vue`, change the non-loading slot wrapper from:

```vue
<span :class="loading ? 'invisible' : ''">
  <slot />
</span>
```

to:

```vue
<span :class="cn('inline-flex items-center justify-center gap-2', loading ? 'invisible' : '')">
  <slot />
</span>
```

Expected: Button icons and text align consistently through the existing `gap-2` behavior, including when a button contains an icon and Chinese label.

- [ ] **Step 5: Increase collapsed sidebar width token**

In `frontend/src/components/ui/sidebar/utils.ts`, change:

```ts
export const SIDEBAR_WIDTH_ICON = "3rem"
```

to:

```ts
export const SIDEBAR_WIDTH_ICON = "4rem"
```

Expected: The icon-only sidebar has 64px of width, matching the design doc and giving centered icons enough breathing room.

- [ ] **Step 6: Tune sidebar menu button variants**

In `frontend/src/components/ui/sidebar/index.ts`, update the `sidebarMenuButtonVariants` base string from:

```ts
"peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left text-sm outline-hidden ring-sidebar-ring transition-[width,height,padding] hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-data-[sidebar=menu-action]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:size-8! group-data-[collapsible=icon]:p-2! [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0",
```

to:

```ts
"peer/menu-button flex w-full items-center gap-3 overflow-hidden rounded-md px-3 py-2 text-left text-sm outline-hidden ring-sidebar-ring transition-[width,height,padding] hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-data-[sidebar=menu-action]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:mx-auto group-data-[collapsible=icon]:size-10! group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:p-0! group-data-[collapsible=icon]:[&>span]:hidden [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0",
```

and update the size variant from:

```ts
default: "h-8 text-sm",
```

to:

```ts
default: "h-10 text-sm",
```

Expected: Expanded nav items have a more comfortable 40px row height, while collapsed nav icons are centered in a 40px target and labels are hidden.

- [ ] **Step 7: Refine app shell spacing**

In `frontend/src/components/layout/AppLayout.vue`, replace the template block:

```vue
<UiSidebarProvider>
  <AppSidebar />
  <UiSidebarInset>
    <header class="flex h-14 items-center gap-3 border-b px-4 shrink-0">
      <UiSidebarTrigger class="-ml-1" />
      <UiSeparator orientation="vertical" class="h-6" />
      <Button variant="outline" size="sm" class="ml-2 gap-2 text-muted-foreground" @click="openCommandMenu">
        <Search class="size-4" />
        <span class="hidden sm:inline">搜索...</span>
        <kbd class="pointer-events-none hidden sm:inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
          ⌘K
        </kbd>
      </Button>
      <div class="flex-1" />
      <div class="flex items-center gap-2">
        <UiButton variant="ghost" size="icon" @click="toggleTheme">
          <SunMedium v-if="!isDark" class="size-4" />
          <MoonStar v-else class="size-4" />
        </UiButton>
      </div>
    </header>

    <main class="flex-1 p-6 overflow-auto">
      <router-view v-slot="{ Component, route }">
        <transition name="page" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </main>
  </UiSidebarInset>
  <CommandMenu ref="commandMenuRef" />
</UiSidebarProvider>
```

with:

```vue
<UiSidebarProvider>
  <AppSidebar />
  <UiSidebarInset>
    <header class="flex h-16 shrink-0 items-center gap-4 border-b bg-background/95 px-5 backdrop-blur supports-[backdrop-filter]:bg-background/80 lg:px-6">
      <UiSidebarTrigger class="size-9" />
      <UiSeparator orientation="vertical" class="h-7" />
      <Button
        variant="outline"
        size="sm"
        class="h-9 w-11 justify-start rounded-full px-3 text-muted-foreground shadow-none sm:w-64 sm:px-4"
        @click="openCommandMenu"
      >
        <Search class="size-4" />
        <span class="hidden flex-1 text-left sm:inline">搜索...</span>
        <kbd class="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground sm:inline-flex">
          ⌘K
        </kbd>
      </Button>
      <div class="flex-1" />
      <div class="flex items-center gap-2">
        <UiButton variant="ghost" size="icon" class="size-9 rounded-full" @click="toggleTheme">
          <SunMedium v-if="!isDark" class="size-4" />
          <MoonStar v-else class="size-4" />
        </UiButton>
      </div>
    </header>

    <main class="flex-1 overflow-auto">
      <div class="mx-auto w-full max-w-7xl px-5 py-7 sm:px-6 lg:px-8 lg:py-8">
        <router-view v-slot="{ Component, route }">
          <transition name="page" mode="out-in">
            <component :is="Component" :key="route.path" />
          </transition>
        </router-view>
      </div>
    </main>
  </UiSidebarInset>
  <CommandMenu ref="commandMenuRef" />
</UiSidebarProvider>
```

Expected: The top bar has more room, the search trigger has stable dimensions, and page content sits inside a spacious responsive container.

- [ ] **Step 8: Refine app sidebar spacing**

In `frontend/src/components/app-sidebar/index.vue`, make these class changes:

Change:

```vue
<UiSidebarHeader class="border-b px-4 py-3">
```

to:

```vue
<UiSidebarHeader class="border-b px-3 py-4 group-data-[collapsible=icon]:px-2">
```

Change the brand button from:

```vue
<UiSidebarMenuButton size="lg" class="gap-3">
```

to:

```vue
<UiSidebarMenuButton size="lg" class="gap-3 group-data-[collapsible=icon]:mx-auto group-data-[collapsible=icon]:size-10 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:p-0">
```

Change both brand and user text wrappers from:

```vue
<div class="grid flex-1 text-left text-sm leading-tight">
```

to:

```vue
<div class="grid flex-1 text-left text-sm leading-tight group-data-[collapsible=icon]:hidden">
```

Change:

```vue
<UiSidebarContent>
```

to:

```vue
<UiSidebarContent class="px-2 py-3">
```

Change:

```vue
<UiSidebarGroup>
```

to:

```vue
<UiSidebarGroup class="gap-2">
```

Change:

```vue
<router-link :to="item.path" class="flex items-center gap-2">
```

to:

```vue
<router-link :to="item.path" class="flex min-w-0 items-center gap-3">
```

Change:

```vue
<UiSidebarFooter class="border-t">
```

to:

```vue
<UiSidebarFooter class="border-t px-2 py-3">
```

Change the user dropdown button from:

```vue
<UiSidebarMenuButton size="lg" class="gap-3">
```

to:

```vue
<UiSidebarMenuButton size="lg" class="gap-3 group-data-[collapsible=icon]:mx-auto group-data-[collapsible=icon]:size-10 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:p-0">
```

Expected: Expanded sidebar reads with more vertical rhythm; collapsed sidebar shows centered logo, navigation icons, and user avatar without clipped text.

- [ ] **Step 9: Refine model page header**

In `frontend/src/views/model/ModelView.vue`, replace:

```vue
<div class="flex items-center justify-between">
  <div class="flex items-center gap-3">
    <BrainCircuit class="size-6 text-primary" />
    <h1 class="text-2xl font-bold">模型管理</h1>
  </div>
  <div class="flex gap-2">
    <Button variant="outline" size="sm" :disabled="backtesting" @click="handleBacktest()">
      <FlaskConical class="size-4 mr-1" :class="{ 'animate-spin': backtesting }" />回测
    </Button>
    <Button size="sm" :disabled="training" @click="handleTrain">
      <Loader2 v-if="training" class="size-4 mr-1 animate-spin" />
      <Play v-else class="size-4 mr-1" />训练新模型
    </Button>
  </div>
</div>
```

with:

```vue
<div class="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
  <div class="flex min-w-0 items-center gap-3">
    <div class="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
      <BrainCircuit class="size-5" />
    </div>
    <div class="min-w-0">
      <h1 class="text-2xl font-semibold tracking-normal">模型管理</h1>
    </div>
  </div>
  <div class="flex flex-wrap items-center gap-3">
    <Button class="min-w-24" variant="outline" size="sm" :disabled="backtesting" @click="handleBacktest()">
      <FlaskConical class="size-4" :class="{ 'animate-spin': backtesting }" />
      <span>回测</span>
    </Button>
    <Button class="min-w-32" size="sm" :disabled="training" @click="handleTrain">
      <Loader2 v-if="training" class="size-4 animate-spin" />
      <Play v-else class="size-4" />
      <span>训练新模型</span>
    </Button>
  </div>
</div>
```

Expected: The page title and action group can wrap gracefully. Button labels remain on one line and have comfortable icon spacing.

- [ ] **Step 10: Run layout verification**

Run:

```bash
cd frontend
npm run test:layout
```

Expected: PASS with `Spacious layout verification passed.`

- [ ] **Step 11: Run build verification**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS with Vite build output and no Vue TypeScript errors.

- [ ] **Step 12: Run local visual verification**

Run:

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

Open the served app and inspect `/model` at desktop width and a narrow width. Verify:

- The top search trigger no longer appears cramped.
- Collapsed sidebar icons are centered and have enough whitespace.
- The model page buttons do not split labels or collide with the title.

Expected: The affected regions match the spacious design direction from the design doc.

- [ ] **Step 13: Commit implementation**

Run:

```bash
git add frontend/package.json frontend/scripts/verify-spacious-layout.mjs frontend/src/components/layout/AppLayout.vue frontend/src/components/app-sidebar/index.vue frontend/src/components/ui/button/Button.vue frontend/src/components/ui/sidebar/utils.ts frontend/src/components/ui/sidebar/index.ts frontend/src/views/model/ModelView.vue
git commit -m "style: relax app layout spacing"
```

Expected: A focused implementation commit after verification passes.
