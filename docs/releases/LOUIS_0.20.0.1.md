# Louis Hermes Agent 0.20.0.1

Release date: 2026-08-07

Louis Hermes Agent 0.20.0.1 selectively integrates reviewed changes from Nous
Research Hermes Agent 0.20.0 (upstream release 2026.8.3). It is an independently
maintained Louis release, not an official Nous Research release. The upstream
license, attribution, original authors, and commit order are preserved.

## Selective upstream boundary

- The review compared Louis commit `a720a9a844e9` with upstream tag
  `v2026.8.3` (`3c27eb6234bf`). The trees differed across more than four
  thousand files, so this release uses ordered cherry-picks and Louis-specific
  adaptation commits rather than a merge, rebase, or tree replacement.
- Louis keeps its newer state-store schema, external-content FTS, CJK bigram
  indexing, storage optimization, redaction correctness, named-provider
  identity, update source, release workflow, branding, and product surfaces.
- `origin/main` remains the only automatic update source. No upstream
  installer, update remote, release metadata, README, or branding replaces the
  Louis equivalents.
- This release deliberately excludes the upstream Dashboard replacement, Node
  26 and channel-retirement changes, a 500-iteration default, default-enabled
  new tool surfaces, third-party product plugins in the core tree, and the
  separately scheduled state-store and A2A work.

## Security and dependencies

- `cryptography` is pinned to 48.0.1, Starlette to 1.3.1, and
  `python-multipart` to 0.0.32 in both normal dependency resolution and the
  lazy-dependency mirror, carrying the reviewed fixes from upstream PRs
  `#72362` and `#76083` without loosening Louis dependency policy.
- Config-key redaction now uses linear-time matching for hostile YAML while
  retaining Louis's namespaced, line-anchored behavior and the existing
  `#67776` correctness guarantees.
- Terminal approval recognizes Docker and Podman commands that redirect a
  client to another daemon, so a daemon-switching command cannot bypass the
  normal approval boundary.

## Tool correctness

- Terminal failures include focused hints for common command, permission,
  network, disk, and dependency errors without changing the underlying output
  or exit status.
- Reapplying an already-applied patch returns a successful no-op instead of a
  misleading failure.
- Search distinguishes a genuine zero-match result from hidden, ignored, or
  alternate-path candidates and can recover across multiple requested paths.
- `write_file` reads the result back from disk and reports `verified: true`
  only after the persisted content matches.
- These changes extend existing tools only; they add no core model tool or
  mid-session toolset mutation.

## CLI and startup

- `/init` scans the current project and creates or updates its `AGENTS.md`
  guidance through the existing CLI command system.
- `!<command>` runs a shell command directly from the interactive CLI without
  consuming a model turn, while preserving the current process environment,
  working directory, output, and exit semantics.
- Heavy SDK imports have moved off the cold-start path and remain lazy until
  their feature is first used.
- Startup readers share one raw `config.yaml` parse per process. The Louis
  adaptation keys the cache by `get_process_hermes_home()`, preserves managed
  overlays, and prevents values from leaking when the process home changes.

## Grounded Citations and fact checking

- The new Grounded Citations skill maintains a profile-aware source ledger,
  emits mechanically verified inline citation numbers and source lists, and
  checks that cited URLs came from retrieval rather than model memory.
- Fact-check mode attaches verbatim evidence, tolerates Markdown markup in
  extracted text, marks genuinely unsourced claims as `[unverified]`, and can
  enforce both evidence presence and citation coverage.
- The skill follows Louis authoring policy: `Teknium + Hermes Agent` credit,
  the `# Grounded Citations Skill` title, a compact description, native Hermes
  retrieval tools, and an explicit `--ledger` option for shared work.

## Opt-in outbound webhooks

- `hooks.outbound` registers only when explicitly configured. Lifecycle events
  enter an asynchronous bounded queue, receive one bounded retry for eligible
  failures, and never block an agent turn.
- Deliveries never follow redirects. An optional `secret_env` value signs the
  exact JSON body with HMAC-SHA256, and one delivery id is shared by the body
  and headers across a retry.
- Payloads may contain `tool_input` and other event metadata. Operators should
  send them only to trusted HTTPS endpoints and keep signing secrets in
  `.env`, referenced from `config.yaml` by environment-variable name.

## Speech-to-text

- Every built-in, command, and plugin STT provider uses one language-resolution
  chain: `stt.<provider>.language` then `stt.language`, then the legacy
  `HERMES_LOCAL_STT_LANGUAGE`, then provider auto-detection.
