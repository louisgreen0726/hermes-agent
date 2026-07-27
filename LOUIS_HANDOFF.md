# Louis Hermes Agent WIP Handoff

Date: 2026-07-27
Repository: `https://github.com/louisgreen0726/hermes-agent`
Branch: `main`
Implementation checkpoint: `7a18d7d3e357a41ed53e9fc3e76890e59f1dc9b7`
Status: **pushed, incomplete, not release-ready**

## Stop Condition

Work was stopped immediately at the user's request. No further implementation or test execution was performed after the checkpoint push.

Do not treat `7a18d7d3e` as a verified release. Do not create a tag, GitHub release, or restart the production Gateway until the known RED test and remaining release-source gaps below are resolved.

## Repository State At Handoff

- Local `main` and `origin/main` both point to `7a18d7d3e` before this handoff document commit.
- The implementation checkpoint includes the three prior Telegram commits:
  - `142f7cdb9` - Telegram native Guest Mode.
  - `7f4c3436a` - preserve Telegram rich tables in replies and cron.
  - `59564d249` - render rich tables in Telegram guest replies.
- `upstream` remains configured as `https://github.com/NousResearch/hermes-agent.git` for manual comparison.
- Automatic Louis update code is intended to use `origin/main` only.
- No Louis release tag exists at the implementation checkpoint.
- The latest GitHub release shown by `gh release list` is still the upstream-style `v2026.7.20` release.

## What Is Implemented

1. Louis distribution identity:
   - User-visible version: `Louis-0.19.0.1`.
   - Python package version: `0.19.0+Louis.1`.
   - Upstream version metadata remains `0.19.0`.
   - Louis release date is `2026.7.27`.

2. Independent distribution documentation:
   - `README.md` identifies this as the independently maintained Louis fork and not an official Nous Research release.
   - `LOUIS.md` documents the distribution boundary and update policy.
   - Primary README installation and issue links point to `louisgreen0726/hermes-agent`.

3. Linux installer and CLI source migration:
   - `scripts/install.sh` and `scripts/install.ps1` clone/download from the Louis repository.
   - CLI reinstall hints and the model-catalog fallback were changed to Louis URLs.

4. Protected updater:
   - `scripts/hermes-update-louis` was added.
   - It is designed to fetch only `origin/<branch>` and never execute upstream fetch/pull/merge/rebase operations.
   - It validates the Louis origin, uses a lock, builds/tests in a worktree, backs up the prior state, and rolls back on activation failure.
   - `/update` was changed to prefer this updater on supported non-Windows hosts.

5. CLI update implementation:
   - Main git update flow validates that `origin` is the Louis repository.
   - Update and check comparisons target `origin/<branch>` rather than automatic upstream synchronization.
   - The Windows ZIP archive URL points to the Louis repository.

6. Tests and fixtures:
   - Existing update fixtures were partly migrated to simulate a Louis `origin`.
   - `tests/hermes_cli/test_louis_distribution.py` was added for distribution metadata and source invariants.
   - `tests/hermes_cli/test_update_check.py` now contains a new fail-closed regression test for non-Louis passive checks.

## Verification State

### Previously Observed

Before the final checkpoint edits, the broad targeted regression reported:

- `693 passed`
- `6 failed`

Those six failures were concentrated in old update-test assumptions that still expected the official repository or did not mock `origin` lookup.

A later narrow run of:

```bash
scripts/run_tests.sh \
  tests/hermes_cli/test_update_check.py \
  tests/hermes_cli/test_cmd_update.py \
  tests/hermes_cli/test_louis_distribution.py -q
```

showed the update tests passing at that point and only the then-missing README identity assertion failing. README was subsequently changed.

### Not Verified After Final Edits

No test suite was run after the last edits and before the WIP push.

The newly added test below is expected to be RED against the current implementation:

```text
tests/hermes_cli/test_update_check.py::test_check_for_updates_rejects_non_louis_origin_before_fetch
```

Reason: `hermes_cli/banner.py::_check_via_local_git()` handles Louis SSH specially but currently falls through to `git fetch origin` for a non-Louis HTTPS origin instead of returning `None` before any fetch.

The working tree passed `git diff --check` before the implementation checkpoint commit. Earlier in the work, `bash -n`, `uv lock --check`, and Python compile checks were reported as passing, but they were not rerun after the final edits.

## Known Incomplete Release-Source Boundaries

These are confirmed by source inspection and must be addressed before release:

1. Passive banner check is not fail-closed:
   - File: `hermes_cli/banner.py`.
   - Validate any origin form with a general `_is_release_remote()` check before shallow probing or fetch.
   - Louis SSH may use anonymous Louis HTTPS `ls-remote` to avoid SSH/FIDO prompts.

