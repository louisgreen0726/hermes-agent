/**
 * Tests for electron/update-remote.ts — the remote-detection helpers that
 * keep passive update checks off SSH and fail closed outside Louis releases.
 *
 * Run with: node --test electron/update-remote.test.ts
 * (Wired into npm test:desktop:platforms in package.json.)
 *
 * Why this matters: a public install can carry
 * origin=git@github.com:louisgreen0726/hermes-agent.git. A background
 * `git fetch origin` then authenticates over SSH and, with a FIDO2/passkey
 * key, triggers an unexplained hardware-touch prompt. isLouisSshRemote
 * must reliably recognize the Louis SSH remote (in every URL form,
 * case-insensitively) so the caller can swap in the anonymous HTTPS path —
 * while NOT misclassifying forks, other hosts, or the HTTPS remote (which
 * never prompts and should keep the normal fetch path).
 */

import assert from 'node:assert/strict'

import { test } from 'vitest'

import {
  canonicalGitHubRemote,
  isLouisRemote,
  isLouisSshRemote,
  isSshRemote,
  LOUIS_REPO_CANONICAL,
  LOUIS_REPO_HTTPS_URL,
  selectLouisUpdateRemote
} from './update-remote'

test('canonicalGitHubRemote normalizes SSH and HTTPS forms to the same value', () => {
  assert.equal(canonicalGitHubRemote('git@github.com:louisgreen0726/hermes-agent.git'), LOUIS_REPO_CANONICAL)
  assert.equal(canonicalGitHubRemote('git@github.com:louisgreen0726/hermes-agent'), LOUIS_REPO_CANONICAL)
  assert.equal(canonicalGitHubRemote('ssh://git@github.com/louisgreen0726/hermes-agent.git'), LOUIS_REPO_CANONICAL)
  assert.equal(canonicalGitHubRemote('https://github.com/louisgreen0726/hermes-agent.git'), LOUIS_REPO_CANONICAL)
  // Case-insensitive: an uppercased owner still canonicalizes to the same repo.
  assert.equal(canonicalGitHubRemote('git@github.com:LouisGreen0726/hermes-agent.git'), LOUIS_REPO_CANONICAL)
  // Trailing slashes are stripped.
  assert.equal(canonicalGitHubRemote('https://github.com/louisgreen0726/hermes-agent/'), LOUIS_REPO_CANONICAL)
})

test('canonicalGitHubRemote is empty for falsy input', () => {
  assert.equal(canonicalGitHubRemote(''), '')
  assert.equal(canonicalGitHubRemote(null), '')
  assert.equal(canonicalGitHubRemote(undefined), '')
})

test('isSshRemote detects scp-like and ssh:// forms only', () => {
  assert.equal(isSshRemote('git@github.com:louisgreen0726/hermes-agent.git'), true)
  assert.equal(isSshRemote('ssh://git@github.com/louisgreen0726/hermes-agent.git'), true)
  assert.equal(isSshRemote('https://github.com/louisgreen0726/hermes-agent.git'), false)
  assert.equal(isSshRemote(''), false)
  assert.equal(isSshRemote(null), false)
})

test('isLouisSshRemote is true only for the Louis repo over SSH', () => {
  assert.equal(isLouisSshRemote('git@github.com:louisgreen0726/hermes-agent.git'), true)
  assert.equal(isLouisSshRemote('git@github.com:louisgreen0726/hermes-agent'), true)
  assert.equal(isLouisSshRemote('ssh://git@github.com/louisgreen0726/hermes-agent.git'), true)
  // Case-insensitive owner/repo match.
  assert.equal(isLouisSshRemote('git@github.com:LouisGreen0726/hermes-agent.git'), true)
})

test('Louis remote selection rejects other repositories before network access', () => {
  assert.equal(isLouisRemote('https://github.com/louisgreen0726/hermes-agent.git'), true)
  assert.equal(isLouisRemote('https://github.com/NousResearch/hermes-agent.git'), false)
  assert.equal(isLouisRemote('git@github.com:someuser/hermes-agent.git'), false)
  assert.equal(isLouisRemote('git@gitlab.com:louisgreen0726/hermes-agent.git'), false)
  assert.equal(selectLouisUpdateRemote('https://github.com/NousResearch/hermes-agent.git'), null)
  assert.equal(selectLouisUpdateRemote(''), null)
})

test('Louis SSH probes use anonymous HTTPS while Louis HTTPS keeps origin', () => {
  assert.equal(selectLouisUpdateRemote('git@github.com:louisgreen0726/hermes-agent.git'), LOUIS_REPO_HTTPS_URL)
  assert.equal(selectLouisUpdateRemote('https://github.com/louisgreen0726/hermes-agent.git'), 'origin')
  assert.equal(canonicalGitHubRemote(LOUIS_REPO_HTTPS_URL), LOUIS_REPO_CANONICAL)
})
