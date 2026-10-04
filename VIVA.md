# Viva preparation

## 30-second explanation

"FieldGuide is a source-referenced troubleshooting prototype. You select a machine and describe a symptom. It searches approved active manuals, logs and safety documents for that model, shows safety first and quotes relevant passages with section/revision citations. If there is no evidence, a hazard or a tagged contradiction, it escalates instead of inventing a fix. Everything runs locally with Python and SQLite. The demonstration documents are fictional."

## Be honest about ownership and time

The implementation was prepared with AI assistance on October 4. Do not claim it was completed during September, personally authored line by line, field-tested or mentor-validated. You should run it yourself, read the named functions, change a sample source and explain the result before presenting it. Separate your earlier PRD/research work from today's implementation. Do not invent team contributions, challenges or results.

## Likely questions

**Why not an LLM?** A safety-related demo should be inspectable and work without keys. This version uses lexical retrieval and exact quotations. A later LLM layer would need grounded output validation, permission for data transfer and measured comparison against this baseline.

**Is this RAG?** It is a retrieval-and-evidence baseline. It does not currently have an LLM generation stage or vector embeddings. Calling it a full generative RAG system would be inaccurate.

**How do you rank documents?** Tokenize words, remove common/generic terms, weight matched words by their rarity across passages and normalize for length. Exact fault codes get extra weight. Require minimum query coverage before showing manual steps.

**How do you stop hallucinations?** No new repair text is generated. It quotes source passages. That prevents free-form invented steps, but wrong retrieval and wrong source text remain possible, so citations and escalation are still needed.

**Why SQLite?** One local process and a small sample corpus need persistence without infrastructure. It is enough for documents, snapshots and feedback in a viva prototype. Large shared usage would need a different deployment/server plan.

**What is a citation?** A passage ID linked to its document title, revision and original section/page. The modal displays that exact stored passage. PDF input retains extracted page locators, not an original-PDF viewer.

**What about old versions?** Replacement retires the old record in the same transaction. New queries exclude it; historical answer snapshots preserve what was shown at the time.

**How are conflicts found?** Maintainers assign an instruction key/value. Different values for one key on active sources for a machine trigger escalation. Arbitrary contradictions hidden in prose are not automatically detected.

**How are safety cases handled?** Safety documents are always shown first; keyword hazard/bypass requests suppress manual checks. This is not a complete safety classifier or a work permit.

**Can a technician import a file by calling the API directly?** No. The server checks maintainer role and CSRF token. Hiding the import button alone would not be security.

**What did testing prove?** The fixture cases and integration/browser checks work on this small fictional corpus. They do not prove real factory accuracy, reduction in downtime or complete safety coverage.

**What would you improve next?** A mentor-reviewed corpus and evaluation set; better retrieval/paraphrase support; approval/audit governance; source-file viewing and OCR; production authentication and durable hosting; measured usability. Revisit the latest allocation before expanding the project.

## Code walkthrough

1. `init` creates tables and seeds samples.
2. `validate` enforces required metadata and approval.
3. `answer` does exact-model retrieval, scoring and escalation gates.
4. `Handler.do_POST` checks authentication, CSRF and role before mutation.
5. `index.html` renders escaped evidence and citation modals.
6. `test_app.py` shows supported, unsupported, hazard and conflict cases.

## Mandatory WI presentation is different from an app demo

The Kalvium viva notice requests five bullet-point slides, five minutes, covering September 4-October 3, followed by questions. It explicitly excludes code, dashboards, internal screenshots and confidential information. Do not use this app's screenshots in that mandatory deck. Use truthful personal reflections:

1. Context: WI track, technology focus, assigned problem and PRD scope.
2. Work & Ownership: what the team did versus what you actually owned.
3. Challenges & Decisions: one real challenge and the choice you made.
4. Learnings: what you learned technically or professionally.
5. Reflection & Next Steps: what changed and what to do differently next sprint.

Fill in personal examples yourself. Today's new app is next-step work, not evidence of completion before October 3.

## Before your viva: a 20-minute rehearsal

- 0-3 minutes: unzip the project, run `python app.py`, sign in as tech.
- 3-6 minutes: run E101; open its manual citation and explain machine/revision/section.
- 6-9 minutes: run a smoke query and an unknown fault; explain why checks disappear.
- 9-12 minutes: sign in as lead; inspect source metadata and review records.
- 12-15 minutes: read `answer` and `validate`; explain retrieval versus generation.
- 15-18 minutes: run `python -m unittest -v`; say what these sample tests do and do not prove.
- 18-20 minutes: rehearse the 30-second explanation and your own ownership/reflection answers without reading.

## If a mentor asks you to demonstrate the app separately

- Show a supported query, source citation, hazard escalation and unsupported query.
- Explain that the documents and machine models are fictional software fixtures.
- Show source retirement/replacement only if you can explain the transaction and active flag.
- Explain the four result states: answered, safety, conflict and no_answer.
- Keep the official five-slide reflection presentation separate from any app demo.
- Be clear about AI assistance and today's implementation; don't turn a working demo into a claim of earlier personal work.

## What you must fill from your own experience

- Exact WI track name and the current problem statement agreed with your mentors.
- The actual Kalvium team repository and where your earlier contributions live.
- One feature you personally worked on during September 4-October 3.
- One real bug or design problem, your decision, and the outcome.
- What your teammates owned and how you coordinated.
- One technical learning and one change you will make next sprint.

Your journal entries describe research, PRD work, implementation and bug fixing, but do not name the code or bug. Use your memory and actual commits to fill these gaps. Do not substitute a plausible story.

## If the local demo fails

- Check Python version: `python --version` (3.10 or newer).
- Run from the extracted `fieldguide` folder, not from inside the ZIP.
- Keep `app.py`, `index.html` and `corpus.json` together.
- If port 8080 is busy: `python app.py --port 8090`, then open http://127.0.0.1:8090.
- For PDFs only: `python -m pip install -r requirements.txt`; text import needs no install.
- If you changed startup passwords after creating the database, existing user hashes do not change. For sample-only reset, stop the server, delete `fieldguide.db` and restart. Never delete a database containing work you need.
- Sessions expire on restart; sign in again.
- No public URL has been deployed. Prepare your local machine before the viva, rather than relying on a cloud service.
