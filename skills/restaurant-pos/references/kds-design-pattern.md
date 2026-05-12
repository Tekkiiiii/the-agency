# Kitchen Display System (KDS) Design Pattern

## Layout
- Columns per station: Grill / Fryer / Salad / Dessert / Bar
- Each column: vertical scrolling ticket list
- Tickets: oldest at top (FIFO)
- Auto-advance when all items on ticket are DONE

## Timing Color Coding
| Age | Color | Meaning |
|-----|-------|---------|
| 0-8 min | White | Normal |
| 8-15 min | Orange | Getting late |
| 15+ min | Red + flash | Rush / stuck |

## Bump Flow
1. Server submits order → items fire to KDS
2. Cook taps item → item goes from COOKING to DONE
3. All items done → ticket auto-bumps (or tap to bump early)
4. Server sees "READY" on their POS screen

## Sound
- New item: subtle ping
- 10+ min: louder alert
- Bump: satisfying click sound
