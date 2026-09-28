# Stretch Goal — Dark Mode Toggle (S, 1 point)

> Applies to all three project versions. *Site*, *asset*, and *job* stand in for your version's nouns.

## Summary

The theme is a single hardcoded light palette created once at module load. This feature turns it into a choice: a toggle in the header switches between light and dark, the choice survives a reload, and the application follows the operating system preference the first time someone visits.

Small in scope, and a good way to find out how much colour has been hardcoded into components instead of coming from the theme.

## Workflow

1. A user opens the application for the first time. It renders in whichever mode their operating system prefers.
2. The user clicks the toggle in the header. The interface switches immediately, with no reload and no flash of the previous palette.
3. The user reloads the page. Their choice is still in effect.
4. The user navigates through lists, dialogs, forms, and the dashboard. Everything is legible in both modes.

## Requirements

### Functional Requirements

1. A control in the application header switches between light and dark mode
2. The switch takes effect immediately, without a page reload
3. The choice persists across reloads and across sessions on the same browser
4. On a first visit, with no stored choice, the mode follows the operating system preference
5. The chosen mode applies to every view, including the data grid, dialogs, form inputs, and the dashboard metric cards
6. Status colours remain distinguishable and legible in both modes
7. A stored value that is missing or unreadable falls back to the system preference rather than failing to render

### Non-Functional Requirements

1. Both palettes are defined in the theme module; components do not carry hardcoded colour values
2. Text and interactive elements meet a normal contrast standard in both modes
3. The toggle is reachable by keyboard and carries an accessible label describing what it does
4. Reading and writing the stored preference is wrapped so that a browser blocking storage does not break the application

## User Stories

- As a user, I can switch the application between light and dark
- As a user, my choice is remembered the next time I open the application
- As a user who prefers dark mode system-wide, the application respects that without my configuring anything
- As a user, every screen is readable in whichever mode I choose

## Technical Notes

- `src/theme.js` currently calls `createTheme` once with `mode: 'light'`. Turn it into a function taking the mode and returning the theme, then build it with `useMemo` in the component that owns the mode so the theme object is recreated only when the mode changes
- The mode state can live in its own small context or ride along in `AuthContext`. A separate context is cleaner, since the theme is not an authentication concern and should apply to the login screen too
- `useMediaQuery('(prefers-color-scheme: dark)')` supplies the system preference. Use it only when nothing is stored, so it never overrides an explicit choice
- `localStorage` is already used for the token, so the pattern is established. Wrap the read in a `try`/`catch` — a browser with storage blocked throws rather than returning null
- The interesting part of this feature is the audit it forces. Any component that hardcoded a colour will look wrong in dark mode, and the fix is to pull that colour from the palette. Status chips are usually the first thing to break
- `CssBaseline` needs to be inside the `ThemeProvider` for the page background to follow the mode

## Definition of Done

- [ ] A toggle in the header switches between light and dark
- [ ] The switch applies immediately with no reload
- [ ] The choice survives a page reload
- [ ] A fresh browser profile with a dark system preference opens in dark mode
- [ ] An explicit choice is not overridden by the system preference afterward
- [ ] Every view renders legibly in both modes, including the data grid, dialogs, and form inputs
- [ ] Status colours remain distinguishable in both modes
- [ ] No component contains a hardcoded colour that breaks in either mode
- [ ] The toggle is operable by keyboard and labeled
- [ ] The application still renders when browser storage is unavailable
