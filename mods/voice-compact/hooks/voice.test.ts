import type { Engine, TestBody } from 'claude-code/testing'
import { expect, test } from 'claude-code/testing'

import { compactText } from './register'

const ORIG_CAVE = 'CAVEMAN MODE ACTIVE — level: full\n\n' + 'Respond terse like smart caveman. '.repeat(60)
const ORIG_PONY = 'PONYTAIL MODE ACTIVE — level: ultra\n\n# Ponytail\n\n' + 'Lazy senior developer. '.repeat(150)

const row = (text: string) => ({
  message: { type: 'user' as const, role: 'user' as const, isMeta: true as const, content: [{ type: 'text' as const, text }] },
})
// The kit has no bottom for session.append: a hook beneath the plugin that
// answers without next is skipped, and next(e) reaches nothing. So the test
// hook beneath records what the plugin passed down, and the call itself is
// allowed to reject. What reached the bottom is the row as the plugin left it.
async function send($: Engine, on: Parameters<TestBody>[1], text: string, door: string): Promise<string> {
  let seen = ''
  on('session.append', (_$, e, next) => {
    seen = e.message.content.map(b => ((b as { text?: string }).text ?? '')).join('')
    return next(e)
  })
  await $.session.append({ ...row(text), door, origin: { kind: 'tool', tool: 'x' }, uuid: 'u0' } as never).catch(() => undefined)
  return seen
}

test('caveman injection on hook-context is replaced by the compact text', async ($, on) => {
  const out = await send($, on, ORIG_CAVE, 'hook-context')
  expect(out).toContain('CAVEMAN MODE ACTIVE — level: full')
  expect(out).toContain('/caveman')
  expect(out.length).toBeLessThan(ORIG_CAVE.length)
})

test('ponytail injection at another level keeps that level', async ($, on) => {
  const out = await send($, on, ORIG_PONY, 'hook-context')
  expect(out).toContain('PONYTAIL MODE ACTIVE — level: ultra')
  expect(out).toContain('/ponytail')
  expect(out.length).toBeLessThan(ORIG_PONY.length)
})

test('unmatched hook-context text passes through byte-identical', async ($, on) => {
  const text = 'Some other hook context.\nNothing about modes.\n'
  expect(await send($, on, text, 'hook-context')).toBe(text)
})

test('a matching text on another door passes through', async ($, on) => {
  expect(await send($, on, ORIG_CAVE, 'prompt')).toBe(ORIG_CAVE)
})

// The pure transform, which does not depend on how the row reaches the hook.
test('compactText: wrapper kept, both injections in one block, short and compact notices untouched', () => {
  const wrapped = `<system-reminder>\nSessionStart hook: ${ORIG_CAVE}\n</system-reminder>`
  const w = compactText(wrapped)
  expect(w.startsWith('<system-reminder>\nSessionStart hook: CAVEMAN MODE ACTIVE — level: full')).toBe(true)
  expect(w.endsWith('\n</system-reminder>')).toBe(true)

  const both = compactText(`${ORIG_CAVE}\n\n${ORIG_PONY}`)
  expect(both).toContain('level: full (compact')
  expect(both).toContain('level: ultra (compact')

  const short = 'CAVEMAN MODE ACTIVE — level: commit. Behavior defined by /caveman-commit skill.'
  expect(compactText(short)).toBe(short)
  const once = compactText(ORIG_CAVE)
  expect(compactText(once)).toBe(once)
  expect(compactText('no marker here')).toBe('no marker here')
})
