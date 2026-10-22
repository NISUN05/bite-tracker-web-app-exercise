# Edit food entries

Run the integrated `app.py` with the existing MongoDB environment. From Add,
choose **View and edit saved entries**, then **Edit** beside a real record.
`GET /entries` lists stored records in pages of 50, newest dates first.
`GET /meals/<ObjectId>/edit` preloads a record. POST to that URL updates only
its seven supported fields using `$set`, preserving `_id` and extra metadata.
No upsert is performed. The schema and validation are shared with Add:
`date`, `food_name`, `meal`, `calories`, `protein`, `carbs`, `fat`.

The page uses the team's base layout and Add styles. Saving redirects to a
fresh database read; a one-time notice confirms the successful update. Cancel
returns to saved entries without a write. Validation errors retain inputs;
invalid or missing record IDs return 404, invalid input/CSRF return 400, and
database failures return 503 without exposing connection details. Saving an
unchanged record succeeds. Concurrent edits currently use last-write-wins.

Edit requires a session CSRF token generated on GET. Set a stable random
`SECRET_KEY` in the ignored `.env` for multiple workers or persistent sessions;
without one the local process generates a key (restarting expires forms).
This project has no account-based authorization; it is a shared local class
app, not a per-user food diary service.

## Team integration

History/search/homepage owners can link to `url_for('edit_meal',
meal_id=str(document['_id']))`. Do not use the preview's fixture IDs as database
IDs. `/entries` is a small editing entry point and does not replace the assigned
history/search work. The existing fixture edit pages remain labeled previews
and do not save. The standalone `frontend_app.py` remains a UI preview too.

Remaining team work: connect homepage summaries, history/search, and delete to
the same collection and fields; verify the combined workflow on Atlas. README
user-story and task-board links also remain placeholders.

## Verification

Install `requirements-dev.txt`, then run `python -m unittest discover -s tests -v`.
Tests use mocks and mongomock only: Add → list → Edit → stored update → reload,
zero-change saves, validation, CSRF, missing/deleted records, metadata
preservation, HTML escaping, pagination and database failures. These checks do
not establish connectivity to the shared Atlas cluster.

## Additional edit entry point

The teammate's `/edit/<id>` flow is available alongside `/meals/<id>/edit`.
It accepts `item_name` and `meal_category` as form aliases for `food_name` and
`meal`, uses the existing styled form, and redirects to `/history` after saving.
`/history` uses the saved-entry list. Dates remain YYYY-MM-DD strings to match
Add and current sorting; validation and CSRF checks apply to both edit routes.
The supplied snippet's datetime storage and missing-value defaults are not
used, to avoid changing the existing data contract or silently clearing values.

The incomplete Delete POST stub previously prevented the application from
importing. It now returns 501 without modifying data until Delete is implemented;
its separate GET preview is unchanged.
