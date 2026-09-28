# Stretch Goal — Server-Side Pagination, Filtering & Sorting (L, 3 points)

> Applies to all three project versions. *Site*, *asset*, and *job* stand in for your version's nouns — farm/equipment/field job, branch/ATM/service call, hospital/device/work order.

## Summary

The asset list endpoint returns every matching row in one response, and the data grid pages, sorts, and filters those rows in the browser. That is fine against seed data and falls apart against anything larger. This feature moves all three operations into SQL and rewires the grid to consume them, so the client holds one page at a time no matter how big the table gets.

## Workflow

1. A user opens the asset list. The client requests the first page only; the response carries the rows plus the total number of matches.
2. The user types into the search box. The client issues a new request with a filter parameter; the server narrows the query and returns a fresh first page.
3. The user clicks a column header. The client issues a new request with sort parameters; the server orders the rows in SQL.
4. The user moves to the next page. The client requests the next offset; earlier rows are not retained.
5. The grid's pagination controls reflect the total from the response, so they stay accurate without the client ever having seen every row.

## Requirements

### Functional Requirements

1. The asset and job list endpoints accept pagination parameters — a page number and size, or a limit and offset
2. Every paginated response carries both the page of items and the total count of matching records
3. The list endpoints accept filter parameters: at minimum status, site, and a free-text search across model or serial number
4. The list endpoints accept a sort field and a direction
5. The sort field is validated against an allowlist of sortable columns; an unrecognized value is rejected with `422`
6. A maximum page size is enforced on the backend; a request above it is rejected rather than quietly served in full
7. Filtering, sorting, and pagination are expressed in the SQLAlchemy statement, not applied to a fully materialized result list in Python
8. The existing role checks continue to apply to filtered queries; no filter combination returns records a caller could not otherwise see
9. A request with no parameters returns a valid first page in a stable default order

### Non-Functional Requirements

1. Retrieving a page costs one query for the rows and one for the count; related entities are loaded without N+1 queries
2. The sort allowlist is the only source of column names used in ordering; no client-supplied string is interpolated into the statement
3. Columns used for filtering and default ordering carry indexes
4. Unit tests cover page boundaries, both sort directions, each filter, and rejection of an invalid sort field

## User Stories

- As a user, I can page through a large asset list without the application slowing down
- As a user, I can sort a list by a column and have the ordering apply across every page, not just the one on screen
- As a user, I can search and filter a list and see an accurate count of how many records matched
- As a user, an unreasonable page size returns a clear error rather than the entire table
- As an auditor, filtering and sorting never surface records outside what my role permits

## Technical Notes

- Schema: no structural change. Add indexes on the columns you filter and sort by — status, the site foreign key, and whatever the list orders by out of the box
- Backend: the current list endpoint follows the `Query(default=None, ge=…, le=…)` pattern already used for the low-level threshold; extend that approach rather than replacing it. A shared dependency holding `page`, `size`, `sort_by`, and `sort_dir` keeps every list endpoint consistent, and a generic Pydantic response model (`items` plus `total`) gives the frontend one predictable shape. Build your filter conditions once and apply them to both the row statement and the `select(func.count())` statement, so the two can never disagree
- Note that this changes the response shape from a bare list to an envelope. `response_model=list[AssetRead]` becomes `response_model=Page[AssetRead]`, and every component reading `response.data` as an array needs updating. Doing this to one resource first, end to end, is less painful than doing it to all of them at once
- Frontend: MUI DataGrid needs `paginationMode`, `sortingMode`, and `filterMode` all set to `"server"`, plus `rowCount` fed from the response total. Leaving any one on its client default produces a grid that paginates within the current page and looks correct right up until it isn't
- Debounce the search input so a keystroke doesn't become a request

## Definition of Done

- [ ] A list request returns only the requested page, and the response includes the total match count
- [ ] Changing pages issues a new request rather than slicing rows already in the browser
- [ ] Sorting descending puts the true maximum on page one, confirming the ordering is applied in the database
- [ ] Each supported filter narrows results correctly, and filters combine
- [ ] An unrecognized sort field is rejected with `422`
- [ ] A page size above the maximum is rejected rather than served
- [ ] The grid's pagination controls reflect the true total, not the rows currently loaded
- [ ] A role-scoped user's filtered results contain nothing outside their scope
- [ ] Unit tests for paging, sorting, filtering, and invalid input pass
- [ ] Existing list views still render; no regressions
