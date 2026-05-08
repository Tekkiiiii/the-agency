# Better Auth — Organization

Multi-tenant organization, team, and role management for Better Auth.

## When to Apply

- Setting up multi-tenant organization structures
- Managing team membership and role-based permissions
- Implementing invitation flows with email triggers
- Building dynamic access control beyond default roles
- Schema customization for organization/member tables

## Server Setup

```ts
import { betterAuth } from "better-auth";
import { organization } from "better-auth/plugins";

export const auth = betterAuth({
  plugins: [
    organization({
      allowUserToCreateOrganization: true,
      organizationLimit: 5,
      membershipLimit: 100,
    }),
  ],
});
```

Run `npx @better-auth/cli migrate` — creates `organization`, `member`, `invitation` tables.

## Client Setup

```ts
import { createAuthClient } from "better-auth/client";
import { organizationClient } from "better-auth/client/plugins";

export const authClient = createAuthClient({
  plugins: [organizationClient()],
});
```

## Creating Organizations

The creator is automatically assigned the **owner** role:

```ts
const { data, error } = await authClient.organization.create({
  name: "My Company",
  slug: "my-company",
  logo: "https://example.com/logo.png",
  metadata: { plan: "pro" },
});
```

**Controlling who can create:**

```ts
organization({
  allowUserToCreateOrganization: async (user) => user.emailVerified === true,
  organizationLimit: async (user) => user.plan === "premium" ? 20 : 3,
});
```

**Server-side creation for admins:**

```ts
await auth.api.createOrganization({
  body: {
    name: "Client Organization",
    slug: "client-org",
    userId: "user-id-who-will-be-owner", // required
  },
});
// Note: userId cannot be used with session headers
```

## Active Organization

Stored in session, scopes subsequent API calls:

```ts
await authClient.organization.setActive({ organizationId });
// Many endpoints use active org when organizationId not provided
```

## Members

**Server-side add:**
```ts
await auth.api.addMember({
  body: { userId, role: "member", organizationId },
});
// Use invitation system for client-side additions

await auth.api.addMember({
  body: { userId, role: ["admin", "moderator"] },
}); // multiple roles
```

**Remove:** `authClient.organization.removeMember({ memberIdOrEmail })`
**Update role:** `authClient.organization.updateMemberRole({ memberId, role })`

**⚠️ Owner protection:** Last owner cannot be removed — transfer ownership first.

**Dynamic membership limits:**
```ts
organization({
  membershipLimit: async (user, organization) => {
    return organization.metadata?.plan === "enterprise" ? 1000 : 50;
  },
});
```

## Invitations

**Setup email handler:**
```ts
organization({
  sendInvitationEmail: async (data) => {
    const { email, organization, inviter, invitation } = data;
    await sendEmail({ to: email, subject: `Join ${organization.name}`, html: `...` });
  },
});
```

**Send invitation:**
```ts
await authClient.organization.inviteMember({ email, role: "member" });
```

**Shareable URL (no email sent — handle delivery yourself):**
```ts
const { data } = await authClient.organization.getInvitationURL({
  email, role, callbackURL: "https://app.com/dashboard",
});
// Share data.url via any channel
```

**Config:**
```ts
organization({
  invitationExpiresIn: 60 * 60 * 24 * 7, // 7 days (default: 48h)
  invitationLimit: 100,
  cancelPendingInvitationsOnReInvite: true,
});
```

## Roles & Permissions

**Default roles:** owner (full), admin (manage members/invites/settings), member (basic).

**Check permission:**
```ts
const { data } = await authClient.organization.hasPermission({ permission: "member:write" });
```

Use `checkRolePermission({ role, permissions })` for static UI rendering.

## Teams

**Enable:**
```ts
organization({ teams: { enabled: true } })
```

**Create/manage:**
```ts
authClient.organization.createTeam({ name: "Engineering" });
authClient.organization.addTeamMember({ teamId, userId }); // user must be in org first
authClient.organization.removeTeamMember({ teamId, userId }); // stays in org
authClient.organization.setActiveTeam({ teamId });
```

**Limits:**
```ts
organization({
  teams: {
    maximumTeams: 20,
    maximumMembersPerTeam: 50,
    allowRemovingAllTeams: false,
  },
});
```

## Dynamic Access Control

Requires `@better-auth/organization/addons`:

```ts
organization({ dynamicAccessControl: { enabled: true } })

// Create custom roles
await authClient.organization.createRole({
  role: "moderator",
  permission: { member: ["read"], invitation: ["read"] },
});
// Use updateRole({ roleId, permission }) and deleteRole({ roleId })
// Pre-defined roles (owner/admin/member) cannot be deleted
```

## Lifecycle Hooks

```ts
organization({
  hooks: {
    organization: {
      beforeCreate: async ({ data, user }) => ({
        data: { ...data, metadata: { ...data.metadata, createdBy: user.id } },
      }),
      afterCreate: async ({ organization, member }) => {
        await createDefaultResources(organization.id);
      },
      beforeDelete: async ({ organization }) => {
        await archiveOrganizationData(organization.id);
      },
    },
    member: {
      afterCreate: async ({ member, organization }) => {
        await notifyAdmins(organization.id, `New member joined`);
      },
    },
    invitation: {
      afterCreate: async ({ invitation, organization, inviter }) => {
        await logInvitation(invitation);
      },
    },
  },
});
```

## Schema Customization

```ts
organization({
  schema: {
    organization: {
      modelName: "workspace",
      fields: { name: "workspaceName" },
      additionalFields: {
        billingId: { type: "string", required: false },
      },
    },
    member: {
      additionalFields: {
        department: { type: "string", required: false },
        title: { type: "string", required: false },
      },
    },
  },
});
```

## Security

- **Owner protection:** Last owner cannot be removed or leave without ownership transfer
- **Invitations expire** after 48h by default
- **Only invited email** can accept
- **Delete prevention:**
  ```ts
  organization({ disableOrganizationDeletion: true })
  // Or soft-delete via beforeDelete hook that throws
  ```

---

**Source:** https://officialskills.sh/better-auth/skills/organization