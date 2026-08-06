import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { StrictMode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { QuickEntryStatePush } from '@/store/quick-entry'

import { QuickEntryApp } from './quick-entry-app'

describe('QuickEntryApp', () => {
  let originalDesktop: Window['hermesDesktop']
  let stateListener: ((payload: QuickEntryStatePush) => void) | null
  const dismiss = vi.fn()
  const submit = vi.fn()

  beforeEach(() => {
    originalDesktop = window.hermesDesktop
    stateListener = null
    dismiss.mockReset()
    submit.mockReset()

    Object.defineProperty(window, 'hermesDesktop', {
      configurable: true,
      value: {
        quickEntry: {
          dismiss,
          onShown: () => () => {},
          onState: (listener: (payload: QuickEntryStatePush) => void) => {
            stateListener = listener

            return () => {
              if (stateListener === listener) {
                stateListener = null
              }
            }
          },
          submit
        }
      } as unknown as Window['hermesDesktop']
    })
  })

  afterEach(() => {
    cleanup()
    Object.defineProperty(window, 'hermesDesktop', { configurable: true, value: originalDesktop })
  })

  function connect(sessions: QuickEntryStatePush['sessions'] = []): void {
    act(() => stateListener?.({ connected: true, sessions }))
  }

  it('submits only once when Enter fires twice in the same frame', () => {
    render(
      <StrictMode>
        <QuickEntryApp />
      </StrictMode>
    )
    connect()

    const input = screen.getByRole('textbox', { name: 'Quick Entry' })
    fireEvent.change(input, { target: { value: '  ship it  ' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(submit).toHaveBeenCalledTimes(1)
    expect(submit).toHaveBeenCalledWith({ target: 'current', text: 'ship it' })
    expect(dismiss).not.toHaveBeenCalled()
  })

  it('keeps blank input open and routes a picked recent session through the submit payload', () => {
    render(<QuickEntryApp />)

    const input = screen.getByRole('textbox', { name: 'Quick Entry' })
    expect((input as HTMLInputElement).disabled).toBe(true)
    expect(input.getAttribute('placeholder')).toBe('Not connected. Open Hermes to reconnect.')

    connect([{ id: 'session-2', title: 'Release review' }])
    fireEvent.change(input, { target: { value: '   ' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(submit).not.toHaveBeenCalled()
    expect(dismiss).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText('Target session'), { target: { value: 'session-2' } })
    fireEvent.change(input, { target: { value: 'review this' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(submit).toHaveBeenCalledWith({ target: 'session-2', text: 'review this' })
  })
})
