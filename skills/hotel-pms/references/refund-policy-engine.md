# Hotel PMS Refund Policy Engine

## Cancellation Tiers (Standard)

| Time before check-in | Refund |
|---|---|
| 72h+ | 100% of deposit |
| 48-72h | 75% of deposit |
| 24-48h | 50% of deposit |
| <24h | 0% — no refund |

## Configurable per Package

Each HotelPackage has:
- `cancellationHours`: hours before check-in that triggers non-refund
- `depositPercentage`: % of total price required as deposit

## Flow

1. User initiates cancellation
2. System calls `calculateRefund()` with reservation + package settings
3. Shows refund amount + reason to user
4. On confirmation: mark `refundEligible=false`, trigger Paymob refund if applicable
5. Update reservation status to `CANCELLED`
6. Log cancellation event
