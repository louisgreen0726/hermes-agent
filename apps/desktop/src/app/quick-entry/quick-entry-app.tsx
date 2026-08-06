import { useCallback, useEffect, useRef, useState } from 'react'

import { controlVariants } from '@/components/ui/control'
import { Input } from '@/components/ui/input'
import { useI18n } from '@/i18n'
import { cn } from '@/lib/utils'
import {
  initialQuickComposerState,
  QUICK_TARGET_CURRENT,
  QUICK_TARGET_NEW,
  type QuickComposerEvent,
  quickComposerReducer
} from '@/store/quick-entry'

/**
 * The Quick Entry composer — the whole renderer surface of the global-hotkey
 * mini window. Deliberately one input plus a session-target picker and nothing
 * else: this is a capture surface, not a second chat.
 *
 * All behavior rides `quickComposerReducer` (pure, unit-tested): submit sends
 * the trimmed text + target through the shell and asks to hide; an empty submit
 * does neither so a stray Enter can't make the window vanish; Escape and losing
 * focus dismiss without sending; a dead gateway disables the input entirely
 * (the reducer refuses the send AND the input paints the reconnect hint).
 *
 * The window itself has no gateway connection. Its view of backend truth — is
 * the gateway up, which recent sessions exist — is pushed in by the primary
 * renderer through main (`onState`), and its text goes back the same road to
 * the primary renderer's normal prompt-submit path.
 */
export function QuickEntryApp() {
  const { t } = useI18n()
  const q = t.settings.quickEntry
  const inputRef = useRef<HTMLInputElement>(null)
  const stateRef = useRef(initialQuickComposerState)
  const [state, setState] = useState(initialQuickComposerState)

  // Keep effects outside React's reducer/updater callbacks: Strict Mode may
  // invoke those callbacks twice. The ref advances synchronously so two Enter
  // events in one frame still see `submitting: true` after the first send.
  const dispatch = useCallback((event: QuickComposerEvent) => {
    const current = stateRef.current
    const { send, state: next } = quickComposerReducer(current, event)
    const api = window.hermesDesktop?.quickEntry

    stateRef.current = next
    setState(next)

    if (send) {
      api?.submit(send)
    } else if (!next.visible && current.visible) {
      api?.dismiss()
    }
  }, [])

  // Re-summoned by the chord: the shell reuses the window, so reset the draft
  // and take the keyboard back for a fresh capture. Also adopt gateway-state
  // pushes (connection + recent sessions) relayed from the primary renderer.
  useEffect(() => {
    const api = window.hermesDesktop?.quickEntry

    const offShown = api?.onShown(() => {
      dispatch({ type: 'shown' })
      requestAnimationFrame(() => inputRef.current?.focus())
    })

    const offState = api?.onState(payload => {
      dispatch({
        connected: payload?.connected === true,
        sessions: Array.isArray(payload?.sessions) ? payload.sessions : [],
        type: 'state'
      })
    })

    inputRef.current?.focus()

    return () => {
      offShown?.()
      offState?.()
    }
  }, [dispatch])

  return (
    <div className="flex h-screen w-screen items-center justify-center p-3">
      <div className="flex w-full flex-col gap-2 rounded-md border border-(--stroke-nous) bg-(--ui-chat-bubble-background) px-3.5 py-2.5 shadow-nous">
        <Input
          aria-label={q.inputLabel}
          disabled={!state.connected}
          onBlur={event => {
            // Moving focus to the target picker is not leaving the window.
            if (!event.relatedTarget) {
              dispatch({ type: 'blur' })
            }
          }}
          onChange={event => dispatch({ draft: event.target.value, type: 'edit' })}
          onKeyDown={event => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              dispatch({ type: 'submit' })
            } else if (event.key === 'Escape') {
              event.preventDefault()
              dispatch({ type: 'dismiss' })
            }
          }}
          placeholder={state.connected ? q.promptPlaceholder : q.disconnectedPlaceholder}
          prefix={
            <span aria-hidden className="text-sm leading-none text-(--ui-text-tertiary)">
              ›
            </span>
          }
          ref={inputRef}
          size="lg"
          value={state.draft}
        />
        <div className="flex items-center gap-2">
          <label
            className="shrink-0 text-[0.6875rem] text-(--ui-text-tertiary) select-none"
            htmlFor="quick-entry-target"
          >
            {q.sendTo}
          </label>
          <select
            aria-label={q.targetLabel}
            className={cn(controlVariants({ size: 'xs' }), 'max-w-80 flex-1')}
            disabled={!state.connected}
            id="quick-entry-target"
            onChange={event => dispatch({ target: event.target.value, type: 'target' })}
            onKeyDown={event => {
              if (event.key === 'Escape') {
                event.preventDefault()
                dispatch({ type: 'dismiss' })
              }
            }}
            value={state.target}
          >
            <option value={QUICK_TARGET_CURRENT}>{q.currentChat}</option>
            <option value={QUICK_TARGET_NEW}>{q.newSession}</option>
            {state.sessions.map(session => (
              <option key={session.id} value={session.id}>
                {session.title}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  )
}
