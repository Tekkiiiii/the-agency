# Changelog

Mọi thay đổi đáng chú ý của The Agency được ghi lại tại đây, nhóm theo từng đợt phát hành (đánh số theo ngày — repo này không có file version riêng, nên ngày tháng là nguồn duy nhất và không bao giờ lệch khỏi lịch sử git).

All notable changes to The Agency are documented here, grouped by release wave (date-based — this repo has no separate version file, so dates are the single source of truth and can never desync from git history).

## [Unreleased]

### Tiếng Việt

#### Added
- `agency upgrade` giờ in ra các mục CHANGELOG.md tương ứng với những gì vừa được pull về sau một lần upgrade thành công — cơ chế best-effort dựa trên date-header (không mapping theo commit-hash, không thêm dependency mới), giới hạn khoảng 40 dòng kèm link trỏ tới CHANGELOG.md cho phần còn lại. Im lặng khi đã ở phiên bản mới nhất.

#### Fixed
- `scripts/` (save-state.py, mem-gardener.sh, setup-graphify.sh, v.v.) giờ được `agency init` và `agency upgrade` deploy vào `{agency root}/scripts/` — trước đây thư mục này chưa từng được sync, nên bất kỳ skill nào tham chiếu `~/.claude/scripts/...` (ví dụ `/save-state`) sẽ báo lỗi "file not found" trên một bản cài mới.
- Đã xóa các ví dụ đường dẫn tuyệt đối cá nhân (`/Users/Tekki/...`) hardcode trong 5 file agent/skill vốn được thiết kế để chạy chung cho mọi user — trong đó 2 trường hợp là bug chức năng thật sự (hướng dẫn agent ghi y nguyên chuỗi `/Users/Tekki` vào file của một user khác).

### English

#### Added
- `agency upgrade` now prints the CHANGELOG.md entries covering what was just pulled after a successful upgrade — best-effort, date-header based (no commit-hash mapping, no new deps), capped at ~40 lines with a pointer to CHANGELOG.md for the rest. Silent when already up to date.

