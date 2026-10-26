# Better Auth — Two-Factor Authentication

Adds two-factor authentication via TOTP authenticator apps, email/SMS OTP codes, and backup codes.

## When to Apply

- Adding TOTP (authenticator app) 2FA to Better Auth apps
- Implementing email/SMS OTP verification flows
- Setting up backup code recovery
- Handling 2FA redirects during sign-in
- Configuring trusted device management

## Server Setup

```ts
import { betterAuth } from "better-auth";
import { twoFactor } from "better-auth/plugins";

export const auth = betterAuth({
  appName: "My App",
  plugins: [
    twoFactor({
      issuer: "My App",
    }),
  ],
});
```

Run `npx @better-auth/cli migrate` — creates `twoFactorSecret` column on user table.

## Client Setup

```ts
import { createAuthClient } from "better-auth/client";
import { twoFactorClient } from "better-auth/client/plugins";

export const authClient = createAuthClient({
  plugins: [
    twoFactorClient({
      onTwoFactorRedirect() {
        window.location.href = "/2fa";
      },
    }),
  ],
});
```

## Enabling 2FA for Users

Requires password verification. Returns TOTP URI (for QR code) and backup codes.

```ts
const { data, error } = await authClient.twoFactor.enable({ password });

if (data) {
  // data.totpURI — generate a QR code from this
  // data.backupCodes — display to user
}
```

**⚠️** `twoFactorEnabled` is NOT set to true until first TOTP verification succeeds.

## TOTP (Authenticator App)

**Display QR code:**
```tsx
import QRCode from "react-qr-code";
const TotpSetup = ({ totpURI }: { totpURI: string }) => {
  return <QRCode value={totpURI} />;
};
```

**Verify:**
```ts
const { data, error } = await authClient.twoFactor.verifyTotp({
  code,
  trustDevice: true,
});
// Accepts codes from one period before/after current time
```

**Config:**
```ts
twoFactor({
  totpOptions: {
    digits: 6,  // 6 or 8 (default: 6)
    period: 30, // seconds (default: 30)
  },
});
```

## OTP (Email/SMS)

**Configure delivery:**
```ts
import { sendEmail } from "./email";

export const auth = betterAuth({
  plugins: [
    twoFactor({
      otpOptions: {
        sendOTP: async ({ user, otp }) => {
          await sendEmail({ to: user.email, subject: "Your code", text: `Code: ${otp}` });
        },
        period: 5,         // minutes (default: 3)
        digits: 6,          // default: 6
        allowedAttempts: 5, // per code (default: 5)
      },
    }),
  ],
});
```

**Send:** `authClient.twoFactor.sendOtp()`
**Verify:** `authClient.twoFactor.verifyOtp({ code, trustDevice: true })`

**OTP storage:**
```ts
twoFactor({
  otpOptions: {
    storeOTP: "encrypted", // "plain" | "encrypted" | "hashed"
  },
});
// Custom encryption:
twoFactor({
  otpOptions: {
    storeOTP: {
      encrypt: async (token) => myEncrypt(token),
      decrypt: async (token) => myDecrypt(token),
    },
  },
});
```

## Backup Codes

**Display (generated automatically on enable):**
```tsx
const BackupCodes = ({ codes }: { codes: string[] }) => (
  <ul>{codes.map((code, i) => <li key={i}>{code}</li>)}</ul>
);
```

**Regenerate (invalidates all previous):**
```ts
const { data } = await authClient.twoFactor.generateBackupCodes({ password });
// data.backupCodes — new codes
```

**Verify backup code:**
```ts
const { data } = await authClient.twoFactor.verifyBackupCode({ code, trustDevice: true });
```

**Config:**
```ts
twoFactor({
  backupCodeOptions: {
    amount: 10,              // number of codes (default: 10)
    length: 10,              // chars per code (default: 10)
    storeBackupCodes: "encrypted", // "plain" | "encrypted"
  },
});
```

## Handling 2FA During Sign-In

Response includes `twoFactorRedirect: true` when 2FA is required:

```ts
const signIn = async (email: string, password: string) => {
  const { data, error } = await authClient.signIn.email(
    { email, password },
    {
      onSuccess(context) {
        if (context.data.twoFactorRedirect) {
          window.location.href = "/2fa";
        }
      },
    }
  );
};
```

**Server-side:** check `"twoFactorRedirect"` in response when using `auth.api.signInEmail`.

## Trusted Devices

Pass `trustDevice: true` when verifying. Default trust: 30 days (`trustDeviceMaxAge`). Refreshes on each sign-in.

## Security

**Session flow:** credentials → session removed → temp 2FA cookie (10 min) → verify → session created.

```ts
twoFactor({ twoFactorCookieMaxAge: 600 }); // seconds (default: 600)
```

**Rate limiting:**
- 3 requests per 10 seconds on all 2FA endpoints
- OTP: configurable `allowedAttempts` per code

**Encryption at rest:**
- TOTP secrets: encrypted with auth secret
- Backup codes: encrypted by default
- OTP: configurable

**⚠️** 2FA can only be enabled for credential (email/password) accounts.

## Disabling 2FA

Requires password confirmation. Revokes trusted device records:

```ts
const { data } = await authClient.twoFactor.disable({ password });
```

---

**Source:** https://officialskills.sh/better-auth/skills/twoFactor