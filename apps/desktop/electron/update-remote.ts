/**
 * Pure helpers for choosing a remote URL during passive update checks.
 *
 * A Louis install can use `origin=git@github.com:louisgreen0726/hermes-agent.git`.
 * If the user's GitHub SSH key is FIDO2/passkey-backed, a background `git fetch
 * origin` triggers an unexplained hardware-touch prompt. Louis SSH installs
 * therefore use the public HTTPS URL for read-only probes, which needs no auth
 * and cannot prompt. Both passive checks and apply-time branch healing reject
 * non-Louis origins before any remote probe or fetch.
 *
 * Extracted from main.ts so the security-critical remote detection is unit
 * testable without booting Electron (main.ts requires('electron') at load).
 */

const LOUIS_REPO_HTTPS_URL = 'https://github.com/louisgreen0726/hermes-agent.git'
const LOUIS_REPO_CANONICAL = 'github.com/louisgreen0726/hermes-agent'

// Normalize common GitHub remote URL forms to `host/owner/repo` (lowercased,
// no trailing slash, no .git suffix) so SSH and HTTPS forms of the same repo
// compare equal.
function canonicalGitHubRemote(url) {
  if (!url) {
    return ''
  }

  let value = String(url).trim()

  if (value.startsWith('git@github.com:')) {
    value = `github.com/${value.slice('git@github.com:'.length)}`
  } else if (value.startsWith('ssh://git@github.com/')) {
    value = `github.com/${value.slice('ssh://git@github.com/'.length)}`
  } else {
    try {
      const parsed = new URL(value)

      if (parsed.hostname && parsed.pathname) {
        value = `${parsed.hostname}${parsed.pathname}`
      }
    } catch {
      // Leave non-URL forms unchanged.
    }
  }

  value = value.trim().replace(/\/+$/, '')

  if (value.endsWith('.git')) {
    value = value.slice(0, -4)
  }

  return value.toLowerCase()
}

function isSshRemote(url) {
  const value = String(url || '')
    .trim()
    .toLowerCase()

  return value.startsWith('git@') || value.startsWith('ssh://')
}

function isLouisRemote(url) {
  return canonicalGitHubRemote(url) === LOUIS_REPO_CANONICAL
}

function isLouisSshRemote(url) {
  return isSshRemote(url) && isLouisRemote(url)
}

function selectLouisUpdateRemote(url) {
  if (!isLouisRemote(url)) {
    return null
  }

  return isLouisSshRemote(url) ? LOUIS_REPO_HTTPS_URL : 'origin'
}

export {
  canonicalGitHubRemote,
  isLouisRemote,
  isLouisSshRemote,
  isSshRemote,
  LOUIS_REPO_CANONICAL,
  LOUIS_REPO_HTTPS_URL,
  selectLouisUpdateRemote
}