2. `hermes update --check` is not fail-closed before fetch:
   - File: `hermes_cli/main.py::_cmd_update_check()`.
   - It currently performs shallow probing/fetch without first validating `origin` as Louis.
   - Add a regression test that proves non-Louis origin exits before any fetch.

3. Windows no-Git ZIP fallback is blocked by origin validation:
   - File: `hermes_cli/main.py::_cmd_update_impl()`.
   - On Windows with no `.git`, `use_zip_update=True`, but the code still queries/validates a missing origin before entering `_update_via_zip()`.
   - The ZIP path already downloads from Louis. Route no-Git Windows directly to the ZIP path before git-origin validation, while preserving safety checks.

4. Desktop bootstrap still downloads the official installer:
   - File: `apps/desktop/electron/bootstrap-runner.ts`.
   - Current raw URL contains `NousResearch/hermes-agent`.
   - Change it to the Louis repository and update/add tests.

5. Desktop passive update checks still identify the official repository:
   - Files:
     - `apps/desktop/electron/update-remote.ts`
     - `apps/desktop/electron/update-remote.test.ts`
     - `apps/desktop/electron/main.ts`
   - Replace official constants/helpers with Louis equivalents.
   - Fail closed when Desktop `origin` is not Louis before branch healing, `ls-remote`, or fetch.
   - Preserve the no-interactive-SSH behavior by probing Louis SSH installs through Louis HTTPS.

6. Desktop remote-install guidance still points to the official installer:
   - Files include `apps/desktop/electron/remote-lifecycle.ts` and Desktop i18n strings.
   - Decide whether all remote install hints belong to the Louis distribution, then migrate consistently.

7. Docker guidance still tells Louis users to pull official images:
   - Files include:
     - `hermes_cli/config.py`
     - `hermes_cli/tools_config.py`
     - `tools/browser_tool.py`
     - related Docker and web-server tests.
   - No Louis Docker image was established during this work.
   - Do not invent a Louis image URL. Replace self-update guidance with an explicit unsupported/build-your-own-image message, or publish a real Louis image first.

8. Protected updater test scope is incomplete:
   - `scripts/hermes-update-louis::TEST_PATHS` does not include at least:
     - `tests/hermes_cli/test_louis_distribution.py`
     - `tests/hermes_cli/test_managed_installs.py`
     - `tests/test_project_metadata.py`
     - `tests/test_packaging_metadata.py`
   - Add the release-integrity tests before relying on the updater as a release gate.

9. `upstream` push remains technically configured:
   - Automatic code does not intentionally use it, but `git remote -v` still shows an upstream push URL.
   - Consider disabling upstream pushes with a non-pushable push URL while retaining fetch for manual review.

## Required Verification Before Release

Run in this order after implementing the fixes:

```bash
cd /usr/local/lib/hermes-agent

git diff --check
bash -n scripts/hermes-update-louis
uv lock --check
venv/bin/python -m compileall -q \
  hermes_cli gateway plugins/platforms/telegram tools
```

Focused release/update tests:

```bash
scripts/run_tests.sh \
  tests/hermes_cli/test_update_check.py \
  tests/hermes_cli/test_cmd_update.py \
  tests/hermes_cli/test_cmd_update_docker.py \
  tests/hermes_cli/test_managed_installs.py \
  tests/hermes_cli/test_louis_distribution.py \
  tests/gateway/test_update_command.py \
  tests/gateway/test_update_streaming.py \
  tests/test_project_metadata.py \
  tests/test_packaging_metadata.py -q
```

Telegram regression set:

```bash
scripts/run_tests.sh \
  tests/gateway/test_telegram_native_guest_mode.py \
  tests/gateway/test_delivery_ledger_producer.py \
  tests/gateway/test_telegram_group_gating.py \
  tests/gateway/test_telegram_rich_messages.py \
  tests/gateway/test_telegram_rich_newlines.py \
  tests/gateway/test_telegram_final_delivery.py \
  tests/gateway/test_telegram_format.py \
  tests/gateway/test_telegram_thread_fallback.py \
  tests/gateway/test_telegram_auth_check.py \
  tests/gateway/test_proxy_mode.py \
  tests/tools/test_send_message_tool.py \
  tests/tools/test_send_message_telegram_proxy.py \
  tests/tools/test_telegram_send_message_caption.py -q
```

Desktop checks after Desktop source migration:

```bash
npm --prefix apps/desktop run typecheck
npm --prefix apps/desktop run test:desktop:platforms
```

Protected updater dry run, only after the focused suites are green:

