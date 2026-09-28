# Stretch Goal — Idempotent Setup & Seed Scripts (M, 2 points)

> Applies to all three project versions. *Site*, *asset*, and *job* stand in for your version's nouns.

## Summary

`bin/setup.sh` and `bin/seed.sh` work when run once, on the machine they were written on, in the right shell. Run either a second time and the results get strange: seeding appends another copy of the data, and setup's behavior depends on state it does not check carefully. This feature makes both scripts safe to run repeatedly, clear about what went wrong when something does, and free of credentials.

This is the least glamorous item on the list and the one most likely to save someone an afternoon, because a broken seed script fails at the exact moment you are trying to fix something else.

## Workflow

1. Someone clones the repository and runs `bin/setup.sh`. It checks its prerequisites, creates what is missing, and finishes.
2. They run it again. It reports what already exists, changes nothing it shouldn't, and finishes cleanly.
3. They run `bin/seed.sh` against their local database. Tables are created and populated.
4. They run it again. The data is the same afterwards as before — no duplicate sites, no doubled assets.
5. They run `bin/seed.sh --reset`. The script warns, asks for confirmation, then drops and rebuilds the seed data.
6. They run it with the database stopped. It fails immediately with a message naming the problem, and exits non-zero.

## Requirements

### Functional Requirements

1. `bin/setup.sh` can be run repeatedly with the same end state and no errors
2. `bin/setup.sh` checks its prerequisites before doing work and, if one is missing, reports which one by name and stops
3. `bin/setup.sh` creates the virtual environment only when absent, and never overwrites an existing `.env`
4. `bin/seed.sh` can be run repeatedly without creating duplicate records
5. `bin/seed.sh` accepts a `--reset` flag that clears seed data and reloads it, confirming first unless a `--yes` flag is also supplied
6. `bin/seed.sh` reads its connection details from the environment, and fails with a clear message when they are missing
7. Neither script contains a password, connection string, or endpoint — placeholder or otherwise
8. Both scripts exit non-zero on failure and zero on success
9. Both scripts can be run from any working directory, not only the repository root
10. `bin/seed.sh` fails with a clear message when the database is unreachable, rather than partway through

### Non-Functional Requirements

1. Both scripts begin with `set -euo pipefail` so an unset variable or a failing command in a pipeline stops the run
2. Neither script echoes secrets, including in error messages
3. The seed data exercises every business question, including the awkward cases — assets below the low-level threshold, technicians assigned to a site other than their asset's, a site above the maintenance percentage, and jobs in each status
4. Both scripts are documented in the README with their flags and required environment variables

## User Stories

- As a developer, I can run setup on a fresh clone and get a working environment
- As a developer, I can re-run either script without wondering what state it will leave behind
- As a developer, I can reset my data to a known state with one command
- As a developer, a failing script tells me what went wrong instead of leaving me to work it out
- As a reviewer, I can read the repository and find no credentials in it

## Technical Notes

- Look at the existing scripts closely before rewriting; both contain bugs that are easier to see once you are looking for them. The `[` test syntax needs spaces inside the brackets, and bash default-value expansion has a specific form that is easy to get subtly wrong — a mistyped one silently produces a literal string rather than the intended default
- `setup.sh` currently activates the virtual environment at `.venv/Scripts/activate`, which exists on Windows and not elsewhere. Detect the platform, or document the requirement explicitly in the script's own output rather than only in a comment
- Idempotent seeding is the substantive part. Options in rough order of effort: `INSERT … ON CONFLICT DO NOTHING` against a unique key, a truncate-then-load inside `--reset`, or checking for a sentinel row and exiting early. Deterministic identifiers in the seed data make all three easier, and make the `--reset` path honest
- Requirement 6 replaces the current pattern of building the connection string inside the script. `.env` is already being read by the application through the `Settings` class; having the script source the same file keeps one source of truth and takes the credentials out of version control
- Resolve paths relative to the script's own location rather than the current directory, so requirement 9 holds
- Check the exit status of each step rather than letting a failed table creation be followed by a load that half works

## Definition of Done

- [ ] `bin/setup.sh` run twice in a row succeeds both times with the same end state
- [ ] `bin/setup.sh` with a prerequisite missing names it and exits non-zero
- [ ] An existing `.env` is never overwritten by setup
- [ ] `bin/seed.sh` run twice leaves the same data as running it once
- [ ] `bin/seed.sh --reset` clears and reloads after confirmation; `--yes` skips the prompt
- [ ] `bin/seed.sh` with no database configuration fails immediately with a clear message
- [ ] `bin/seed.sh` against a stopped database fails before writing anything
- [ ] Neither script contains a password, connection string, or endpoint
- [ ] Both scripts run correctly from a directory other than the repository root
- [ ] Both scripts exit non-zero on failure
- [ ] Seed data produces non-trivial results for every business question, including the edge cases
- [ ] The README documents both scripts, their flags, and their required environment variables
