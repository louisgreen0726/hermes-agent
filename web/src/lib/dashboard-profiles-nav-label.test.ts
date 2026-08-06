import { describe, expect, it } from 'vitest'

import { en } from '../i18n/en'

describe('dashboard profiles navigation label', () => {
  it('uses the concise navigation copy', () => {
    expect(en.app.nav.profiles).toBe('Profiles')
  })
})