```bash
scripts/hermes-update-louis --dry-run
```

Then run an independent pre-commit review, commit the fixes, and push `origin/main`.

## Release Work Still Pending

- Decide the Louis tag convention. No convention was finalized. Candidate formats must be reviewed rather than guessed, for example `vLouis-0.19.0.1` versus a PEP-440-derived release tag.
- Create Louis-specific release notes describing upstream base, Guest Mode, rich Telegram tables, update boundary, supported platforms, and known limitations.
- Create and verify the GitHub release only after all gates pass.
- Verify installer URLs from a clean temporary environment.
- Verify `hermes --version`, `command -v hermes`, and package editable location after activation.
- Restart the production Gateway only after the verified commit is active, then check service health and Telegram Guest Mode/rich-table behavior.
- Update or remove old local update aliases such as `hermes-update-with-guest-mode` only after the protected Louis updater is proven.

## Cache-Rate Regression: Separate Investigation

The user observed that cache hit rate may have degraded during the Hermes modifications. This was not investigated before the stop request.

Do not assume `7a18d7d3e` directly caused it. The implementation checkpoint does not modify `run_agent.py`, `agent/` cache-policy helpers, model request construction, or the token-accounting schema directly. Confirm this with:

```bash
git diff --name-only 41f2196c5..7a18d7d3e -- \
  run_agent.py agent model_tools.py toolsets.py hermes_state.py
```

### Cache Investigation Checklist

1. Record the exact symptom:
   - Provider and model.
   - API mode and base URL.
   - Whether the rate is from the upstream relay, Hermes usage UI, or another dashboard.
   - Before/after time window and representative sessions.

2. Distinguish real cache misses from accounting loss:
   - OpenAI-compatible responses commonly report `usage.prompt_tokens_details.cached_tokens`.
   - Anthropic-style responses report `cache_read_input_tokens` and `cache_creation_input_tokens`.
   - Confirm the custom relay preserves the relevant fields and Hermes maps them into `cache_read_tokens` / `cache_write_tokens`.

3. Compare raw provider responses with Hermes accounting:
   - Inspect redacted request/response logs for cache usage fields.
   - Inspect recent usage rows in `~/.hermes/state.db`; discover the exact tables/columns first with SQLite schema commands rather than assuming names.
   - Compare raw response totals with `hermes_state.py` writes and the displayed cache rate.

4. Run a controlled two-request reproduction:
   - Same provider, model, API mode, system prompt, tools, and user payload.
   - Send the identical large-prefix request twice.
   - Capture raw usage for both calls.
   - Repeat once through the relay directly and once through Hermes.

5. Check prefix stability:
   - System prompt changes.
   - Dynamic tool schema/order changes.
   - Memory, skill, persona, project-context, date/environment blocks.
   - Context compression or session resume.
   - New session/restart cold-cache effects.
   - Any provider/model/API-mode rotation between calls.

6. Inspect the primary code paths:
   - `run_agent.py::_anthropic_prompt_cache_policy()`.
   - `agent/agent_runtime_helpers.py::anthropic_prompt_cache_policy()`.
   - `run_agent.py` cache-control injection around the prepared system message.
   - Usage normalization/accounting paths found with:

```bash
rg -n "cached_tokens|cache_read|cache_write|cache_control|prompt_cache" \
  run_agent.py agent hermes_state.py providers.py tests
```

7. Test likely non-code causes:
   - Gateway or provider restart causing cold caches.
   - Custom relay changing cache behavior or omitting usage details.
   - Credential-pool rotation sending requests to different upstream accounts/backends.
   - Prefix churn from newly loaded skills/tools or changing system metadata.

8. Add a regression test before fixing:
   - One test for raw usage-field normalization.
   - One test for stable cache-control placement and stable request prefix across repeated turns.
   - If the issue is only dashboard calculation, test the rate formula separately.

### Cache Investigation Evidence To Preserve

- Redact all API keys, authorization headers, cookies, and tokens.
- Preserve exact model ID, provider, API mode, usage JSON, request prefix hash, timestamps, and session ID.
- Do not use historical session claims as proof; reproduce with current live data, per user preference.

## Suggested First Commands For The Next Agent

```bash
cd /usr/local/lib/hermes-agent
git status --short --branch
git log -5 --oneline --decorate
git show --stat 7a18d7d3e
scripts/run_tests.sh \
  tests/hermes_cli/test_update_check.py \
  tests/hermes_cli/test_cmd_update.py \
  tests/hermes_cli/test_louis_distribution.py -q
```

Expected starting point: at least the new non-Louis passive banner test should fail until `hermes_cli/banner.py` is made fail-closed.
