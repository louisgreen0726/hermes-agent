# Louis Hermes Agent

This repository is the production source for the Louis distribution of Hermes Agent.

## Identity

- Product repository: `https://github.com/louisgreen0726/hermes-agent`
- Release branch: `main`
- User-facing version: `Louis-0.19.0.1`
- Python package version: `0.19.0+Louis.1`
- Upstream project: `https://github.com/NousResearch/hermes-agent`

The project is based on Hermes Agent by Nous Research and remains distributed under the MIT License. It is an independently maintained fork and is not an official Nous Research release.

## Release policy

`origin/main` is the only automatic update source. The `upstream` remote may be retained for manual review, but ordinary `hermes update`, `hermes-update-louis`, and the gateway `/update` command never merge, rebase, pull, or synchronize from it.

Upstream changes are adopted only through an explicit integration branch, code review, and the Louis regression suite. They are then committed to this repository as a new Louis release.

## Local capabilities

The first Louis release carries:

- Telegram Native Guest Mode.
- Native Rich Markdown table delivery in Telegram Guest Mode.
- CJK Rich Message delivery for ordinary replies.
- Rich table consistency for cron and standalone sends.
- Regression coverage for Telegram routing, authorization, rich delivery, threads, proxy mode, and delivery ledger behavior.

## Updating

Production machines use `hermes-update-louis`. The updater validates `origin/main` in an isolated worktree, runs the Louis regression suite, updates dependencies, verifies the candidate again, activates the validated commit, and restarts the gateway only after integrity checks pass.

The gateway launches updates in an independent transient user service so the updater survives the intentional Gateway stop/restart window. Progress and the final exit code are delivered through durable marker files.

Do not use `git pull upstream main` on a production checkout.
