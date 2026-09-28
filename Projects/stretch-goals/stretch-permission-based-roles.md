# Stretch Goal — Permission-Based Roles (L, 3 points)

> Applies to all three project versions. *Site*, *asset*, and *job* stand in for your version's nouns.

## Summary

Authorization is currently expressed as role names written into each endpoint — `require_role(UserRole.ADMIN)` and so on. Every new role means editing every endpoint that role should reach, and answering "what can an auditor actually do?" means reading the whole router package. This feature replaces role checks with named permissions: roles become sets of permissions stored as data, and endpoints declare the permission they need rather than the roles they accept.

The three existing roles must behave exactly as they do today when the work is finished. This is a refactor with a capability added, not a change in who can do what.

## Workflow

1. An endpoint declares the permission it requires, for example `asset:write`, instead of listing the roles allowed to call it.
2. A request arrives. The dependency resolves the caller's role to its permission set and checks whether the required permission is present.
3. A caller without that permission receives `403`, exactly as before.
4. An admin opens a roles view and sees each role alongside the permissions it holds.
5. A new role is introduced by defining its permission set. No endpoint code changes.

## Requirements

### Functional Requirements

1. Permissions are defined as named values covering the application's operations — at minimum reading and writing assets, reading and writing jobs, changing job status, uploading reports, reading analytics, reading audit history, and managing users
2. A role is a set of permissions, stored as data rather than expressed in endpoint code
3. Endpoints declare a required permission; no endpoint names a role directly
4. A caller lacking the required permission receives `403` with a message naming the missing permission rather than the caller's role
5. The three existing roles are reproduced exactly as permission sets, and every endpoint remains reachable by precisely the roles that reach it today
6. Adding a role requires no change to any endpoint
7. An admin can view all roles and the permissions each holds
8. The frontend hides controls the current user lacks permission for, and the backend still rejects the request if one is invoked anyway
9. A role's permissions are resolved per request, so a role's definition changing does not require reissuing tokens

### Non-Functional Requirements

1. Permission names are defined in one place and referenced everywhere; no endpoint contains a permission string literal that exists nowhere else
2. The permission check is a FastAPI dependency, consistent with how authorization is already expressed
3. The frontend derives its visibility rules from permissions supplied by the API, not from a second copy of the rules written in JavaScript
4. Unit tests cover each role against a representative endpoint per permission, including the negative cases
5. Every endpoint carries an authorization dependency; none is left unprotected by the refactor

## User Stories

- As an admin, I can see exactly what each role is allowed to do without reading the source
- As an admin, I can introduce a new role without a developer editing endpoints
- As a developer, I can add an endpoint by declaring the permission it needs, without knowing which roles hold it
- As a technician, I see only the controls I can actually use
- As an auditor, I can read everything I could read before and write nothing, exactly as before

## Technical Notes

- `require_role(*allowed_roles)` in `app/dependencies.py` is the seam. Introduce `require_permission(permission)` beside it, migrate endpoints one router at a time, and delete `require_role` once nothing calls it. Keeping both during the migration means the application keeps working between commits
- Where permissions live is the design decision. A dictionary mapping role to permission set is the simplest form and satisfies most of the requirements; a database table satisfies requirement 6 more convincingly and is what makes role management a real feature rather than a constant. Either is defensible — pick one, write down why, and note that the table version needs seed data so a fresh database has working roles
- The token carries the role in its `sub`-based payload today and `get_current_user` loads the `User` from the database on every request anyway, so permissions can be resolved from the loaded user without touching token issuance. That is what makes requirement 9 free
- Frontend: expose the current user's permissions from the endpoint that already returns their identity, hold them in `AuthContext` alongside the role, and gate controls on permission checks. Hiding a control is a courtesy; the `403` is the actual boundary
- The migration is the risky part, not the design. An endpoint accidentally left without a dependency is an endpoint open to everyone, which is why requirement 5 and the last non-functional requirement are both worth checking deliberately

## Definition of Done

- [ ] Permissions are defined in one module and referenced by name throughout
- [ ] Every endpoint declares a required permission; no endpoint names a role
- [ ] Each of the three roles reaches exactly the endpoints it reached before the refactor, confirmed by tests
- [ ] A caller lacking a permission receives `403` naming the missing permission
- [ ] A new role can be added and behaves correctly with no endpoint code changed
- [ ] An admin can view roles and their permissions
- [ ] The frontend hides controls the user lacks permission for
- [ ] Invoking a hidden control directly against the API is still rejected
- [ ] No endpoint is left without an authorization dependency
- [ ] Unit tests cover every role against every permission boundary
- [ ] No regressions in login or existing access behavior
