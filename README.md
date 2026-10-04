# FieldGuide

Source-referenced equipment troubleshooting prototype for Kalvium Semester 5, Sprint 2, Team 01.

A technician chooses a machine and describes a fault. FieldGuide finds matching approved passages, shows safety first, and links every displayed passage to the original source and revision. It refuses unsupported questions and flagged hazards. A maintenance lead imports, replaces or retires documents and reviews feedback.

**This is a local demonstration, not validated industrial advice. All bundled equipment documents are fictional software-test fixtures. Never use them on real equipment.** Built on October 4, 2026; no claim that this implementation existed earlier in the sprint.

## Run in 60 seconds

Requires Python 3.10 or newer. The core app has no third-party dependencies or API keys.

```sh
python app.py
```

Open http://127.0.0.1:8080. On Windows, use `py app.py` if `python` is unavailable.

Local sample accounts:

| Role | Username | Demo password |
|---|---|---|
| Technician | tech | demo-tech-2026 |
| Maintenance lead | lead | demo-lead-2026 |

These are non-secret fixture credentials, not real account passwords. The app refuses a non-loopback binding with default credentials. Do not store confidential documents in this demo.

Optional PDF import:

```sh
python -m pip install -r requirements.txt
python app.py
```

Text and Markdown import always work. PDFs must have extractable text, be unencrypted and at most 1 MB / 100 pages. OCR is not included.

## Demo flow

1. Sign in as `tech`. Pick CV-100 and use E101 / belt not moving.
2. Read safety, then open the E101 source citation. It shows section and revision.
3. Mark the answer helpful and open Review log to see the answer snapshot.
4. Ask "smoke and sparks". No repair checks appear; it escalates.
5. Ask "quantum calibration failure". No invented fix appears.
6. Sign out, sign in as `lead`, then open Source library.
7. Import an approved text file with metadata. Replace a selected active revision or retire one. New queries exclude retired passages.
8. For a conflict demo, import two manual documents for CV-100 with conflict key `restart-policy` and different conflict values. All CV-100 queries escalate until the conflicting source is retired or corrected.

## What is implemented

- Responsive browser UI with technician and maintenance-lead roles.
- Machine-scoped approved/effective/active source selection.
- Text/Markdown ingestion; optional text-PDF extraction with page locators.
- Passage metadata, revisions, replacements and retirement.
- TF-IDF-style lexical ranking, exact fault-code boosts and query-coverage gating.
- Extractive answer assembly: exact quotations, not free-form LLM generation.
- Safety-first passages, hazard keywords, explicit tagged-source conflicts, no-answer states.
- Original-source modal for each citation.
- SQLite query snapshots, retrieval IDs and helpful/unsafe feedback.
- Role checks, salted PBKDF2 passwords, session cookies, CSRF protection, bounded upload sizes.
- Reproducible tests and optional browser smoke tests.

## Design choices

The PRD does not require a particular framework or paid model. Python standard-library HTTP + SQLite keeps the viva demo reliable and explainable. No cloud dependency, API quota or cold start is needed for a local demo. The corpus is small, so ranking on query is simpler than a vector database. Log passages are history only, never repair instructions. See [VIVA.md](VIVA.md) and [ARCHITECTURE.md](ARCHITECTURE.md).

## Testing

```sh
python -m unittest -v
```

The test set includes 20 question cases plus rejection, retirement, safety-source and tagged-conflict checks. These are developer-created fixture tests, not mentor-reviewed validation or a field trial. No downtime-reduction or under-60-second user-study result is claimed.

Optional browser smoke test:

```sh
npm install --no-save --package-lock=false playwright
npx playwright install chromium
node visual-test.cjs
```

## Deployment and data

Local hosting costs nothing. Docker configuration is included for reproducible local use. A public server is **not deployed**. `render.yaml` describes a free-tier demo option, but deployment needs the owner's chosen account and generated password secrets. Free tiers may sleep or lose local disk, so a local demo is the reliable viva fallback.

SQLite creates `fieldguide.db` on first run. It is ignored by Git. Back it up privately. To reset the demo, stop the app and remove the database file. Startup password environment variables apply only when the user rows are first created, not as a password rotation mechanism.

For deployment, start with a fresh database and set both `FIELDGUIDE_ADMIN_PASSWORD` and `FIELDGUIDE_TECH_PASSWORD`, then use `python app.py --host 0.0.0.0`. Use HTTPS termination, a restricted network, a production server, durable storage, rate limits and proper identity management before any real use. This prototype is not security-audited.

## Known limits / PRD gaps

- No LLM, embeddings or semantic paraphrase understanding. Lexical retrieval can miss relevant passages or match a wrong passage with shared words. Read every original citation.
- Conflict handling is explicit metadata, not automatic comprehension of contradictions in prose. Importers must identify/tag conflicts. All tagged conflicts on a machine stop answering conservatively.
- Hazard detection is keyword-based, not a complete industrial safety system.
- No OCR, original-PDF viewer, source-file retention or cryptographic approval attestation. PDF citations show extracted text and the original page number, not the PDF image.
- Approved status is asserted by the maintainer. Real approval governance is outside this app.
- No real company documents, real factory testing, telemetry, automatic repairs or machine control.
- Sessions are in memory. Restarting signs users out. No password-reset UI, login throttling, SSO or multi-tenant isolation.
- Query logs contain submitted text; use only non-confidential samples until a proper permission and retention policy exists.
- Mentor-reviewed evaluation and timed usability testing remain outstanding.

Example local Docker demo (fixture-only passwords, bind host port to loopback):

```sh
docker build -t fieldguide .
docker run --rm -p 127.0.0.1:8080:8080 -e FIELDGUIDE_ADMIN_PASSWORD=demo-lead-2026 -e FIELDGUIDE_TECH_PASSWORD=demo-tech-2026 fieldguide
```

This container's database is ephemeral. Use a private writable volume if retaining data. Do not publish its default accounts on the internet.
