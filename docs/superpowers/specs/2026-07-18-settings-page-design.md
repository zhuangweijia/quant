# Settings Page Completion Design

**Date:** 2026-07-18
**Status:** Approved in conversation

## Context

The current settings route renders a single placeholder card even though the backend already exposes APIs for notification configuration, system parameters, profile data, and password changes. The frontend also has a working local theme store that is not exposed through the settings page. The existing frontend password request shape does not match the backend contract, and most database-backed system parameters are stored but are not yet consumed by the analysis runtime.

## Goals

- Replace the placeholder with a complete, usable settings page.
- Present appearance, notifications, system parameters, and account security on one spacious page.
- Keep each settings area independently understandable, loadable, and saveable.
- Preserve sensitive notification secrets without returning plaintext values to the browser.
- Keep administrator-only controls hidden in the UI and protected by backend authorization.
- Ensure editable analysis parameters affect subsequent jobs instead of acting as display-only values.
- Add focused frontend and backend coverage and verify the final page visually.

## Non-goals

- Adding stock universes beyond the currently supported CSI 300 workflow.
- Building organization-level profiles, multi-tenant settings, or fine-grained permissions.
- Adding notification channels beyond email and Webhook.
- Persisting appearance preferences on the server.
- Invalidating all previously issued JWTs after a password change; the client will clear its own session and require a new login.

## Information Architecture

The existing `BasicPage` remains the page shell. Its content becomes a vertical stack of four independent cards:

1. **Appearance** — visible to every user.
2. **Notifications** — visible to every user.
3. **System parameters** — visible only to administrators.
4. **Account security** — visible to every user.

This single-page structure keeps the available settings visible without adding route depth or hiding errors behind tabs. Each card owns its loading, dirty, submitting, success, and error state so one failed request does not block the rest of the page.

## Frontend Components

`SettingsView.vue` becomes a thin orchestration shell. The implementation introduces four focused child components under the settings view directory.

### AppearanceSettingsCard

- Reads and writes the existing theme store.
- Controls color mode: light, dark, or system.
- Controls the existing accent color choices.
- Controls the existing radius value through a small set of labeled density choices.
- Applies changes immediately and relies on the theme store's current local-storage persistence.
- Has no save button because the preview and persistence are immediate.

### NotificationSettingsCard

- Loads `/api/v1/settings/notifications` independently.
- Supports email enabled state, SMTP host, SMTP port, sender, recipient, SSL, and password.
- Supports Webhook enabled state, URL, secret, and notification levels.
- Displays whether a password or secret already exists without exposing it.
- Treats an empty secret field as “keep the existing value.”
- Provides a primary save action plus separate test-email and test-Webhook actions.
- Enables test actions only when the corresponding channel is enabled and the current form has been saved.

### SystemParamsCard

- Renders only when the authenticated user role is `admin`.
- Loads `/api/v1/settings/params` only for administrators.
- Groups fields into retention, model windows, prediction thresholds, stock universe, and schedule.
- Shows CSI 300 as the only supported stock universe instead of presenting inactive options.
- Provides save and restore-default actions.
- Uses a confirmation dialog before restoring defaults.
- Explains that saved values affect subsequent analysis or cleanup jobs rather than an already-running job.

### AccountSecurityCard

- Loads `/api/v1/settings/profile` independently.
- Displays username, role, account state, and creation time.
- Provides current password, new password, and confirmation fields.
- Requires a new password of 8–64 characters containing at least one letter and one digit.
- Clears local authentication state and redirects to the login page after a successful password change.

## API Contracts

The frontend settings client gains typed methods for notifications and test actions. Its password payload is corrected to match the backend contract:

```ts
{
  old_password: string
  new_password: string
  confirm_password: string
}
```

Notification responses continue to return `has_email_password` and `has_webhook_secret`; they never return decrypted secret values. Saving a blank secret preserves the prior encrypted value.

System parameters move from an unvalidated generic dictionary at the API boundary to a typed request model. Unknown keys are rejected instead of silently ignored. The response remains a complete parameter object so the UI can replace its saved baseline after save or reset.

## System Parameter Validation

