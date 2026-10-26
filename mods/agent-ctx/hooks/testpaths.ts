// COPY of mods/_shared/testpaths.ts, edit there and re-copy; mods cannot import outside their plugin folder
// Test-only helper (never imported by a register file): lets a stub compare the paths a hook reads/writes on any host.

// The kit runs every path through the HOST's path.resolve before a stub sees it, so the same hook code shows a stub:
//   macOS/Linux  'C:\Users\x/.claude/x'  ->  '<plugin folder>/C:\Users\x/.claude/x'   (not absolute there)
//   Windows      'C:\Users\x/.claude/x'  ->  'C:\Users\x\.claude\x'                    (separators rewritten)
//   Windows      '/home/t/.claude/x'     ->  'D:\home\t\.claude\x'                     (host drive prepended)
// Both helpers return one spelling for all of them, so each expectation stays as strict as before.

/** A Windows-style path as the hook built it: drive kept, sim prefix dropped, '\' -> '/'. 'C:/Users/x/.claude/x'. */
export const seenWin = (p: string): string => p.replace(/^.*?(?=[A-Za-z]:\\)/, '').replace(/\\/g, '/')

/** A POSIX-style path as the hook built it: host drive dropped, '\' -> '/'. '/home/t/.claude/x'. */
export const seenPosix = (p: string): string => seenWin(p).replace(/^[A-Za-z]:(?=\/)/, '')
