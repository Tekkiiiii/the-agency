# Google Workspace — Chat

Google Chat spaces, messages, memberships, and bot integration via `gws`.

## When to Apply

- Creating or managing Google Chat spaces
- Sending messages to spaces or direct messages
- Managing space memberships
- Uploading/downloading chat media attachments
- Custom emoji management

## Prerequisites

Read `../gws-shared/SKILL.md` for auth, global flags, and security rules.
If missing: `gws generate-skills`

## Usage

```bash
gws chat <resource> <method> [flags]
```

## Helper Commands

| Command | Description |
|---------|-------------|
| `+send` | Send a message to a space |

## Resources & Methods

**customEmojis:** `create`, `delete`, `get`, `list`
**media:** `download`, `upload`
**spaces:** `create`, `delete`, `get`, `list`, `patch`, `search`, `setup`, `completeImport`, `findDirectMessage`
**members:** membership management
**messages:** `list`, `get`, `create`, `delete`, `patch`
**spaceEvents:** event tracking
**users/spaces:** cross-user space operations

## Discovery

```bash
gws chat --help
gws schema chat.<resource>.<method>
```

---

**Source:** https://officialskills.sh/googleworkspace/skills/gws-chat