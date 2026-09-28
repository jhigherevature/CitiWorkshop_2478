# Stretch Goal — Refresh Tokens (M, 2 points)

> Applies to all three project versions. *Site*, *asset*, and *job* stand in for your version's nouns.

## Summary

Login issues one access token with a fixed lifetime, and when it expires the user is dropped back to the login screen mid-task. Shortening the lifetime makes that worse; lengthening it means a stolen token stays useful longer. This feature separates the two concerns: a short-lived access token for requests, and a longer-lived refresh token that can be exchanged for a new one and revoked when needed.

## Workflow

1. A user logs in. The response carries an access token and a refresh token.
2. The client sends the access token with each request, as it does now.
3. The access token expires. The next request comes back `401`.
4. The client sends the refresh token to the refresh endpoint and receives a new access token — and a new refresh token, replacing the one just used.
5. The client retries the original request. The user notices nothing.
6. The user logs out. The refresh token is invalidated on the server; presenting it again fails.

## Requirements

### Functional Requirements

1. A successful login returns both an access token and a refresh token
2. The access token's lifetime is materially shorter than the refresh token's
3. A refresh endpoint accepts a valid refresh token and returns a new access token
4. An expired, malformed, unrecognized, or already-invalidated refresh token is rejected with `401`
5. Refresh tokens are tracked in the database so individual tokens can be invalidated
6. Using a refresh token invalidates it and issues a replacement, so any given refresh token is accepted at most once
7. Presenting a refresh token that has already been used invalidates every token in that chain, on the assumption it was stolen
8. Logging out invalidates the caller's refresh token; a later refresh attempt fails
9. The access token keeps carrying the same `sub` claim the current `get_current_user` dependency relies on
10. The client refreshes once on a `401` and retries; if the refresh also fails it clears its tokens and redirects to login

### Non-Functional Requirements

1. Token lifetimes are settings, not literals — they belong in the `Settings` class alongside `secret_key`, not as module-level constants
2. The refresh endpoint does not require a valid access token, since the entire point is that the access token has expired
3. The refresh token is stored hashed, so reading the table does not yield usable tokens
4. Several requests failing at once trigger one refresh, not one per request
5. Unit tests cover refresh with a valid token, an expired token, a reused token, and refresh after logout

## User Stories

- As a user, I can keep working without being returned to the login screen while my session is still valid
- As a user, I can log out and be confident my session cannot be resumed
- As a user, an expired session ends cleanly at the login screen rather than with a broken page
- As an operator, I can invalidate one compromised session without rotating the signing secret and logging everyone out

## Technical Notes

- Schema: a refresh token table — id, user reference, token hash, issued timestamp, expiry, a revoked flag, and a chain identifier to support requirement 7. It belongs on the updated ERD
- Backend: `create_access_token` and `decode_access_token` already take an optional `expires_delta`, so the access side needs little change beyond moving `ACCESS_TOKEN_EXPIRE_MINUTES` into settings and shortening it. Add the refresh path beside the existing token endpoint rather than reworking it. Rotation plus reuse detection is the part worth getting right — it is what makes a stolen refresh token detectable rather than merely long-lived
- Frontend: `apiClient` in `src/api/client.js` has a request interceptor and no response interceptor; the retry belongs in a response interceptor there. Guard it against two failure modes: a failed refresh must not itself trigger a refresh, and several simultaneous `401`s must share one in-flight refresh rather than each starting their own. `AuthContext` owns the token today, so decide whether it or the interceptor owns the refresh, and keep it in one place
- Where the refresh token lives in the browser is a real decision with real tradeoffs. The access token is in `localStorage` today. Make a choice, write down the reasoning, and be consistent

## Definition of Done

- [ ] Login returns both tokens
- [ ] A request with an expired access token returns `401`
- [ ] Exchanging a valid refresh token returns a new access token and a new refresh token
- [ ] The refresh token used in that exchange is no longer accepted
- [ ] Presenting a previously used refresh token is rejected and invalidates the rest of that chain
- [ ] Logging out invalidates the refresh token; refreshing afterward fails with `401`
- [ ] The frontend recovers from an expired access token without the user seeing an error or a login screen
- [ ] Several simultaneous expired requests trigger one refresh, not several
- [ ] A failed refresh clears client state and redirects to login
- [ ] Token lifetimes are configurable through settings
- [ ] Unit tests for the new behavior pass
- [ ] Existing login and role checks still work; no regressions
