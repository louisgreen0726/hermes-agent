import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import { test } from 'vitest'

const REPO_ROOT = path.resolve(__dirname, '..')

function readJson(file: string): Record<string, unknown> {
  return JSON.parse(fs.readFileSync(path.join(REPO_ROOT, file), 'utf-8'))
}

test('desktop package uses the Louis release version shape', () => {
  const desktopPackage = readJson('apps/desktop/package.json')

  assert.equal(typeof desktopPackage.version, 'string')
  assert.match(desktopPackage.version as string, /^\d+\.\d+\.\d+-louis\.\d+$/)
})

test('workspace lock tracks the desktop package version', () => {
  const desktopPackage = readJson('apps/desktop/package.json')
  const workspaceLock = readJson('package-lock.json')

  const packages = workspaceLock.packages as Record<
    string,
    Record<string, unknown>
  >

  assert.ok(packages['apps/desktop'])

  assert.equal(packages['apps/desktop'].version, desktopPackage.version)
})
