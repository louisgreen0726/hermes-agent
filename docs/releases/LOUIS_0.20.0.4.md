# Louis Hermes Agent 0.20.0.4

Release date: 2026-08-14

Louis Hermes Agent 0.20.0.4 fixes ordinary Markdown rendering in Telegram
Native Guest Mode and restores a bounded scope for the protected-update release
gate. It is an independently maintained Louis release, not an official Nous
Research release. The selectively integrated upstream baseline remains Hermes
Agent 0.20.0 (upstream release 2026.8.3).

## Telegram Native Guest Markdown

- Ordinary Markdown replies now use Telegram MarkdownV2 through
  `InputTextMessageContent`, rather than sending raw Markdown as plain text.
- Bold, italic, strikethrough, links, inline and fenced code, block quotes, and
  ordered and unordered lists retain their intended Telegram rendering.
- Pipe tables, task lists, `<details>` blocks, and block math continue to use
  Bot API 10.1 `InputRichMessageContent.rich_message` when rich delivery is
  enabled and eligible.

## Delivery safety and compatibility

- Guest replies still make exactly one `answerGuestQuery` call. A rejected
  request is not retried or resent as a second message.
- Non-rich replies keep the existing 4,096 UTF-16-unit limit and are truncated
  before Markdown conversion, so a cut construct is escaped before the only API
  call.
- Ordinary Telegram private and group delivery paths are unchanged.
- No configuration or data migration is required.

## Bounded protected-update gate

- `scripts/louis-release-tests.txt` now contains only update command and
  progress delivery, Louis distribution, protected-updater, managed-install,
  update-check, and release-metadata contracts.
- Telegram, provider, TTS, backup, tool, and UI regressions remain in normal CI
  and in focused change validation instead of being rerun as part of every
  production update.
- Candidate ownership, strict path validation, and checks before and after
  candidate dependency installation remain unchanged.

## Release metadata

- CLI version: `Louis-0.20.0.4`
- Python package version: `0.20.0+Louis.4`
- Desktop package version: `0.20.0-louis.4`
- Selectively integrated upstream baseline: Hermes Agent `0.20.0`, release
  `2026.8.3`

## Verification

- Telegram Native Guest Mode tests passed 12 tests.
- Telegram MarkdownV2 and rich-message tests passed 182 tests across two files.
- JavaScript release-version metadata passed 2 tests.
- The bounded Louis protected-update gate passed 157 tests across all nine
  manifest files.

## Install and update

Existing installations can run `hermes update`. Managed Linux production hosts
can run `hermes-update-louis --dry-run` before an explicit
`hermes-update-louis` activation. The updater remains Louis-owned and ff-only;
it does not synchronize from the upstream remote.
