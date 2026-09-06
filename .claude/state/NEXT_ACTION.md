# Next Action

_Updated 2026-09-06._

> **Since 2026-09-05:** the new scheduled catalogue-probe (#1426) filed issue #1434
> the next morning, and its "Unreachable providers" section was itself a bug: `ollama`/
> `lmstudio`/`vllm`/`localai` are disabled by default but still had a localhost
> `base_url`, so the probe dialled them anyway on every CI run and always failed.
> Fixed in PR [#1443](https://github.com/strikersam/autonomous-ai-agency/pull/1443)
> (auto-merge armed) — see tracker row 53. **Not fixed, needs a live key:** #1434 also
> names `anthropic:claude-sonnet-5` returning HTTP 400 to the probe's minimal chat
> payload (`model`, one user message, `max_tokens: 8` — no `temperature`, so this is
> not the known adaptive-thinking 400 class already guarded in
> `packages/llm/providers/anthropic.py`/`packages/ai/router.py`). Could not be
> reproduced here — no `ANTHROPIC_API_KEY` reaches this sandbox. Re-run
> `gh workflow run catalogue-probe.yml -f provider=anthropic -f chat=anthropic
> -f model=claude-sonnet-5` and read the raw response body (the probe only prints
> the HTTP status, not the error JSON — that may itself be worth improving) before
> guessing at a fix. `cerebras:gpt-oss-120b` HTTP 402 in the same issue is the
> already-tracked billing hold, §6 below — no code fix exists for it. Task #50 below
> remains the top priority for the next session that can run the real pytest suite.

## TOP: Provider/model central source of truth + admin-UI control (task #50)

Branch `claude/provider-health-status-3gc25r`. **Phase 0 MERGED to master (squash
`1e08270`, PR #1412)** — dead planner prefer_models fixed, rule 4 corrected, CI
guard `scripts/check_model_catalog_consistency.py` live. Next: Phase 1 with these
decisions **locked**:

1. **One authoritative model catalogue** — everything derives from it. Blocker
   confirmed by reading the loader: `packages/llm/config.py::_load_models` +
   `registry.py` key models `id → one ModelConfig` (`self._models: dict[str, ...]`,
   `_build(ModelConfig, body, id=mid)`), so `_merge_env_defaults`/`_backfill`
   last-wins-overwrite when two providers list the same id — `openai/gpt-oss-120b`
   (nvidia AND groq) and `openai/gpt-oss-20b`; `qwen/qwen3.8-27b` is groq-only.
   **Concrete Phase 1 design:** add `extra_providers: list[str]` to `ModelConfig`;
   accept `providers: [nvidia, groq]` in models.yaml (`_load_models` sets
   `provider=providers[0]`, `extra_providers=providers[1:]`); build a
   per-provider index in `ModelRegistry` so `for_provider(pid)`/`candidates(
   provider_id=pid)` return a `with_provider`-bound copy when `pid in
   extra_providers` (keep `get(id)` returning the canonical/primary entry for
   back-compat). Then declare groq on the gpt-oss entries, remove the 3 dead groq
   entries (`llama-3.3-70b-versatile`, `deepseek-r1-distill-llama-70b`,
   `llama-4-maverick-17b-128e-instruct`), collapse `config/models.yaml` into it,
   and tighten the guard's cross-catalogue check from WARN to FAIL. Needs new
   multi-provider tests + likely fixups in ~10 existing catalogue tests
   (test_daily_automation_*, test_brain_failover, test_llm_router_*). **Not doable
   in the web container — no fastapi/bcrypt/motor, and CI never calls a live
   provider, so green CI ≠ correct routing. Must land with real `pytest -x`.**
2. **Keys stay in Render env (rule 6 intact), updatable via the UI** using the
   Render API — "Render is the key DB". Build an admin-only endpoint that PATCHes a
   provider's key/base_url env var via the Render API (foundation:
   `backend/render_router.py`, `packages/integrations/render_mcp.py`). Note: an
   env change triggers a Render redeploy — surface that in the UI. One bootstrap
   secret (the Render API token) stays in env.
3. **UI**: simple (ref `CompanyHelm/companyhelm`, not yet reviewed — review when
   building). Show availability (which keys are set) + health (from
   `/api/brain/failover/status`) + editable base_url/model. Much of the surface
   exists: `frontend/src/v5/screens/ProvidersScreen.jsx`, `/api/providers*`.

**Constraint:** none of P1–P4 is testable in the web container (no fastapi/bcrypt/
motor) — they must land with the real `pytest -x` suite. Do not ship the brain
change without it.

## Nothing is blocked on an agent. Two things need a human.

### 0. NVIDIA models — resolved, with one measurement still missing

Every NVIDIA id this repo carried was probed against the production key on
2026-08-28. All but one answered 410 or 404, including `z-ai/glm-5.2` (the
default brain for all four agent roles) and `nvidia/nemotron-3-ultra-550b-a55b`
(briefly installed as the default on the strength of a catalogue listing alone).

The rotation now holds only ids that returned HTTP 200 to a real completion,
and all three tool-call correctly:
`nvidia/nemotron-3-super-120b-a12b`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`.
`mistralai/mistral-nemotron` answers but is slow — it timed out on one of two runs.

**Still missing, and not guessable:** real `context_window` / `max_output_tokens`
for these models. NVIDIA's `/v1/models` returns only `id`, `object`, `created`
and `owned_by` — no capability fields at all, so an earlier note here claiming
"anyone with the key can get them from `GET /v1/models`" was wrong. The entries
in `config/llm/models.yaml` and `packages/ai/registry.py` therefore carry
conservative floors (32768 / 4096), which prune prompts rather than overflow
them. Raise them when someone measures the real limits.

Model ids live in six places (`config/models.yaml`, `config/llm/models.yaml`,
`config/llm/providers.yaml`, `packages/ai/brain_config.py`,
`packages/ai/registry.py`, `services/brain_failover.py::_MODEL_ALIASES`).
`tests/test_one_model_catalogue.py` freezes the divergence and blocks retired
ids from becoming routable, but the consolidation itself is not done.

Re-check anything above with:
`gh workflow run catalogue-probe.yml -f provider=nvidia -f chat=nvidia -f tools=true`

### 0b. `nvidia/nemotron-3-ultra-550b-a55b` — RESOLVED, restored to the rotation

It was retired on a 404 from probes at 17:02 and 17:05 on 2026-08-28. Three
later observations contradicted that — a council-review `HTTP/1.1 200 OK` at
20:10, and probe runs 33220369591 (23:25, with a real `tool_calls`) and
33241283346 (2026-08-29 07:37), both exiting zero from a workflow that returns
non-zero when a `--chat` model will not answer.

It is back as a rotation candidate, behind `nvidia/nemotron-3-super-120b-a12b`,
which stays the default because it has answered on every probe. Removed from
both `RETIRED` lists, added to `config/models.yaml` and the reconciled
`packages/ai/brain_config.py` copy, and the "proven dead" comments in
`config/models.yaml` and `render.yaml` are corrected.

Four documents had drifted the *other* way and are now consistent with
`packages/config/settings.py`: `CLAUDE.md` (two tables) and `.env.example` (two
blocks) named the ultra as the built-in default, which the code has not done
since 2026-08-28.

### 0c. The daily `Update repo with latest details` routine needs one edit from you

`trig_01YAcSFjnca1mmTyyS4CpJCy`, cron `0 7 * * *`. It cannot be changed from a
session: it was created via the HTTP API, and an agent may only update routines
it created itself. The edit is a prompt replacement in the Routines UI.

Its last run (`cse_01Lt5frsHuqskGmcpmDbYZwg`, 2026-08-28 07:01) failed with
`"You've hit your session limit · resets 10:20am (UTC)"` — a five-hour rate
limit, `status: rejected`, after 1.49M cached tokens and $1.18 spent on an
open-ended industry survey with nothing committed. The stale
`local-llm-server` source URL is **not** the cause; GitHub's rename redirect
resolves it and the run did check out and branch.

Two real defects:

1. **Its prompt says "Push directly to `master`."** That bypasses the plan
   gate, the PASS-only council merge and the review-bot counting added in
   #1377 — precisely the gates that exist to stop unreviewed work landing.
2. **Its scope is unbounded** ("scan Anthropic, OpenAI, Claude Code, Codex and
   leading AI-dev tools"), which is what exhausted the budget. It also implies
   it must always ship something, so "nothing worth doing today" is not an
   available outcome.

The replacement prompt is in the session transcript for 2026-08-29.

### 1. Render is suspended for billing — this is the big one

Service `srv-d7cb43beo5us73e1leug` (`local-llm-server`) is `suspended`,
`suspenders: ["billing"]`. Everything below is dark until that is resolved, and
none of it is fixable from a session:

- `PR_APPROVAL_GATE_ENABLED=true` cannot be set (`400 cannot deploy suspended
  service`), so there is no Telegram gate on PR approval.
- The in-process agency is down: CEO loop, self-healing, dispatcher, Telegram
  bot, `services/pr_approval_gate.py`.
- **Langfuse tracing is already wired** across `proxy.py`, `agent/loop.py`,
  `agent/agency.py`, `tasks/service.py`, `packages/ai/self_heal.py`,
  `services/otel_tracing.py`, `handlers/anthropic_compat.py`,
  `agent/trend_watcher.py`, `agent/sam.py`, `packages/config/settings.py`, with
  keys in `render.yaml` as `sync: false`. It emits nothing because the service
  is not running. No code change is needed — only billing.

`/api/ping` returns 000; Hermes 404s. The GitHub-Actions half of the agency
(37 loops) is unaffected and running.

### 2. `anthropic >=1.0.0` — resolved, and the premise was wrong

An earlier note here held this back under rule 40 as a breaking dependency
upgrade. It is not one, and the reason matters: **`anthropic>=0.122.0` already
resolves to 1.0.0**, so CI, Render and every developer install have been running
1.0.0 since it was published. Dependabot's PR raises the *floor*; it does not
change a single byte of what gets installed. The risk it appeared to carry had
already been taken, silently, weeks earlier — which is the same shape as every
other defect on this branch.

Verified rather than assumed. The SDK has exactly two call sites, both in
`agent/loop.py` (not `packages/ai/router.py` or `handlers/anthropic_compat.py`,
as the earlier note said): they construct `AsyncAnthropic` and
`AsyncAnthropicBedrock` and call
`messages.create(model=, max_tokens=, system=, messages=)`. All four names are
present in 1.0.0's signature; neither site passes `temperature`, which 1.0.0
dropped. The pin is applied and #1336 is closed.

### 3. The loop overrode its own recorded REJECT, inside a single pull request

The first fully successful autonomous run (run 33204279915, 39 min, issue #1356)
worked end to end — implement, pytest, PR, review bots, apply review, council,
draft→ready, squash-merge, close issue — and produced `b368f9e7` on master:
~1,200 lines of SEO-to-portfolio bridging (`agents/seo_portfolio_bridge.py`,
three new endpoints in `backend/seo_api.py`, 13 tests).

**PR #1357 is that PR** — not, as an earlier draft of this note said, a separate
earlier one. Verified: `merged_at 2026-08-28T20:10:59Z` (the second `b368f9e7`
was authored), base `8b448842` (its parent), and `1199 additions / 7 deletions /
7 changed files`, matching the commit exactly. Its title is still
*"docs: reject: SEO backlog-to-roadmap is out of scope for autonomous-ai-agenc"*
and its body still reads **"🛑 REJECT — nothing here belongs in this
repository."** The context step wrote that verdict; the implement step ran on the
same branch and merged 1,199 lines under it. Nothing in the pipeline reads its
own planning decision.

The REJECT was not authoritative either, and should not be treated as the
correct answer that got overridden. The same PR body records
*"Fetch status: ⚠️ NOT FETCHED — the plan below is unverified against the
source"* and a Quality Gate failure: *"R1 — the linked source was not retrieved,
so every claim about it is unverified; the document must be reviewed before
implementation."* It was generated by `mistral-small-latest`. So the planner
rejected an article it never read, and the implementer then built 1,200 lines
for an article it never read. Neither half of that run was grounded.

The bad squash subject is what hid the contradiction: with a correct subject the
merge commit would have read *"implement quick-note issue #1356"* while its own
PR was titled *"reject: … out of scope"* — visible in one line of `git log`.

**The review bots did not review it.** CodeRabbit posted
*"This repository does not receive automatic reviews because it has fewer than
10 stars"*, and Codex posted *"You have reached your Codex usage limits for code
reviews."* The `.coderabbit.yml` the loop created in this very commit sets
`auto_review.drafts: true`, which does not address the actual blocker (star
count). The pipeline's "Wait for review bots → Apply review comments" steps ran
11m03s and reported success against no bot review.

What *did* review it was the repo's own council step, and its verdict was
**WARN** with: *"SECURITY: WARN — New API endpoints added … but diff is
truncated; cannot verify authentication/authorization guards on these routes"*
and *"These are non-blocking but require human verification before merge."*
`process-quick-note.yml` treats `WARN` as mergeable, so a review that asked for
human verification before merge was auto-merged without it.

Both council WARNs have now been resolved by hand:

- **Security — resolved, no defect.** All three endpoints take
  `Depends(_get_current_user_thunk)` *and then* `get_company_access(company_id,
  user)`, so another company's audit answers 404. Rule 10 holds; rule 11 holds
  too (Pydantic v2 request models with `Field` constraints, `response_model` on
  every route).
- **Correctness — one real defect, now FIXED.** `Initiative.wsjf` is a
  `@property`, so `init.wsjf` was always correct, and `source` is a real field.
  But `estimated_monthly_value` was **not a field on `Initiative`**, and
  `delegation_task_to_initiative` never carried it across — it interpolated
  `task.estimated_monthly_value` into the free-text `rationale` and dropped the
  number. Every consumer read it back as
  `getattr(init, 'estimated_monthly_value', 0)`, so all three endpoints returned
  a fabricated `0` and the roadmap printed `$0` on every row.

  `Initiative` now declares `estimated_monthly_value: float = 0.0`, the bridge
  sets it, and all **8** `getattr` defaults are gone — **6** in
  `backend/seo_api.py` and 2 in the bridge. (An earlier note here said 8 in
  `seo_api.py` and 10 overall; the real counts are 6 and 8, caught by an
  assertion in the edit script.) The default is what made the loss silent, so
  removing it matters as much as adding the field: a future regression now
  raises instead of reporting a plausible zero.
  `tests/test_seo_initiative_value_survives.py` — 9 tests, all failing against
  the pre-fix code.

**The override itself is fixed** — see §4. `scripts/context_plan_gate.py` now
reads the plan before the implementer runs, and fails closed on all three of the
signals this plan carried (REJECT, unfetched source, unmet rules).

Still unmet and not fixed:

- **Rule 28 in `b368f9e7`.** `build_seo_roadmap` (74 lines), `plan_seo_sprint`
  (83), `run_seo_pipeline` (114), and three functions in
  `agents/seo_portfolio_bridge.py` (52/57/78) all exceed the 50-line limit, and
  `backend/seo_api.py` went from 381 to 756 lines against the 800-line cap.
  Refactoring merged code is behaviour-touching work under rule 1 and needs its
  own change, not a rider on a workflow fix.

### 4. The backlog is at zero, and the gates that let bad work through are closed

**6 open issues → 0. 11 open PRs → 0.** Details in tracker row 43.

Five gates in `process-quick-note.yml` resolved an unknown into an approval,
and all five are now closed with tests that fail against the pre-fix workflows:

1. **The plan is read before anything is built.** `scripts/context_plan_gate.py`
   parses the committed context plan and fails **closed** — a REJECT verdict, an
   unfetched source, unmet rulebook rules, or a verdict it does not recognise
   all block the implement step, label the issue `quick-note:rejected`, and
   comment. The old defence was a label written best-effort by a different
   workflow on one code path; when it did not happen, nothing said so.
2. **Only `PASS` auto-merges.** `WARN` used to, including the one on #1357
   reading *"cannot verify authentication/authorization guards"* and *"require
   human verification before merge"*.
3. **A council that did not run is `NONE`, not `WARN`.** The step is
   `continue-on-error: true`, so a crashed reviewer previously merged exactly
   like an approving one. Every non-`PASS` outcome now comments; before, only
   `FAIL` did.
4. **Review bots are counted.** Zero reviews raises a warning instead of an
   11-minute "apply review comments" step reporting success against nothing.
5. **The queue holds work, not paperwork.** `agency-escalation`,
   `trend-digest` and `crispy-burn-in` labels are excluded from selection.

Two upstream loops fed the same pattern and are fixed: `agency-cycle.yml` no
longer escalates failures its own classifier calls unfixable, and
`crispy-burn-in-check.yml` fails loudly instead of filing a verdict computed
from an empty evaluation.

**What this changes for you:** the loop will now open PRs and leave them for a
human whenever the council does not return `PASS`. That is deliberate — it
trades throughput for the property that a merged change was actually reviewed.
If the volume of waiting PRs becomes the problem, the lever is the council's
own strictness, not the merge gate.

### 5. The catalogue probe was letting a refused listing veto the answering

`probe_catalogues.py` exists on one premise — a model can sit in a vendor's
catalogue and still refuse to serve, so listing is not proof and answering is.
Its provider loop did the opposite of that. On a `list-models` failure it
recorded the provider as unreachable and `continue`d, which skipped the `--chat`
block entirely, so an explicit `--model` id passed precisely to test a candidate
was discarded without a word.

Found by running it: with `CEREBRAS_API_KEY` now in GitHub Actions, run
33257508244 reported `key present: yes`, `list-models failed: HTTP 403 —
Forbidden`, `reachable providers: 0` — and never sent the completion it had been
asked to send.

Listing and calling are now independent. A named model is called whichever way
the listing went; a provider is reachable if *either* succeeds; and "answered but
would not list" is its own line, distinct from `unreachable`, because collapsing
the two is how a live model gets written off (§0b, the day before). Relaxing the
rule exposed a second silent path — `probe_chat` returned `True` for an adapter
kind it has no chat route for, which would have read as an answer — so the skip
is now decided before the call and counts as nothing.

Re-check any candidate model with:
`gh workflow run catalogue-probe.yml -f provider=<id> -f chat=<id> -f model="<model-id>" -f tools=true`

### 6. Cerebras serves nothing to this account — and needs one thing from you

With the key finally in Actions, the provider was asked what it serves rather
than configured from documentation. Its `/v1/models` returns exactly two ids:
`gpt-oss-120b` and `gemma-4-31b`.

**Every id this repo had configured for Cerebras answers 404** —
`qwen-3-coder-480b` (the default, the one `CLAUDE.md` named), `llama-3.3-70b`
(the verifier/judge preset and `ProviderRouter`'s default), `llama-3.1-8b`, and
`qwen-3-235b-a22b-instruct-2507` from PR #1378, which would have gone in at
`priority: 9`, ahead of everything. Rule 4 makes Cerebras the *first* provider
tried on every call, so this was a 404 on the first hop of every request, all
along, reported by nothing: failing over to Groq looks exactly like a healthy
chain until Groq fails too.

That half is fixed — the configuration now names only what the account lists.

**What needs you:** both remaining ids return **402 Payment Required**. That is
an account state, not a model state, and no code change reaches it. Until it is
resolved, Cerebras contributes nothing and every call starts at Groq. Nothing is
broken by this: the chain degrades correctly, and it is the second billing hold
on the list (Render, §1, is the other).

**The key has been ruled out.** `CEREBRAS_API_KEY` was replaced on 2026-08-29
and re-probed (run 33263933282): the catalogue listed both ids and both
completions returned 402 again. A 402 is an *authenticated* refusal — an invalid
or revoked key answers 401/403 and never reaches a billing check — so the
credential is good and the account simply has no credit. Replacing the key again
will not change this; only billing will.

When credit is in place, re-probe before trusting anything:
`gh workflow run catalogue-probe.yml -f provider=cerebras -f chat=cerebras -f model="gpt-oss-120b gemma-4-31b" -f tools=true`

That run also settles the two capability numbers currently carrying conservative
floors (32768/4096) and `supports_tools: false`. The flag is not pessimism for
its own sake: `packages/llm/registry.py` routes tool-calling work on it, and
inferring it from a model's family name is precisely what PR #1378 did.

PR #1378 is closed with the probe output on the thread.

### 7. The last 410 is operator data, not code — one edit in the admin UI

Production still logs, roughly hourly:

    Model nvidia-nim/z-ai/glm-5.2 returned 410 Gone — skipping for 3600s
    Provider nvidia-nim placed on cooldown for 300s

**This is no longer an outage.** After #1400 and #1401 the chain fails over and
completes — `router.huggingface.co` returned `HTTP/1.1 200 OK` at 11:26:19 on
2026-09-01, and no task has been `blocked after 5 failed dispatch attempts`
since that deploy. The cost is one wasted first hop plus a 300s NVIDIA cooldown
per cycle, so the platform runs on its second-choice provider.

Every code-side source was checked and is correct:

| source | value |
|---|---|
| `render.yaml` `NVIDIA_DEFAULT_MODEL` (3 places) | `nvidia/nemotron-3-super-120b-a12b` |
| `packages/ai/router.py` `from_env` default | same |
| `packages/ai/brain.py` `DEFAULT_FREE_NVIDIA_MODEL` | same |
| `packages/ai/brain_config.py` presets + candidates | same |
| the persisted BrainConfig row | reset correctly at 11:24:22, log-confirmed |

What remains is a **persisted provider record in MongoDB** with
`provider_id="nvidia-nim"` and `default_model="z-ai/glm-5.2"`. Two things point
there and nothing points elsewhere: `ProviderRouter.from_provider_records` is
the only builder that takes `default_model` from stored data, and
`packages/ai/brain.py` only uses its (correct) free-NVIDIA fallback *"when the
operator has no configured provider records"* — a path production did not take.
Strongly indicated by elimination, not directly observed: this sandbox cannot
reach the app, the Worker, or MongoDB, and the Render API exposes no env reader.

**The fix is yours and takes one edit:** in the Brain / Providers admin surface,
set the `nvidia-nim` record's model to `nvidia/nemotron-3-super-120b-a12b`
(probed 2026-09-01, HTTP 200 with a real `tool_call`).

**A code guard was considered and deliberately not shipped.** Rejecting a
retired id inside `from_provider_records` needs a retired-model list in
production — a seventh copy of the catalogue, which is the defect this whole
line of work has been removing — and validating against the catalogue instead
would override operator-configured records, a behaviour change nobody asked
for and a real risk for legitimate proxy setups. The safe version, if wanted,
is *observability only*: one loud startup WARNING naming any provider record
whose `default_model` is absent from the catalogue for that provider. No
override, no behaviour change, and it would have surfaced this on day one
instead of after four catalogue corrections and two fixes.

## Running unattended, no action needed

- **Dependabot backlog: 12 open, draining ~1/hour.** `dependabot-auto-merge.yml`
  runs hourly, updates one stale branch per run (branch protection means only one
  PR can merge per run regardless), classifies each up-to-date PR with
  `scripts/classify_dependabot_update.py`, and arms auto-merge only for
  `group`/`minor`/`patch`. `major` and `unknown` go to a human. #1346 and #1345
  merged this way.
- **The plan→implement loop converged.** `agency-cycle` run 380 ran on `50b04aa7`
  (contains the parser fix `cfea9ff`) and filed no new failure issue — the first
  clean tick since the ghost-node-ID bug. #1331 and #1317 closed themselves;
  #1312 is on `retry:1`. Open issues 10 → 8.
- `process-quick-note.yml` picks the oldest open non-exhausted issue every 4h.
- `orphaned-pr-sweep.yml` runs daily at 06:00 UTC.

## If you pick this up next

Check that the Dependabot count keeps falling (12 → 0 over ~12 hours). If it
stalls, read the sweep log first — the exit code has been misleading three
separate times on this workflow, and every real defect was found by comparing
the log against the PRs' actual state.
