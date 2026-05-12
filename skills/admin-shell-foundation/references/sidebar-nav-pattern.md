# Admin Sidebar Navigation Pattern

## Standard Admin Nav Items

| Label | Icon | Route | Roles with access |
|---|---|---|---|
| Dashboard | LayoutDashboard | /admin | admin, owner |
| Bookings | Calendar | /admin/bookings | admin, owner |
| Guests | Users | /admin/guests | admin |
| Rooms | Bed | /admin/rooms | admin, owner |
| Packages | Package | /admin/packages | admin |
| Meal Windows | Utensils | /admin/meal-windows | admin |
| Payments | CreditCard | /admin/payments | admin |
| Reports | BarChart3 | /admin/reports | admin, owner |
| Settings | Settings | /admin/settings | admin |
| Guest Portal | ExternalLink | / | guest |

## Collapsible Sidebar

- Desktop: collapsed by default, expands on hover or click
- Mobile: drawer overlay
- Width: 240px expanded, 64px collapsed
- Persist collapse state to localStorage

## Active State

- Highlight active route in sidebar with accent color
- Auto-expand parent group when child route is active
