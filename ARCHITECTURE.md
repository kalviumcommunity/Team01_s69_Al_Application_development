# Architecture

Browser UI (index.html) -> same-origin JSON API (app.py) -> SQLite.

## Files

- `app.py`: schema, validation, retrieval, auth and API handlers.
- `index.html`: responsive UI and same-origin fetch calls. User/source text is HTML-escaped before rendering.
- `corpus.json`: five fictional demonstration documents; never real machine instructions.
- `test_app.py`: deterministic retrieval/validation tests.
- `test_api.py`: auth, roles, ingestion, PDF and revision integration tests.

## Data model

Documents hold machine, type, revision, effective date, owner, approved/active flags and optional conflict metadata. Passages hold exact source text and page/section locators. Queries store a full evidence snapshot so later retirement does not rewrite history. Feedback references a query. Users hold role, salt and PBKDF2 password hash, not plaintext passwords.

## Query path

1. Validate machine and question size; require an authenticated session.
2. Select only active approved documents for the exact machine.
3. Remove stopwords/generic machine terms from the query.
4. Rank passages by word overlap weighted by rarity and length, boosting exact fault codes.
5. Require manual evidence with a minimum coverage gate. If a fault code is supplied, retain only code-matching manual passages.
6. Stop for missing sources/safety, tagged conflict, hazardous keywords or no matching manual evidence.
7. Otherwise show verbatim manual evidence after safety; show logs in a separate history section.
8. Store query, result, evidence IDs, revision text and timestamp; return them to the UI.

No model generates a new repair step. Source citations prove provenance of the displayed text, not correctness of the source or suitability for a real machine.

## Replacement

Validate the new revision first, insert it and retire the selected old revision in one SQLite transaction. Replacement requires the same model and type. Retired passages remain available in historical snapshots and source archive but are excluded from new retrieval.

## Security boundaries

Technicians can query, inspect sources and submit feedback for their own queries. Leads can import, retire and see all query records. Both POST role gates and CSRF checks run on the server, not only in hidden buttons. Cookies are HttpOnly and SameSite=Strict. This is still a development server with no anti-brute-force protection. Restrict to local demonstration use.
