# External change workflow

## Product scope
Supplier notices and periodic external monitoring are parallel change triggers. The shared loop is
Excel upload → baseline risk briefing and human acceptance of the monitoring plan → watch start →
supplier notice from the inbox, or a newly detected external change (triaged once automatically) /
registered evidence document → retrieve cited passages and interpret them → confirm affected tasks (ask if ambiguous) →
calculate the schedule → recheck holidays and weather across the shifted period → link relevant
L2 real-case evidence → compare responses → confirm conditions → human approval → revised Excel
with evidence → continued monitoring. The demo supplier notices are synthetic, but notices are a
core trigger. Automatic email ingestion is not yet connected; the MVP accepts pasted notices.

The initial collection plan follows `REPLAN_PROJECT_MASTER.md` section 8.2: process supplier
messages immediately on receipt, propose weather checks every 6 hours, and propose registered
official notices and public-company news checks every 12 hours. These intervals are adjustable
team-approved settings, not a guarantee that a source has published new data.

## Implemented sources and limits
- Open-Meteo daily forecasts for explicitly configured coordinates, outdoor tasks and thresholds.
  Forecasts are not observations or guaranteed work stoppages. No long-range weather prediction.
- Nager.Date public holidays for configured country, year, subdivision and task IDs. Non-public
  holiday types and other regions are excluded. Actual local/supplier work calendars need review.
- Registered HTTPS pages and RSS/Atom feeds. Each feed entry retains its URL, ID, publication time,
  retrieval time and a content hash. Source registration still uses REPLAN_ALLOWED_SOURCE_HOSTS.
  This is registered-source monitoring, not unrestricted web discovery.
- Registered `.txt`, `.md`, and text-based PDF documents enter the same evidence store. A source document
  is split into immutable, hash-addressed passages and retrieved only against the project schedule,
  risk tags and approved watch terms. The current MVP uses transparent lexical retrieval in SQLite;
  the passage contract is ready for a later vector index.
- A newly detected registered-source notice with at least one rule candidate is triaged once by the
  LLM into related / needs check / unrelated, on its own daily limit (`REPLAN_MAX_AUTO_TRIAGE_PER_DAY`).
  The triage is stored apart from the rule candidates, never starts an investigation and never
  writes a schedule patch; a notice without rule candidates is marked unrelated without a call.
- Optional paid LLM interpretation runs before NEEDS_INPUT for public notices and evidence documents
  when a person starts an analysis; a notice that was already triaged reuses that result.
  In live mode the model receives retrieved passages with citation IDs (plus the task list,
  purchase list and risk register for the triage). Candidate task IDs must exist, quotes
  must occur verbatim in a cited passage, and uncited output is discarded. LLM output cannot write
  a schedule patch. Missing dates or applicability require a documented operator decision.
  Existing API_KEY/LLM_MODEL/LLM_BASE_URL and REPLAN_PAID_CALLS_ENABLED gates and usage caps apply.

## Review and calculation
Configure source keywords and related tasks in the workspace. Match reasons are candidates,
not legal applicability judgments. Publication dates are never converted automatically to delays.
The agent interprets notices and evidence, connects affected-task candidates, asks for missing
facts and drafts a response. Deterministic tools calculate dates, costs and schedules; people
confirm tasks and conditions, approve changes and send external messages. If the task or changed
date is ambiguous, ask before schedule calculation. The operator can record a supported start
constraint, unavailable date or finish estimate. Weather and calendar proposals with sufficiently
specified inputs can be simulated as conditional scenarios before applicability confirmation;
all evidence included in a scenario must be confirmed before approval or commit. Recheck public
holidays and weather over the newly shifted period, not only the original task dates. L2 article
delay durations are reference context, never schedule-calculation inputs. Concurrent external
calendar constraints are unioned, avoiding double-counting, and conflicting finish claims stop
for review.
Forecast updates supersede earlier proposals; successful scans below the limit retire them.
A failed fetch leaves previous evidence intact and is explicitly shown as a collection failure.
Changing evidence, the input version or operating calendars invalidates relevant approval.
An approval for an evidence-document event also verifies the immutable evidence document hash.
Approved blocked dates remain attached to tasks in subsequent schedule versions. Removing an
already approved constraint requires a new reviewed schedule change, not silent forecast rollback.

## Data and evaluation
data/external/hu-2026-holidays.json is an actual Nager.Date API response captured with URL, timestamp
and hash. It is an aggregated public calendar source, not claimed to be an official legal notice.
The schedule and weather/notice fixtures used in tests are synthetic and labeled as such. The RAG
tests use captured-style battery-project notices with a contract LLM; they exercise the same API,
human confirmation, calculation, approval, commit and export path without calling a paid provider.
Run python scripts/evaluate_external.py for a four-case offline engineering regression:
real calendar + synthetic project, same-day weather/calendar overlap, relevant notice and unrelated
notice. This is not a representative news benchmark, verified LLM performance, or an accuracy claim
for the existing historical L2/L3 corpus. Existing historical benchmark results are preserved.

## Fields preserved on import
supplier_id, equipment_id, country_code, risk_tags (comma-separated), planned_cost, currency.
Supplier calendar IDs are isolated by project. Calendars are applied only to matching supplier_id,
with supplier/owner as a legacy fallback. Cost comparison still reports catalog extra_cost_krw;
planned_cost/currency preservation does not implement total cost forecasting or FX conversion.

## Setup
1. Import and confirm a schedule with task IDs, dates, dependencies and outdoor flags.
2. Review the agent-proposed monitoring plan; accept, edit or exclude its sources and conditions.
3. On the 감시 (Watch) screen, open 감시 계획 설정 and configure coordinates/timezone/thresholds,
   outdoor tasks and country/year holiday calendars. Register approved public URLs and connect
   keywords and task candidates.
4. Enable monitoring, press 감시 시작, and keep the API and worker running. Use 외부 변화 지금 확인
   for a manual scan. (In the hero demo, 감시 시작 simulates one collection instead.)
5. Receive a supplier notice by pasting it into the workspace, upload a public notice/letter, or
   review a change detected by a periodic scan. Public sources and uploaded documents first show
   retrieved citation passages and candidate tasks; both join the same impact-analysis and response flow.
6. Confirm ambiguous tasks or dates, inspect calculated impact and shifted-period constraints,
   compare responses, record each condition's reply, approve, then commit and download Excel.

Automatic email OAuth ingestion and external notification delivery remain unimplemented and are
labeled accordingly. No production credentials, account permissions or deployments are changed.
