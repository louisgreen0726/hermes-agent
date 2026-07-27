# Louis Hermes Agent 0.19.0.1

> [!NOTE]
> This is the historical record for the versioned 0.19.0.1 baseline. Changes
> merged into `main` afterward are tracked separately in the
> [release-notes index](../../LOUIS_RELEASE_NOTES.md).

Release date: 2026-07-27

Louis Hermes Agent 0.19.0.1 is based on Nous Research Hermes Agent 0.19.0
(upstream release 2026.7.20). It is an independently maintained Louis release,
not an official Nous Research release. The upstream license and attribution
are preserved.

## Highlights

- Telegram Native Guest Mode lets approved guests use the agent without being
  treated as the bot owner.
- Guest replies render rich Markdown tables natively instead of flattening
  them to plain text.
- Ordinary Telegram replies preserve CJK rich-message formatting.
- Rich tables stay consistent across direct replies, cron delivery, and
  standalone `send_message` delivery.

## Louis release boundary

- Automatic source updates trust only
  `https://github.com/louisgreen0726/hermes-agent` as `origin` and update from
  the configured Louis branch, normally `origin/main`.
- CLI and Desktop checks reject a missing or non-Louis origin before any
  remote probe or fetch. Louis SSH installs use anonymous HTTPS for passive
  probes so background checks do not trigger SSH or hardware-key prompts.
- `hermes-update-louis` validates the candidate in an isolated worktree,
  verifies the release regression suite before and after dependency changes,
  creates a bundle of the previous release, and activates only a fast-forward
  Louis commit.
- If activation or Gateway startup fails, the updater restores the previous
  commit and Python editable install. A previously running Gateway is restarted
  only after that rollback succeeds.
- Native Windows installations without Git metadata use the fixed Louis ZIP
  archive path rather than consulting another repository.

## Install and update

Linux, macOS, WSL2, and Termux:

```bash
curl -fsSL https://raw.githubusercontent.com/louisgreen0726/hermes-agent/main/scripts/install.sh | bash
```

Native Windows PowerShell:

```powershell
iex (irm https://raw.githubusercontent.com/louisgreen0726/hermes-agent/main/scripts/install.ps1)
```

Existing source installations can run `hermes update`. Linux production hosts
with a user-level systemd service can use `hermes-update-louis` for the guarded
worktree, rollback, and Gateway health workflow. Desktop supports Linux, macOS,
and Windows; release assets are published only on the Louis GitHub Releases
page.

## Known limitations

- Louis does not currently publish a prebuilt Docker image. Build
  `louis-hermes-agent:local` from this repository's `Dockerfile` and restart
  the container; pulling a Nous Research image switches distributions.
- The protected `hermes-update-louis` worker requires Linux, `systemd --user`,
  and the managed source layout. Other platforms use their normal Louis CLI,
  ZIP, or Desktop update path.
- A Desktop installer may not be attached for every platform. When no Louis
  asset is present, install the Louis CLI and run `hermes desktop` to build it
  locally.
- The public documentation and Nous-hosted services describe the upstream
  Hermes foundation. Louis-specific distribution and update policy lives in
  [LOUIS.md](../../LOUIS.md).

## Verification coverage

This release is gated by the Louis update/release suite, the Telegram Guest
Mode and rich-delivery regression set, model-catalog and packaging integrity
checks, Desktop TypeScript and Electron platform tests, installer manifest
checks, and an updater integration test that exercises activation failure and
rollback from a real shallow clone.
