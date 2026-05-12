# Calendar Slot Picker Pattern

## UX Flow

1. Calendar shows available dates (have slots)
2. Unavailable dates: grayed out (no availability or past)
3. Click date → show time slot grid
4. Slots show: time, remaining capacity
5. Select slot → show booking form

## Slot Availability Logic

```typescript
// Real-time availability from database
async function getAvailability(serviceId: string, date: Date) {
  const service = await prisma.service.findUnique({ where: { id: serviceId } });
  const bookings = await prisma.booking.aggregate({
    where: { serviceId, bookingDate: date, status: { in: ['PENDING', 'CONFIRMED'] } },
    _count: true
  });

  const totalCapacity = service.capacity;
  const booked = bookings._count;
  return booked < totalCapacity;
}
```

## Library Choice

| Library | Use when |
|---|---|
| react-day-picker | Best for simple date-only selection |
| @fullcalendar/react | For full calendar UI (week/month view) |
| react-datepicker | Lightweight alternative |