The frontend provides immediate field feedback, while the backend remains authoritative. The accepted constraints are:

- Data retention days: 7–3650.
- Alert retention days: 7–3650.
- Model training window: 252–2520 trading days.
- Model validation window: 21–504 trading days and shorter than the training window.
- Forward-return window: 1–30 trading days.
- Forward-return threshold: greater than 0 and at most 1.
- Model IC threshold: 0–1.
- Stock universe: `csi300` only.
- Analysis time: a valid `HH:mm` time.

Invalid values return a 422 response with field-level detail. The frontend maps validation detail back to the relevant control and also shows a concise toast when a request fails.

## Runtime Parameter Flow

Database-backed system parameters use environment settings as defaults and database values as runtime overrides.

- A typed runtime-parameter provider converts stored strings into validated values.
- A pipeline run loads one immutable parameter snapshot at its start and passes that snapshot to the model operations it invokes. An in-progress run is never changed halfway through.
- Model training, prediction-label construction, validation-window selection, and IC activation checks consume the snapshot rather than reading Pydantic environment settings directly.
- Cleanup continues to load retention values at the start of each cleanup run.
- A malformed legacy database override is logged and replaced by its validated environment default; new malformed values are rejected at the API boundary.
- Saving a new analysis time explicitly commits the database transaction before rescheduling the analysis job.
- The CSI 300 value is displayed but not made editable until another universe is implemented end to end.

This design makes the settings page truthful: a successful save changes the next relevant job, while preserving environment variables as safe boot defaults.

## Permissions and Security

- The frontend uses the authenticated role only to decide whether to render and request administrator data.
- Backend role checks remain mandatory for all system-parameter reads, writes, and resets.
- Notification secrets remain encrypted through the existing encryption service.
- Password fields are never persisted locally or logged.
- Notification test actions are explicit button presses and report sent/failed status without exposing secrets.
- Password-change success clears both access and refresh tokens from local storage.

## Loading, Error, and Dirty-state Behavior

- Cards render their own skeleton or compact loading state.
- A card request failure shows a local retry action and does not hide successful cards.
- Save buttons remain disabled until data is dirty and valid.
- Save and test actions prevent duplicate submission while in flight.
- Successful saves update the card's saved baseline and show a toast.
- Reset replaces the system-parameter form with the complete server response.
- Navigating away with unsaved data does not introduce a global route blocker; the dirty state remains visible through enabled save/reset controls. This keeps the first version focused and avoids browser-navigation complexity.

## Testing Strategy

### Frontend

- API client tests cover notification methods and the corrected password payload.
- Appearance-card tests cover theme mode, color, and radius updates.
- Notification-card tests cover existing-secret indicators, blank-secret preservation, dirty state, and test-action enablement.
- System-parameter tests cover administrator visibility, validation, save, and reset confirmation.
- Account-card tests cover profile rendering, password validation, and logout/redirect after success.
- Settings-view tests verify that non-administrators do not request or render system parameters and that one card failure does not block the others.

### Backend

- Settings API tests cover administrator enforcement, typed validation, reset behavior, and secret preservation.
- Runtime-provider tests cover environment defaults, database overrides, type conversion, and invalid stored values.
- Pipeline/model tests verify that one immutable snapshot is used for a run and that the configured thresholds/windows reach their consumers.
- Scheduler tests verify rescheduling only after a successful settings save.

### Completion Verification

- Run the frontend and backend test suites.
- Run the frontend production build and backend lint checks relevant to changed files.
- Verify appearance, notifications, administrator parameters, ordinary-user permissions, profile, and password validation in a local browser.
- Confirm that no plaintext secrets appear in API responses or browser state.

## Success Criteria

- No placeholder content remains on the settings page.
- Every visible control either changes local appearance immediately or completes a real backend operation.
- Ordinary users can manage appearance, notifications, and account security but cannot see or call administrator system-parameter operations.
- Administrators can save and reset validated parameters, and those values affect the next relevant job.
- Sensitive notification values remain encrypted and undisclosed.
- Independent card failures are recoverable without breaking the rest of the page.
- Automated tests, production build, and browser verification pass.
