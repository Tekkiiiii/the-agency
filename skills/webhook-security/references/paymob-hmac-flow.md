# Paymob HMAC Webhook Flow

## Verification Steps
1. Receive POST request with `hmac` query param
2. Read raw request body (do NOT use parsed JSON — use raw bytes)
3. Compute: `HMAC-SHA512(hmac_secret, raw_body)` → hex string
4. Compare with `hmac` param using `hash_equals()` / `timingSafeEqual`
5. If mismatch → 401 immediately
6. If match → parse body JSON

## Idempotency
- Paymob sends SAME webhook multiple times on failure
- Use `merchant_order_id` as idempotency key
- Check: `SELECT id FROM webhook_events WHERE paymob_order_id = ? LIMIT 1`
- If found → return 200, skip processing

## Refund Flow
1. POST /v1/auth/tokens → get token
2. POST /v1/acceptance/payments/refund with transaction_id + amount
3. Webhook fires `transaction.refund` on success

## Test Cards (Paymob test mode)
- Card: 4200000000000000
- OTP: any 6 digits
- 3DS bypass in test mode