- Local faster-whisper accepts `stt.local.initial_prompt` for vocabulary and
  script biasing. The new configuration key is deep-merged without a config
  schema-version bump.
- OpenAI and Groq now receive configured language hints consistently, null
  provider blocks are safe, and xAI no longer silently forces English when
  automatic detection was requested.

## Text-to-speech and voice routing

- One shared cleaner removes reasoning and verifier blocks, Markdown noise,
  and text that should not be spoken, then normalizes units and symbols for
  synthesis. Telegram captions retain the original reply rather than the
  cleaned spoken form.
- `text_to_speech` accepts stable `speed`, `instructions`, and `provider`
  arguments. Provider-specific speed overrides the global TTS speed, and
  OpenAI-compatible voice-design endpoints receive `instructions`.
- `tts.openai.language` maps to `lang_code` for compatible multilingual
  endpoints, while `tts.xai.text_normalization` controls xAI's native text
  normalization.
- CLI voice mode and Gateway media routing share the same preparation path,
  preserving each platform's distinction between voice notes, audio files,
  captions, and ordinary text replies.

## Desktop Quick Entry

- The global `CommandOrControl+Shift+Space` shortcut opens a compact composer
  that submits to the current chat, a new session, or a recent session through
  the existing Desktop submission flow. It does not create another Gateway
  connection or a second prompt pipeline.
- Quick Entry is enabled by default and configurable under **Settings ->
  Advanced**. Disabling it unregisters the shortcut; invalid and occupied
  shortcuts are shown as errors instead of silently reverting.
- Electron owns `quick-entry.json` and exposes only restricted IPC. Empty and
  duplicate submits are rejected, a closed primary window publishes a
  disconnected state, and every shipped locale (`en`, `zh`, `zh-hant`, `ja`,
  and `ar`) includes the new UI.

## Louis project and provider identity

- Root documentation now presents Louis Hermes Agent as an independent
  derivative with its own roadmap, production branch, update source, release
  process, and English/Simplified Chinese parity contract while retaining
  upstream attribution and the MIT license.
- Named custom providers remain durable identities. Providers sharing one
  relay URL keep independent models, API modes, environment-key references,
  credential pools, fallback recovery, and cross-turn routing.

## Release metadata

- CLI version: `Louis-0.20.0.1`
- Python package version: `0.20.0+Louis.1`
- Desktop package version: `0.20.0-louis.1`
- Selectively integrated upstream baseline: Hermes Agent `0.20.0`, release
  `2026.8.3`

Version tests now assert relationships instead of frozen snapshots: the CLI
and Python base/revision must agree, the Python base must match the declared
upstream version, release dates must be ordered, and Vitest owns the Desktop
package/workspace-lock invariant.

## Verification

- The complete Python suite passed 48,242 tests across 2,325 files with no
  failures. Its only retry was `tests/acp/test_server.py`, which exceeded the
  300-second file budget under 32-way contention and then passed all 92 tests
  in 233.5 seconds when rerun alone.
- The Louis release manifest passed all 2,533 tests across 65 files in the
  dependency-complete loopback environment.
- Integration batches also passed focused Python gates for security, tool
  correctness, CLI and import behavior, startup caching, citations, webhooks,
  STT, TTS, voice mode, and Gateway media routing. The socket/process-sensitive
  TTS subset passed all 77 tests in the dependency-complete environment.
- Desktop Quick Entry passed 44 focused tests. The complete Desktop Vitest run
  passed 3,121 tests with 3 skips, followed by typecheck, lint with 0 errors
  (24 pre-existing warnings), and a production build. An isolated, credential-
  free Electron-to-`hermes serve` onboarding smoke passed all 3 Playwright
  checks.
- The web application passed 113 Vitest tests, typecheck, and the locale parity
  check. The cross-workspace JS release tests passed all 11 tests, typecheck,
  and lint. Docusaurus generated both English and Simplified Chinese static
  sites; its configured non-fatal broken-link and broken-anchor warnings
  remain.
- `scripts/louis-release-tests.txt` now protects redaction, daemon redirects,
  all four tool fixes, `/init`, bang shell mode, lazy startup/cache behavior,
  citations, webhooks, STT, TTS, voice mode, and Gateway media routing.

## Install and update

Existing installations can run `hermes update`. Managed Linux production hosts
can run `hermes-update-louis --dry-run` to validate the candidate before an
explicit `hermes-update-louis` activation. The updater remains Louis-owned and
ff-only; it does not synchronize from the upstream remote.
