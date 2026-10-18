# Independent engineering audit

This is evidence for a human-reviewed remediation pass. No application behavior,
test, notebook, workflow, or other document was changed. No live provider API
was called, nothing in Databricks was touched, and no credential or personal
information was read or recorded.

## 1. Audit identity and method

| Item | Value |
| --- | --- |
| Audited commit | `8cf008b` ("Clarify schema quality boundaries", 2026-10-17). The checked-out `HEAD` is `5b6dc01` ("Initial plan"), an empty commit; `git diff --stat 8cf008b HEAD` is empty, so the audited tree is identical. |
| Base branch | `codex/dq-10-source-schema-quality-rules` (provided as the base branch for this stacked pull request). |
| Scope | The entire tree at that commit: 53 tracked files (all listed in section 2), not a diff. |
| Environment | Python 3.12.3, the same minor version as CI. `coverage`, `pyflakes`, `mypy`, and `ruff` were installed only for this audit and nothing was added to the repository. `pyspark` is not installed. |

Labels used below:

- **Verified** means I executed it or read the exact lines cited.
- **Inferred** means it follows from code or documentation but I could not
  exercise it here, for example Databricks runtime behavior.

## 2. Review-scope inventory

Every tracked file was opened and read, except the seven PNG screenshots. For
those I looked at five images and inspected the metadata of all seven (see
section 4).

### 2.1 Python source (`src/`, 9 files)

- `src/data_quest/__init__.py`
- `src/data_quest/ingestion/__init__.py`
- `src/data_quest/ingestion/datausa.py`
- `src/data_quest/ingestion/discovery.py`
- `src/data_quest/ingestion/download.py`
- `src/data_quest/ingestion/landing.py`
- `src/data_quest/ingestion/manifest.py`
- `src/data_quest/ingestion/spark_manifest.py`
- `src/data_quest/validation/__init__.py` (docstring only)

### 2.2 Databricks notebooks (2 files)

- `notebooks/01_land_bls.py`
- `notebooks/02_land_datausa_population.py`

### 2.3 Pipeline and SQL artifacts (2 files, placeholders only)

- `pipelines/README.md`
- `sql/alternatives/README.md`

No pipeline, Spark SQL, or PySpark transformation code exists yet, so Bronze,
Silver, and Gold are contract-only.

### 2.4 Tests (8 files)

- `tests/README.md`
- `tests/test_datausa.py`
- `tests/test_discovery.py`
- `tests/test_download.py`
- `tests/test_landing.py`
- `tests/test_manifest.py`
- `tests/test_package_smoke.py`
- `tests/test_spark_manifest.py`

### 2.5 GitHub configuration (2 files)

- `.github/workflows/quality.yml`
- `.github/pull_request_template.md`

### 2.6 Configuration (2 files)

- `.env.example`
- `.gitignore`

There is no `pyproject.toml`, `setup.cfg`, `requirements*.txt`, lock file,
Databricks bundle, or linter/type-checker configuration. The task text mentions
requirements; the only requirements-like artifact is `REQUIREMENTS_CHECKLIST.md`
(see 2.7).

### 2.7 Contract and documentation files (20 files)

- `README.md` (the quest brief)
- `PROCESS.md`
- `REQUIREMENTS_CHECKLIST.md`
- `docs/BLS_LANDING_RUNBOOK.md`
- `docs/BLS_SOURCE_PROFILE.md`
- `docs/DATAUSA_LANDING_RUNBOOK.md`
- `docs/INGESTION_MANIFEST_CONTRACT.md`
- `docs/INGESTION_RERUN_EVIDENCE.md`
- `docs/LOGICAL_DATA_MODEL.md`
- `docs/PRODUCT_ONE_PAGER.md`
- `docs/PROJECT_CONVENTIONS.md`
- `docs/QUALITY_ASSURANCE_PROTOCOL.md`
- `docs/REQUIRED_GOLD_CONTRACTS.md`
- `docs/SOURCE_SCHEMA_QUALITY_CONTRACT.md`
- `docs/SYSTEM_UML.md`
- `docs/evidence/README.md`
- `docs/evidence/dq08_first_reconciliation.csv`
- `docs/evidence/dq08_first_run.csv`
- `docs/evidence/dq08_no_change_reconciliation.csv`
- `docs/evidence/dq08_no_change_run.csv`

### 2.8 Evidence images (8 files)

- `docs/screenshots/README.md`
- `docs/screenshots/dq07_first_run_reconciliation.png`
- `docs/screenshots/dq07_no_change_counts_publication.png`
- `docs/screenshots/dq07_no_change_counts_unchanged.png`
- `docs/screenshots/dq07_no_change_reconciliation.png`
- `docs/screenshots/dq08_no_change_counts.png`
- `docs/screenshots/dq08_reconciliation_identity.png`
- `docs/screenshots/dq08_reconciliation_schema.png`