#### Fixed
- `scripts/` (save-state.py, mem-gardener.sh, setup-graphify.sh, etc.) is now deployed to `{agency root}/scripts/` by `agency init` and `agency upgrade` — previously it was never synced, so any skill referencing `~/.claude/scripts/...` (e.g. `/save-state`) would fail on a clean install with a "file not found" error.
- Removed hardcoded personal absolute-path examples (`/Users/Tekki/...`) from 5 shipped agent/skill files that are meant to run generically for any user — two of these were functional bugs (instructions that told the agent to literally write the string `/Users/Tekki` into another user's own files).

## [2026-07-24] — Skill sync self-heal (`00cd410`)

### Tiếng Việt

#### Fixed
- Cơ chế sync skill được viết lại để so sánh theo content-hash — mtime/size vốn không đáng tin cậy sau khi `git checkout` reset lại timestamp của file, khiến quá trình cài đặt có thể âm thầm bỏ qua các file skill đã cập nhật.
- Layout thư mục `skills/<name>/SKILL.md` giờ là layout canonical duy nhất. Thay đổi này tự self-heal mọi bản cài từng bị "nhiễm" bởi một file `skills/<name>.md` dạng flat — vốn vô hình với cơ chế sync và chưa bao giờ đến được các bản cài.

### English

#### Fixed
- Skills sync rewritten to content-hash comparison — mtime/size were unreliable after a `git checkout` resets file timestamps, which meant installs could silently skip updated skill files.
- Directory-only `skills/<name>/SKILL.md` is now the sole canonical layout. This self-heals any install previously poisoned by a flat `skills/<name>.md` file, which was invisible to the sync and never reached installs.

## [2026-07-22] (`dd9d64f`)

### Tiếng Việt

#### Security
- Thêm một lượt scrub private-slug khỏi các asset được sync, đóng lỗ hổng khiến slug nội bộ của project có thể rò rỉ vào các file được ship ra ngoài.

#### Added
- Bộ ba MCP-schema-overload và sync dept-coord (wave 8+9).

### English

#### Security
- Additional private-slug scrub from synced assets, closing a gap where internal project slugs could leak into shipped files.

#### Added
- MCP-schema-overload trio and dept-coord sync (wave 8+9).

## [2026-07-16] (`fab3727`, `9958328`)

### Tiếng Việt

#### Deprecated
- Tier orchestration `lite` — dự kiến gỡ bỏ, xem `docs/tiers.md`.

#### Security
- Đã scrub PII (địa chỉ email cá nhân, GTM container ID) khỏi tài liệu công khai.

### English

#### Deprecated
- `lite` orchestration tier — scheduled for removal, see `docs/tiers.md`.

#### Security
- Scrubbed PII (personal email address, GTM container ID) from public docs.

## [2026-07-13 to 2026-07-14] (`7162f84`, `e0b0e5c`)

### Tiếng Việt

#### Added
- Bộ công cụ Memory v2 P2/P3 và runbook cho gardener.
- Công cụ orchestrator: tài liệu floor và context-budget.
- Đồng bộ lesson (wave 6).

### English

#### Added
- Memory v2 P2/P3 tooling and gardener runbook.
- Orchestrator tools: floor and context-budget documentation.
- Lesson sync (wave 6).

## [2026-07-03 to 2026-07-07] (`cf2bf3e`, `46daa28`, `801c548`, `eb6f60a`, `7ef9710`)

### Tiếng Việt

#### Added
- Nguyên tắc định tuyến lookup-first cho Delegator.
- Hook kỷ luật reasoning cho Fable-on-Opus.

#### Fixed
- Tình trạng git-dirty churn liên tục ở mỗi lần `agency upgrade`.
- Spam relink CLI giả (false positive) ở mỗi lần `agency upgrade`.

#### Changed
- Tinh gọn hiệu quả token cho PD/Coord (`N_global=5`).

### English

#### Added
- Lookup-first Delegator routing doctrine.
- Fable-on-Opus reasoning-discipline hook.

#### Fixed
- Perpetual git-dirty churn on every `agency upgrade`.
- False CLI relink spam on every `agency upgrade`.

#### Changed
- PD/Coord token-efficiency slimming (`N_global=5`).

## [2026-07-02] (`1bc1244`, `f837d84`)

### Tiếng Việt

#### Security
- Đã xóa các file PD cá nhân từng bị rò rỉ vào repo công khai.

#### Added
- `/save-state` chế độ INLINE và SUBAGENT.
- Chuyển `runbooks/` lên cấp cao nhất của repo.

### English

#### Security
- Removed personal PD files that had leaked into the public repo.

#### Added
- `/save-state` INLINE and SUBAGENT modes.
- Moved `runbooks/` to the repo top level.

## [2026-06-22] (`2ab2ca6`, `9ec9cad`)

### Tiếng Việt

#### Fixed
- `agency upgrade` giờ giữ nguyên tier setting của user và re-exec với code vừa pull về — một cơ chế tự cập nhật (self-updater) không độ trễ, ngăn việc chạy logic upgrade cũ trên state repo mới.

### English

#### Fixed
- `agency upgrade` now preserves the user's tier setting and re-execs with freshly-pulled code — a zero-lag self-updater that prevents running stale upgrade logic against new repo state.

## [2026-06-08 to 2026-06-18] (`597da37`, `632ae1a`, `1eb2345`, `f0aaac3`, `1873c01`, `187a6a3`, `1cff59f`, `0e146a7`, `4c2c5ba`, `3d9fc95`, `cba6781`, `058369b`, `a767808`, `f300f9e`)

### Tiếng Việt

#### Added
- Kiến trúc Director Upgrade.
- Các mandatory service agent.
- Họ agent `understand-*`.
- Hook fabrication-guard, autonomy tier gate, LS-PROOF gate.
- `bootstrap-machine.sh` (bootstrap máy portable 3 lớp) và lệnh CLI `agency initiate`.
- Thiết lập Graphify MCP.

#### Removed
- omnivoice-studio và các tool khác không portable khỏi bootstrap.

### English

#### Added
- Director Upgrade architecture.
- Mandatory service agents.
- `understand-*` agent family.
- Fabrication-guard hooks, autonomy tier gate, LS-PROOF gate.
- `bootstrap-machine.sh` (3-layer portable machine bootstrap) and the `agency initiate` CLI command.
- Graphify MCP setup.

#### Removed
- omnivoice-studio and other unportable tools from bootstrap.

## [2026-06-01 to 2026-06-05] (`0979b1c`, `5007c52`, `39db1aa`, `3ae4f3a`, `911d930`, `a3aa2e1`)

### Tiếng Việt

#### Added
- Phòng ban Critiques (13 agent).
- Phòng ban Video Studio (17 agent).
- Đóng gói dual tier lite/standard.

#### Fixed
- Re-link CLI symlink khi init/upgrade sau một bản clone cũ (stale).

#### Security
- Đã xóa các mục skill riêng tư từng bị rò rỉ vào INDEX công khai.

### English

#### Added
- Critiques department (13 agents).
- Video Studio department (17 agents).
- Dual lite/standard tier packaging.

#### Fixed
- CLI symlink re-linking on init/upgrade after a stale clone.

#### Security
- Removed private skill entries that had leaked into the public INDEX.

## [2026-05-21 to 2026-06-01] (`6f07124`, `dfb5fcc`, `03c554a`)

### Tiếng Việt

#### Added
- Bắt buộc áp dụng delegator-first.
- Hook spawn-gate.
- Protocol quality-loop cùng 8 skill mới.

#### Security
- Đã xóa `general-purpose` khỏi allowlist của spawn-gate.

### English

#### Added
- Delegator-first enforcement.
- Spawn-gate hook.
- Quality-loop protocol plus 8 new skills.

#### Security
- Removed `general-purpose` from the spawn-gate allowlist.

## [2026-05-13 to 2026-05-18] (`b471e31`, `0fc1a3e`, `e506a39`, `3ee3bbb`, `5d183cb`, `5135f5a`)

### Tiếng Việt

#### Added
- Wizard thiết lập tương tác `agency onboard`.
- Hệ thống Dept-Coord.
- Agent Delegator và Curator.
- Script khôi phục `rescue.sh`.
- Hệ thống hook lifecycle (10 script).
- Agent `codebase-search`.

#### Fixed
- Sửa clone target về đúng `~/.claude/` (trước đó có một thời gian ngắn là `~/the-agency/`).

### English

#### Added
- `agency onboard` interactive setup wizard.
- Dept-Coord system.
- Delegator and Curator agents.
- `rescue.sh` recovery script.
- Hook lifecycle system (10 scripts).
- `codebase-search` agent.

#### Fixed
- Clone target corrected to `~/.claude/` (was briefly `~/the-agency/`).

## [2026-05-08 to 2026-05-12] (`ae18064`, `e03a10b`, `9e8707b`, `d314243`)

### Tiếng Việt

#### Added
- Memory v2 — mô hình 4 loại kèm YAML frontmatter.
- Skill được tái cấu trúc theo layout thư mục kèm catalog INDEX.
- Installer giờ copy skill và agent cross-platform.

#### Fixed
- Sửa các đường dẫn hardcode trong protocol NEXUS thành dạng generic, đảm bảo portable.

### English

#### Added
- Memory v2 — 4-typed model with YAML frontmatter.
- Skills restructured to directory layout with an INDEX catalog.
- Installer now copies skills and agents cross-platform.

#### Fixed
- Genericized hardcoded paths in the NEXUS protocol for portability.

## [2026-04-16 to 2026-04-18] (`a396fe6`, `538049b`, `9607f2d`)

### Tiếng Việt

Bản phát hành công khai đầu tiên.

#### Added
- Hệ thống lõi v2.
- 32 skill.
- Protocol PD.
- Agency Rooms.
- Kiến trúc phân tầng PD → Coord → Task-Executor.
- QA gate với protocol ACK/NACK.

### English

Initial public release.

#### Added
- v2 core system.
- 32 skills.
- PD protocol.
- Agency Rooms.
- Tiered PD → Coord → Task-Executor architecture.
- QA gates with ACK/NACK protocol.
