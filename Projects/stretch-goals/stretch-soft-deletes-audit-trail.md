# Stretch Goal — Soft Deletes with Audit Trail (L, 3 points)

> Applies to all three project versions. *Site*, *asset*, and *job* stand in for your version's nouns.

## Summary

Deleting a record removes it for good, and nothing records who changed what. This feature replaces destructive deletes with a reversible inactive state, and records every change to an asset or job as an immutable audit entry. Together they make the system's history inspectable and its deletions recoverable — and they give the Auditor role something real to audit.

The `User` model already carries an `is_active` flag; this applies the same idea to the records that matter operationally, and adds the history that flag alone can't provide.

## Workflow

1. An admin deletes an asset. The row is not removed; it is marked inactive, with the acting user and a timestamp recorded.
2. The asset disappears from normal list views and from the analytics counts. Jobs that referenced it keep their reference intact.
3. The admin opens an inactive-records view, finds the asset, and restores it. It returns to normal listings.
4. Meanwhile, every create, update, status change, and delete has written an audit entry naming the record, the action, the acting user, and the time.
5. Any user entitled to view a record can open its history and see those entries in order. No user, of any role, can alter or remove them.

## Requirements

### Functional Requirements

1. Assets and jobs are never removed from the database by the API; a delete marks the record inactive and records the acting user and the time
2. Inactive records are excluded from default list views, filters, and every analytics endpoint answering the business questions
3. An admin can list inactive records and restore one, returning it to normal visibility
4. Every create, update, status change, and soft delete of an asset or job writes an audit entry recording the record type, record id, action, acting user, timestamp, and what changed
5. Audit entries are immutable; no endpoint modifies or deletes one
6. An entry is written if and only if its change is committed — a rejected change leaves no entry, and a committed change never lacks one
7. A record's audit history is retrievable in chronological order
8. Audit history follows record visibility, and the Auditor role can read history wherever it can read the record
9. Soft-deleted records stay referentially intact; existing foreign keys to them continue to resolve

### Non-Functional Requirements

1. The audit entry is written in the same transaction as the change it records, so a rolled-back change takes its entry with it
2. Audit writing lives in one shared helper that every write path calls, rather than being repeated in each route handler
3. The inactive exclusion is applied in the SQLAlchemy statement, not by filtering a loaded result list
4. The audit table is indexed on the record reference so history retrieval does not scan
5. Unit tests cover soft delete, exclusion from listings, restore, entry creation for each action, history retrieval, and the absence of any mutation path

## User Stories

- As an admin, I can delete an asset and restore it later if the deletion was a mistake
- As an admin, I can see which records have been deleted and by whom
- As a user, I can view a record's history: what changed, who changed it, and when
- As an auditor, I can read the history of any record I can see
- As any user, I cannot alter or erase history entries
- As a user, deleted records do not clutter my lists or distort the dashboard numbers

## Technical Notes

- Schema: add `is_active` (or `deleted_at`, which carries the timestamp for free) plus `deleted_by` to the asset and job tables. Add an audit table — id, record type, record id, action, acting user reference, timestamp, and a JSON column holding the changed fields. Both belong on the updated ERD
- Backend: the routers currently talk to the session directly through `Depends(get_db)`, so there is no service layer to hang this on. See the section below — this is the feature where that starts to matter
- The acting user is already available: `get_current_user` returns the `User`, so the audit helper can take it as an argument rather than re-deriving it
- Watch the analytics endpoints specifically. They answer the business questions with their own aggregate queries, and each one needs the inactive filter added — a maintenance-percentage figure that counts deleted assets is wrong in a way nobody notices
- Frontend: an admin-only inactive-records view with a restore action, and a history panel on the asset and job detail views rendering each entry as action, actor, and time
- Decide and document whether an update entry stores the full before and after or only the changed fields. Either works; mixing them makes the history unreadable

## On Adding a Service Layer

Requirement 6 — an entry exists if and only if the change was committed — is the first requirement in this project that the current architecture makes genuinely awkward.

Right now each route handler receives a session through `Depends(get_db)` and writes to it directly. To satisfy requirement 6 that way, every handler that changes a record has to remember to add an audit entry, in the right order, inside the same transaction. It works. It also means the guarantee holds only as long as everyone remembers, and the day someone adds an endpoint and forgets, nothing breaks loudly — the history is just quietly incomplete, which is the one failure mode an audit trail cannot have.

The alternative is a small module sitting between the routers and the session: functions like `update_asset(db, asset, changes, actor)` that perform the write and record the entry together. The router calls one function; the guarantee lives in one place; a new endpoint gets it by construction rather than by diligence.

**The recommendation is to introduce this for the write paths this feature touches, and no further.** That means a module covering create, update, status change, and soft delete for assets and jobs — not a refactor of every read endpoint, and not a repository pattern underneath it. Read paths are fine as they are; they have no invariant to protect.

Two reasons to keep the scope that tight. A full architectural refactor is a large change with no visible result, and it is easy to get stranded halfway through with an application that half-works. And the narrow version actually demonstrates the point better: you can see precisely which problem the layer solves, because it is the problem you were just stuck on.

If you would rather not restructure anything, that is a legitimate choice — write the audit calls inline, and note in your README that the guarantee is maintained by convention. Being honest about where a guarantee actually lives is worth more than the layer itself.

## Definition of Done

- [ ] Deleting an asset marks it inactive; the row still exists in the database
- [ ] Inactive assets and jobs are absent from list views, filters, and every analytics result
- [ ] An admin can view inactive records and restore one; it reappears in normal views
- [ ] Creating, updating, deleting, and changing the status of a record each produce an audit entry with actor and timestamp
- [ ] A record's history returns all entries in chronological order
- [ ] A rejected change leaves no audit entry behind
- [ ] No endpoint exists that modifies or deletes an audit entry
- [ ] A non-admin cannot restore records or view the inactive list
- [ ] Jobs referencing a soft-deleted asset still load without error
- [ ] The audit entity and the new columns appear on the updated ERD
- [ ] Unit tests for the new behavior pass
- [ ] No regressions