Total: 9 + 2 + 2 + 8 + 2 + 2 + 20 + 8 = 53, matching `git ls-files | wc -l`.

## 3. Commands and checks run

All commands ran from the repository root with no network access to providers.

| # | Command | Result |
| --- | --- | --- |
| 1 | `python -m compileall -q src tests` (the CI step) | Pass. |
| 2 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests` (the CI step) | **66 tests pass, 0 failures.** A counting result class shows 11 subtests also executed. That matches `PROCESS.md`'s "66 tests plus 11 subtests". |
| 3 | `coverage run --branch --source=src -m unittest discover -s tests`, then `coverage report -m` | **86 % total** (611 statements, 64 missed; 220 branches, 50 partial). Per file: `datausa.py` 76 %, `download.py` 77 %, `landing.py` 92 %, `manifest.py` 90 %, `spark_manifest.py` 91 %, `discovery.py` 94 %. Missed lines are listed in section 7. |
| 4 | `python -m pyflakes src tests` | Clean. |
| 5 | `python -m pyflakes notebooks` | Only `undefined name 'dbutils'`, `'spark'`, and `'display'`, which Databricks injects. No other findings. |
| 6 | `mypy src` | `Success: no issues found in 9 source files`. |
| 7 | `ruff check src tests` (the repository has no ruff config, so the rule set is whatever this sandbox's ruff applied) | 35 style and modernisation hints: `I001` import order, `UP017` `datetime.UTC`, `UP035` `collections.abc`, `SIM117` nested `with`, `FURB167`, `RUF100` unused `noqa: N802`, `PYI034`, and `TRY004` (see L-9). None indicate a runtime defect. |
| 8 | `git diff --check` against the parent | Clean. |
| 9 | Secret and personal-data scan: `git grep` for email-shaped strings, tokens, passwords, `dapi…`, and `adb-…` or `*.databricks` hosts | No credentials, workspace hosts, or real contact addresses. Only the placeholder `your-email@example.com` and test addresses `owner@example.org` appear. One test fixture uses a credential-shaped URL with fake values, which is intentional. |
| 10 | Screenshot review | I viewed five of the seven PNGs (`dq07_first_run_reconciliation`, `dq07_no_change_counts_unchanged`, `dq07_no_change_reconciliation`, `dq08_no_change_counts`, `dq08_reconciliation_schema`). They show only run IDs, byte counts, and digest prefixes, with no email, workspace host, or user name. I did **not** visually inspect `dq07_no_change_counts_publication.png` or `dq08_reconciliation_identity.png`, because the image-viewing limit was reached. For all seven I parsed the PNG chunks: only macOS EXIF/XMP screenshot metadata (`UserComment: Screenshot`) is present, with no author, host, or text chunks. |
| 11 | Read-only probes in `/tmp` (not committed) against `validate_population_response`, `discover_file_links`, and `download_to_staging` with fake openers | Results are quoted in the findings they support (M-2, M-4, M-5). |

Not run, with reasons: Databricks notebooks and Spark paths (no pyspark here,
and mutation is out of scope); any live BLS or Data USA request; any linter or
type check that the repository itself configures (none is configured).

## 4. Findings

Severity scale:

- **Critical**: silent data loss or corruption, or a credential breach, with no
  practical mitigation.
- **High**: a plausible silent-wrong-result path.
- **Medium**: a real defect or gap that fails loudly, or a weakness with a
  limited trigger.
- **Low**: hygiene or maintainability.

Line numbers refer to the audited commit.

### Critical

**None.** I found no secret, credential, or personal data in tracked files or
screenshot metadata. I also found no defect that corrupts immutable raw bytes
or overwrites a version the manifest references. Content-addressed paths,
post-promotion re-verification, and the promote-then-append ordering hold in
code (`download.py:200-247`, `landing.py:172-238`).

### High

#### H-1. A truncated but non-empty directory listing is treated as a complete inventory and tombstones every missing file

- **Where:**
  - `landing.py:143-148` hard-codes `inventory_complete=True, downloads_complete=True`.
  - `manifest.py:169-235` turns every active path absent from the observed set into a `REMOVED` entry.
  - `discovery.py:184-187` rejects only an *empty* result.
  - `notebooks/01_land_bls.py:88-94` discovers the files, `:103-113` prepares the landing, `:131-142` reconciles active paths to discovery, and `:144-149` verifies committed objects.
- **Impact:**
  - If BLS returns a partial or degraded page (a proxy error page with one link, or a changed layout where only some anchors parse), the run succeeds. It writes tombstones for the files it did not see.
  - The reconciliation `assert` then passes, because active paths equal the (truncated) discovered paths.
  - Per `docs/SOURCE_SCHEMA_QUALITY_CONTRACT.md` ("reads only the active manifest versions"), Bronze would silently stop seeing those files.
  - Raw bytes remain on the Volume, so this is recoverable, but nothing flags it.
- **Evidence:**
  - **Verified:** `inventory_complete` and `downloads_complete` are caller-asserted booleans, never computed, and the only production caller passes literal `True`. The test `test_incomplete_inventory_cannot_publish_a_plan` (`tests/test_manifest.py:135`) therefore proves only that the flag is honored.
  - **Verified:** `docs/INGESTION_MANIFEST_CONTRACT.md` states that the empty-listing rejection "prevents that failure from being interpreted as mass removal". This holds only for zero links.
  - **Inferred:** the provider-side trigger is plausible but not observed.
- **Remediation:**
  - Add a removal guard in `plan_manifest_changes` or the landing layer. For example, require `pr.data.1.AllData` and `pr.series` to be present, or fail when more than N % of active paths would be tombstoned, unless an explicit `allow_mass_removal` override is supplied.
  - Drop the misleading `inventory_complete` and `downloads_complete` parameters, or derive them from real state.
  - Add tests covering a 1-of-12 listing and the override.

### Medium

#### M-1. A deleted or corrupted landed object is never repaired; reconciliation fails on every subsequent run

- **Where:**
  - `landing.py:194-216`: only `NEW` and `CHANGED` changes call the promoter.
  - `manifest.py:251-259`: matching size and SHA-256 gives `UNCHANGED`.
  - `notebooks/01_land_bls.py:144-149` and `notebooks/02_land_datausa_population.py:141-146` verify the objects only *after* publication.
- **Impact:**
  - If an object under `objects/<sha>/…` is lost or damaged (manual cleanup, Volume incident), the run just downloaded identical, verified bytes but discards them. The classification stays `UNCHANGED`.
  - The final verification raises `DownloadIntegrityError` on every rerun with no automated recovery path.
  - This contradicts the stated "retry … safely compares against committed state" recovery story.
- **Evidence:**
  - **Verified by reading:** no code path re-promotes bytes for an `UNCHANGED` entry.
  - **Verified by reading:** no test covers an `UNCHANGED` entry whose landed object is missing.
- **Remediation:**
  - If the expected object is missing, verify the staged bytes against the manifest's size and digest, then promote them before publishing any transitions.
  - If the destination exists but fails verification, do not retry the normal promoter: it deliberately refuses to overwrite conflicting bytes. Keep publication blocked and preserve the damaged object in quarantine. Restore the expected bytes from a trusted copy, or use a coordinated operator recovery with concurrent readers and writers stopped to quarantine the bad destination and promote the verified staged copy. Verify the restored size and digest before resuming; do not silently overwrite the immutable path.

#### M-2. Discovery rebuilds source URLs from the percent-decoded path, so the requested URL can differ from the linked URL

- **Where:** `discovery.py:155` (`unquote`), `:164-182` (the canonical URL is built from the decoded path with `urlunsplit` and never re-quoted).
- **Impact:**
  - A link containing `%25` or `%20` is requested as a different or invalid URL.
  - **Verified probe:** `href="…/a%2541.txt"` becomes `name='a%41.txt'`, `url='…/a%41.txt'`. That URL addresses `aA.txt`, a different object. `href="…/a%20b.txt"` becomes `url='…/a b.txt'`.
  - A space in the request path raises `http.client.InvalidURL`, which is not caught by the retry or `SourceRequestError` handling (see M-5), so the whole run aborts with a raw exception.
  - The wrong-object case is silent: it records content from an unintended URL under a misleading `relative_path`.
  - The current BLS names are plain ASCII, so there is no known occurrence today.
- **Remediation:** keep the original (still-encoded) path segment for the URL, and use the decoded segment only for the display name, validating it after decoding. Reject names containing `/`, `\`, control characters, or `%` after decoding. Add tests for `%25`, `%20`, `%2F`, and a backslash.

#### M-3. The redirect-origin check runs only after the cross-origin request has been sent, and discovery has no check at all

- **Where:** `download.py:81-90` (a response URL check after `opener(...)` returns), `discovery.py:76-78` (no origin check), `datausa.py:176-188` and the notebooks (the same `User-Agent` is used for Data USA).
- **Impact:**
  - `urllib.request.urlopen` follows redirects automatically, including `https`→`http`. The `User-Agent`, which carries the owner's contact email, is already sent to the redirect target before `SourceRedirectError` is raised.
  - The test `test_rejects_cross_origin_redirect_before_writing` (`tests/test_download.py:203`) models only the post-hoc response, so it cannot detect this.
  - The directory listing is parsed even if it came from another origin. Link filtering is relative to the configured origin, so the blast radius is limited to inventory content.
  - `README.md` and `docs/BLS_LANDING_RUNBOOK.md:14` claim the email is "sent only in the BLS `User-Agent`", but notebook 02 also sends it to `honolulu-api.datausa.io` (`notebooks/02_land_datausa_population.py:74`), a separate third party.
- **Remediation:**
  - Use a custom `HTTPRedirectHandler` (or `build_opener` with a redirect validator) that refuses off-origin and scheme-changing redirects *before* following them. Apply it to both discovery and download.
  - Use a distinct `User-Agent` for Data USA that does not include the personal email, or document that disclosure.

#### M-4. Data USA accepts non-standard JSON numeric constants

- **Where:** `datausa.py:45` uses Python's default `json.loads` parser; `:103-111` checks population type and nonnegativity but not finiteness.
- **Impact:** Python's parser accepts `NaN`, `Infinity`, and `-Infinity`, although these are not JSON numeric values. **Verified by probe:** a record with `Population: NaN` passes validation because `NaN < 0` is false. Positive infinity also passes the shown type and nonnegative checks. This conflicts with `PROCESS.md:75`, which requires valid UTF-8 JSON before publication.
- **Scope:** Exact top-level and pagination keys, ordered columns, and population finiteness/integrality are specified for Bronze and Silver in `SOURCE_SCHEMA_QUALITY_CONTRACT.md:137-150,218-239`; the document explicitly defers those pipeline rules to DQ-11–DQ-15 at `:249-253`. Their absence from raw landing is not a landing defect.
- **Remediation:**
  - Parse with `parse_constant` raising on `NaN`, `Infinity`, and `-Infinity`.
  - Add negative tests confirming each constant is rejected before promotion.

#### M-5. Several failure modes escape the bounded retry and error-wrapping design

- **Where:** `download.py:81-158` (handlers catch `HTTPError`, `URLError`, `TimeoutError`, `OSError` during reads, and the project's own errors) and `discovery.py:74-106`.
- **Impact:**
  - `http.client.IncompleteRead` (a chunked body cut short, which is the way a Content-Length-less response such as an API JSON endpoint is truncated) and `http.client.InvalidURL` (see M-2) are `HTTPException`s, not `OSError`s.
  - **Verified probe:** a fake response whose `read()` raises `IncompleteRead` propagates as a raw `IncompleteRead`. There is no retry, and the `.partial` file is left on disk.
  - The staging tree is later removed by `landing._cleanup_tree`, but a direct caller of `download_to_staging` is exposed.
  - Byte-count verification therefore protects only responses that carry `Content-Length`. Others rely on later parsing (JSON for Data USA, nothing for BLS text files).
  - `mkdir` and `open` failures at `download.py:96-97` raise raw `OSError` rather than `StagingWriteError`.
- **Remediation:**
  - Catch `http.client.HTTPException` alongside `URLError` and treat it as retryable (except `InvalidURL`, which is a hard failure).
  - Remove the partial file in a `finally`, wrap staging `OSError`s, and add tests for `IncompleteRead`, chunked truncation, and `InvalidURL`.

#### M-6. Several tests can pass while the behavior they name is wrong (false-positive risk)

- `tests/test_spark_manifest.py:98-120`, "loads only the latest manifest state": the fake returns one canned row, so the ranking SQL is never executed. The test asserts that substrings appear in the SQL text. A wrong `ORDER BY`, a wrong partition key, or a broken tie-break would still pass.
- The same file's `ensure_manifest_table`, append, and identifier tests assert on strings and on a fake writer. Nothing checks column order against the DDL or NOT NULL handling. No real Spark (local or Databricks) test exists in CI.
- `test_rejects_cross_origin_redirect_before_writing` (see M-3) and `test_incomplete_inventory_cannot_publish_a_plan` (see H-1) test the guard but not the real scenario.
- `tests/test_download.py:250-282` tests reuse of an existing matching object by the real promoter, and `:311-332` tests that conflicting existing bytes are refused. However, `tests/test_landing.py:180-256` mocks promotion, so no test exercises `execute_landing_plan` with the real promoter and filesystem together.
- **Remediation:**
  - Add an orchestration test using the real promoter and filesystem: stage, promote, publish to an in-memory fake, then rerun with the unchanged object's path missing and verify the intended recovery before publication.
  - Add a local-Spark or Databricks CI job (or at least a documented manual gate) for the manifest query.
  - Remove or rename tests that claim more than they check.

### Low

- **L-1. `ingested_at_utc` is the run *start* time, not the transition time.**
  - `notebooks/01_land_bls.py:85` and `notebooks/02_land_datausa_population.py:88` capture it before discovery and downloads. `docs/INGESTION_MANIFEST_CONTRACT.md` defines it as "timestamp of the successful state transition".
  - `spark_manifest.py:70-73` uses it, together with the lexical `run_id`, to pick the latest row. Overlapping runs (not supported) or a backward clock step can mis-order rows, and a duplicate `(relative_path, ingested_at_utc, run_id)` is non-deterministic.
  - Remediation: stamp at publish time, or add a monotonic sequence column. Add a unique `(relative_path, run_id)` check.
- **L-2. Naive timestamps from Spark are relabelled UTC.** `spark_manifest.py:87-90` assumes any naive `datetime` is UTC. PySpark returns naive values in the Python process's local zone. The result is correct only if the driver zone is UTC, **inferred** from PySpark semantics and untested. Impact is limited because retained `UNCHANGED` entries are never rewritten. Remediation: set and assert `spark.sql.session.timeZone` and the driver TZ to UTC, or select `unix_micros`/an explicit UTC cast.
- **L-3. The manifest table has no constraints.** `spark_manifest.py:26-46` creates a Delta table with NOT NULLs only. There is no `CHECK` for `status IN ('active','removed')`, the digest format, or non-negative sizes. `CREATE TABLE IF NOT EXISTS` does not verify that an existing table's schema matches. Remediation: add Delta CHECK constraints and a schema-match check.
- **L-4. Manifest and path validation gaps.**
  - `manifest.py:305-317` and `download.py:171-197` accept backslashes, newlines, NUL, and other control characters in `relative_path`.
  - `manifest.py:299-302` does not reject embedded credentials or fragments in `source_url`, although `download.py` does.
  - No cross-field invariants are checked: `source_content_length` vs `content_size_bytes`, or `landed_path` containing the digest and `relative_path`.
  - Remediation: centralize validators and add negative tests.
- **L-5. Contact-email validation is weak and inconsistent.**
  - `discovery.py:225-229` and `download.py:315-319` duplicate a regex and reject only the literal `your-email@example.com`. Any `@example.com`, `@localhost.xx`, or `a@b.co` passes.
  - The notebooks use a different regex (`notebooks/01_land_bls.py:61`, `notebooks/02_land_datausa_population.py:62`). **Verified:** `a@b.c` passes the notebooks but fails the library, so the failure surfaces late as a `ValueError` from deep in the run.
  - The `User-Agent` product token differs: `.env.example:3` says `data-quest/0.1`, the notebooks say `rearc-data-quest/0.1`.
  - Remediation: a single shared validator and constant.
- **L-6. `.env.example` is disconnected from the notebook configuration.** No code reads its `BLS_BASE_URL`, `BLS_USER_AGENT`, `DATAUSA_POPULATION_URL`, or `DATABRICKS_*` values. The notebooks accept deployment-specific catalog, schema, and Volume values through widgets (`01_land_bls.py:56-73`; `02_land_datausa_population.py:57-78`), so this does not establish that those object names are fixed deployment targets or violate the configuration convention. Remediation: document how the example settings map to supported widget inputs, or remove the unused example entries.
- **L-7. Unbounded and unclosed reads.** `discovery.py:78` reads the entire directory page into memory with no size cap. `download.py` has no maximum object size, so a hostile or faulty source can fill the Volume. `discovery.py:79-93` does not `close()` an `HTTPError` (the download path does, at `download.py:152`). Remediation: add `max_bytes` limits and close the error.
- **L-8. The `SourcePolicyError` text names BLS in all contexts.** `download.py:139-141` and `discovery.py:82-84` say "review the BLS access policy" even for a Data USA 403. Remediation: make the provider name a parameter.
- **L-9. Maintainability and duplication.**
  - Copy-pasted: the run-ID regex (`manifest.py:19`, `landing.py:26`), the SHA-256 regex (`manifest.py:18`, `download.py`), the email check (L-5), `ObservedFile` and `ManifestEntry` validation, `_IDENTIFIER_PART` plus the notebooks' inline identifier regex, and the two notebooks (about 85 % identical).
  - Reconciliation logic is untested and lives only in the notebooks. `src/data_quest/validation/` is an empty package, although `docs/PROJECT_CONVENTIONS.md` says it holds "reconciliation and contract checks".
  - `execute_landing_plan` calls `_cleanup_tree` with `ignore_errors=True` (`landing.py:248-249`), so a cleanup failure is invisible.
  - The notebooks use `assert` for post-publish reconciliation (`01_land_bls.py:138`, `02_…py:137`).
  - `prepare_bls_landing` is a pass-through wrapper.
  - `ruff` (section 3, row 7) flags 35 mechanical issues.
- **L-10. Display/evidence quirk.** `datausa.py:23-31` stores `columns` as a tuple. In `notebooks/02_land_datausa_population.py:118-127` and `:149-161`, `createDataFrame` turns the tuple into a **struct** with fields `_1`…`_4`, not an array. **Verified in evidence:** `docs/evidence/dq08_*.csv` and `dq08_reconciliation_schema.png` show `{"_1":"Nation ID","_2":…}`. The column names are readable but the schema is wrong. Remediation: pass `list(columns)`.
- **L-11. CI and supply-chain hygiene.**
  - `.github/workflows/quality.yml` pins actions by mutable tag (`actions/checkout@v4`, `actions/setup-python@v5`) rather than by SHA.
  - It runs only `compileall` and `unittest`. There is no lint, no type check, no coverage floor, and no `git diff --check`, although `docs/QUALITY_ASSURANCE_PROTOCOL.md` Gate 3 says to "run formatting, linting, and type checks configured for the repository".
  - There is no dependency manifest, so imports of `pyspark` and `dbutils` are untested and the Python version is implicit. Tests need `PYTHONPATH=src` because the package is not installable.
  - The `README.md` requirement "shouldn't reprocess anything it's already ingested" is met at the state level but not at the network level: every run re-downloads all 12 BLS files (`PROCESS.md:47-53`, which is disclosed).

## 5. Category-by-category conclusions

| Category | Result |
| --- | --- |
| 1. Functional correctness and edge cases | Findings: M-2, M-5, L-4. The core planner (`manifest.py`) and promoter are correct on all paths I exercised. |
| 2. Ingestion idempotency, manifest and version transitions, deletion/change handling, partial-failure behavior, single-writer | Findings: H-1, M-1, L-1, L-3. The no-change rerun, the tombstone and reappearance semantics, and promote-before-publish are correct in code and consistent with the live runs. Single-writer is **unenforced** (no lock, no run-control table, no unique constraint). It is documented and accepted; see residual risk R-1. |
| 3. BLS and Data USA parsing, schema drift, malformed records, typing, data-quality rules, provenance, reconciliation | BLS: **no findings in code, because no BLS parsing, typing, or quality code exists yet**. Only the contract (`docs/SOURCE_SCHEMA_QUALITY_CONTRACT.md`) exists. Data USA: M-4 is the strict-JSON landing gap; the Bronze and Silver checks are pending DQ-11–DQ-15, not landing obligations. Also L-10. Reconciliation covers file bytes and manifest paths only, not rows. |
| 4. Security and privacy | No secrets, hosts, or personal data in tracked files or image metadata (**verified**). SQL identifiers are regex-validated everywhere they are interpolated (`spark_manifest.py:140-148`, both notebooks). There is no injection path. Findings: M-3, L-5, L-7. |
| 5. Test completeness | M-6 and the gaps in section 7. |
| 6. Databricks/Spark compatibility | **No defect found, none provable here.** Live notebook runs recorded in `PROCESS.md` and the screenshots show that the Volume operations and the Delta append work on the Free Edition runtime (**the documents and images are verified; the runs themselves are inferred**). Remaining risk: L-2, L-3, and the untested Spark SQL. |
| 7. Consistency among code, notebooks, PROCESS.md, requirements, model, and contracts | See section 8. |
| 8. Maintainability, dead code, duplication, misleading claims | L-6, L-9, L-11, plus the section 8 contradictions. |

## 6. Residual risks and unknowns

- **R-1. Single-writer.** Nothing prevents two concurrent notebook runs.
  - They can race on `landed.exists()` then `os.replace` (`download.py:228-239`), or publish interleaved manifest batches.
  - The write targets are content-addressed, so overwrite risk is low. Mis-ordered "latest" rows (L-1) are the real exposure.
  - Accepted and documented; it needs a job-level concurrency limit before any schedule.
- **R-2. Delta atomicity and `os.replace` on Volumes.** Both rest on platform behavior that is demonstrated only by the two recorded live runs, not by a repeatable test.
- **R-3. Provider behavior.** I could not test BLS or Data USA changes: the content-length-less chunked response (M-5), layout changes (H-1), and a nonempty but incomplete listing are all unobserved.
- **R-4. No analytics yet.** Bronze, Silver, and Gold, and the SQL/PySpark parity required by the quest, do not exist (`pipelines/README.md`, `sql/alternatives/README.md`, `src/data_quest/validation/__init__.py`). Everything in the schema and Gold contracts is untested design, as those documents themselves state.
- **R-5. Unexamined screenshots.** Two of the seven PNGs were not visually inspected (section 3, row 10).
- **R-6. Git history.** The clone is shallow, so I could not scan earlier history for secrets. The audited tree has none. `REQUIREMENTS_CHECKLIST.md` DQ-23 asks for a full-history scan.

## 7. Test and coverage gaps

Measured: 86 % statement and branch coverage. Missed lines:

- `datausa.py`: 39-40, 52, 62, 69, 71, 81, 87, 91, 95, 100, 109, 118, 172, 182. That is the unreadable-file path, most error branches of the envelope, and some record-level error branches.
- `download.py`: 101-102, 109-110, 115-117, 142-150, 166, 185, 195, 215, 217, 258, 260, 277, 304, 317, 321-327, 338, 341-342, 346. That includes streaming `OSError`, write failures (`StagingWriteError`), HTTP 404 and 4xx, 5xx retry, and parts of `promote_verified_file`.
- `manifest.py`: 73, 105, 107, 117, 213, 215, 302, 336, 341.
- `landing.py`: 86, 113, 199, 212, 249.
- `discovery.py`: 158, 171, 197, plus the anchor-parser branches at 47-48.
- `spark_manifest.py`: 86, 90 (a non-timestamp value, and the aware-timestamp branch).

Missing negative or edge tests:

- Truncated or partial listings and mass removal (H-1).
- An `UNCHANGED` entry with a missing or corrupt object is not covered through landing orchestration (M-1); direct promoter reuse and conflicting-object behavior are covered in `test_download.py:250-282,311-332`.
- `%`, space, and encoded-slash hrefs (M-2).
- Off-origin or downgrade redirects, tested at the handler level, and discovery redirects (M-3).
- Rejection of non-standard JSON constants (`NaN`, `Infinity`, `-Infinity`) in Data USA responses (M-4).
- `IncompleteRead`, `InvalidURL`, and unbounded bodies (M-5, L-7).
- A real filesystem `execute_landing_plan` with real promotion; a publisher that raises after promotion, asserting that the orphan object is not referenced and a rerun recovers.
- Duplicate `(relative_path, run_id)` rows, an unknown `status`, and a naive timestamp in a non-UTC zone in the Spark adapter.
- Notebook code (the reconciliation, email validation, and `createDataFrame` shapes) has no automated test at all.
- Nothing measures coverage in CI, and nothing runs against Spark.

## 8. Documentation and code contradictions

| # | Document claim | Reality |
| --- | --- | --- |
| D-1 | `PROCESS.md:75` requires valid UTF-8 JSON before publication. The schema contract separately assigns exact-envelope checks to Bronze and finite/integral population plus normalized-key uniqueness to Silver (`:137-150,218-239`), deferring those rules to DQ-11–DQ-15 (`:249-253`). | `datausa.py:45` accepts non-standard JSON numeric constants and its population check at `:103-111` lets `NaN` pass (M-4). The Bronze and Silver rules are pending downstream work, not raw-landing obligations. |
| D-2 | `docs/INGESTION_MANIFEST_CONTRACT.md` says `ingested_at_utc` is the "timestamp of the successful state transition". | The notebooks pass the run's start time (L-1). |
| D-3 | The same document says the empty-listing rejection "prevents" mass removal, and that the planner "refuses to produce a plan for incomplete inventory". | Only zero links is rejected. The completeness flags are caller-asserted (H-1). |
| D-4 | `PROCESS.md:39-45` still calls the Databricks implementation "planned". | DQ-07 through DQ-09 are implemented and have live-run evidence (`PROCESS.md:132-195`); only this `PROCESS.md` wording is stale. The manifest contract accurately says these behaviors are implemented and proven. |
| D-5 | `docs/BLS_LANDING_RUNBOOK.md:14` says the email is "sent only in the BLS `User-Agent`". | Notebook 02 sends it to the Data USA host as well (M-3). |
| D-6 | `docs/LOGICAL_DATA_MODEL.md` (`gold_series_annual_result`, `gold_population_summary`, `gold_series_population_context`) vs `docs/PROJECT_CONVENTIONS.md`, `docs/REQUIRED_GOLD_CONTRACTS.md`, and `docs/PRODUCT_ONE_PAGER.md` (`gold_bls_best_year_by_series`, `gold_population_summary_2013_2018`, `gold_bls_q01_population`). | Two different sets of Gold object names. |
| D-7 | `docs/LOGICAL_DATA_MODEL.md` has a `SOURCE_OBJECT` with a unique `source_url`, `RAW_ARTIFACT_VERSION.source_last_modified` as a timestamp, `ingested_at`, `footnote_code`, `SILVER_POPULATION.source_url`, and `INGESTION_RUN` with counts. | `docs/INGESTION_MANIFEST_CONTRACT.md` says the URL is "provenance, not identity". The implemented manifest stores `source_last_modified` as `STRING` and uses `ingested_at_utc`. The Silver contract uses `footnote_codes`, `ingested_at_utc`, and `source_file`. No `ingestion_run` table exists. |
| D-8 | The "Data-model decisions still open" list in `docs/LOGICAL_DATA_MODEL.md` includes tombstones vs `is_active`, decimal precision, and quality-failure severity. | All three are decided (the manifest contract, `decimal(20, 6)`, the quality-action vocabulary). The list is stale. |
| D-9 | `docs/SYSTEM_UML.md` shows one job and one manifest covering BLS and Data USA. | Two notebooks use two manifests (`PROCESS.md:69-73`). |
| D-10 | `docs/BLS_SOURCE_PROFILE.md` types `value` as "decimal or double". | The Silver contract fixes `decimal(20, 6)` (minor). |
| D-11 | `docs/QUALITY_ASSURANCE_PROTOCOL.md` Gate 3 refers to formatting, linting, and type checks "configured for the repository". | None is configured; CI runs only compile and unittest (L-11). |
| D-12 | `docs/PROJECT_CONVENTIONS.md` says `validation/` holds reusable reconciliation checks. | `src/data_quest/validation/` is still an empty package, and reconciliation remains in the notebooks (L-9). Notebook catalog, schema, and Volume values are widget-configurable, consistent with the convention's allowance for environment-specific settings. |
| D-13 | `REQUIREMENTS_CHECKLIST.md` marks DQ-07 to DQ-10 `[x]` and leaves **every** box for DQ-01 to DQ-06 unchecked (121 unchecked and 19 checked overall). | `PROCESS.md` and the evidence show DQ-01 to DQ-06 delivered. The checklist has drifted. |
| D-14 | `PROCESS.md` "Trade-offs" and "Retrospective" are placeholders; `PROCESS.md:170` and `docs/DATAUSA_LANDING_RUNBOOK.md:42` describe "11 records spanning 2013–2024". | The placeholders are expected at this stage. The 11-versus-12-year span is consistent with a missing year (likely 2020), but no document says so, and the validator has no year-continuity check. |
| D-15 | `docs/evidence/README.md` and `docs/screenshots/README.md` describe the exported `columns` as "declared columns". | They are exported as a struct `_1`…`_4` (L-10). |

Consistent as claimed (**verified**):

- `PROCESS.md`'s "66 tests plus 11 subtests".
- BLS file sizes in `docs/BLS_SOURCE_PROFILE.md` match the screenshot rows: 102, 562, 1,615,931, 3,239,525, 176, 40, 745, 146, 79, 263, 15,657, and 18,343.
- The no-change run counts: 12 unchanged, 0 promoted, 0 published.
- Screenshot timestamps agree with the run IDs after allowing for a UTC offset of −4 h.
- `pr.data.0.Current` row count (38,469) plus the older rows (38,657) equals the `AllData` count (77,126).

## 9. Overall readiness verdict

**Verified facts**

- The audited tree passes its own local checks: compile, 66 tests, `mypy`, and `pyflakes` (`src` and `tests`).
- There are no tracked secrets and no personal data.
- The ingestion core is deterministic and well structured. Every promotion is verified, and nothing that a manifest references is overwritten.
- The repository contains **only the ingestion/landing stage**. Bronze, Silver, Gold, SQL/PySpark parity, expectations, screenshots of pipeline or tables, and the three analytical answers do not exist yet.

**Inferences**

- For the *ingestion stage on its observed sources* the design is sound and the recorded live runs are credible. I rate it **ready for a remediation pass, not yet production-grade**.
  - One High finding (H-1) allows a silent bad-state publication.
  - Six Medium findings remain, including retry/recovery gaps and the strict-JSON landing gap. Exact-envelope, finite/integral, and normalized-key checks belong to pending Bronze/Silver work, not raw landing.
  - M-6 means the Spark adapter, the part most exposed to platform behavior, has no executed test.
- For the **overall quest deliverable** the repository is **not ready**. Most required deliverables (README steps 2 and 3, `PROCESS.md` sections, three Gold outputs, and screenshots) are still future work and are labelled so in the documents.
- Recommended remediation order: H-1, M-1, M-4, M-3, M-2 and M-5, M-6, then the documentation reconciliation (section 8), then the Low items.
