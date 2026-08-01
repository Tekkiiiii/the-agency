# Changelog

Mọi thay đổi đáng chú ý của The Agency được ghi lại tại đây, nhóm theo từng đợt phát hành (đánh số theo ngày — repo này không có file version riêng, nên ngày tháng là nguồn duy nhất và không bao giờ lệch khỏi lịch sử git).

All notable changes to The Agency are documented here, grouped by release wave (date-based — this repo has no separate version file, so dates are the single source of truth and can never desync from git history).

## [Unreleased]

### Tiếng Việt

#### Added
- **Checkpoint Handshake Protocol** (`runbooks/checkpoint-handshake-protocol.md`) — cổng APPROACH và CHECKPOINT của Exec/Member giờ chạy qua một file scratch-board với cơ chế poll có giới hạn (~5 phút), thay cho pattern gửi SendMessage lên trên rồi chờ. Roster là phẳng nên SendMessage định danh theo tên đi lên KHÔNG resolve được — Exec nào chờ theo cách cũ sẽ deadlock vĩnh viễn. Khi hết thời gian chờ, Exec vẫn tiếp tục nhưng phải đánh dấu `APPROACH_UNREVIEWED` / `CHECKPOINT_UNREVIEWED` trong báo cáo, và Coord phải soi kỹ hơn ở QA gate thay vì ACK nhanh. Áp dụng cho coord, mini-coord, task-executor, 7 dept-coord và dept-coord-protocol.
- Agent critic mới `critique-social` — chấm chất lượng ảnh/carousel mạng xã hội (mật độ chữ, safe zone, sàn cỡ chữ, tính liên tục khi vuốt), bắt buộc chụp màn hình từng frame ở đúng kích thước pixel gốc của nền tảng.
- `scripts/mem-d8-sample.py` — bộ lấy mẫu độ trễ từ lúc user chỉnh sai đến lúc có lesson/feedback delta; `scripts/mem-scorecard.py` giờ chấm mục D8 dựa trên kết quả này (nhãn PROXY, không phải phát hiện ngữ nghĩa).
- `agency upgrade` giờ in ra các mục CHANGELOG.md tương ứng với những gì vừa được pull về sau một lần upgrade thành công — cơ chế best-effort dựa trên date-header (không mapping theo commit-hash, không thêm dependency mới), giới hạn khoảng 40 dòng kèm link trỏ tới CHANGELOG.md cho phần còn lại. Im lặng khi đã ở phiên bản mới nhất.
- **CI cho installer** (`.github/workflows/installers.yml`) — chạy `install.sh` trên `ubuntu-latest` và `install.ps1` trên `windows-latest` ở mỗi lần push/PR vào main. Mỗi job kiểm tra: cài đủ số skill có trong repo, mọi tham chiếu `{agency-root}/…` do cây đã deploy phát ra đều resolve được, `hooks/emit-metric.sh` ghi ra một dòng event thật, và một lần cài **thứ hai** vào `AGENCY_HOME` khác phải resolve đúng vào đó mà không rò rỉ sang `$HOME/.claude`. Trước đây `install.ps1` chưa từng được chạy thật lần nào — nó chỉ được viết cho khớp với `install.sh` rồi đọc lại bằng mắt. Không cần secret nào.
- `hooks/lib/resolve-root.sh` — nguồn duy nhất trả lời "agency root nằm ở đâu". Export `AGENCY_ROOT`, thứ tự ưu tiên `$AGENCY_HOME` → `$CLAUDE_CONFIG_DIR` → `~/.claude`. Kèm theo hai script guard chạy trong CI: `.github/scripts/verify-agency-refs.sh` (+ bản `.ps1` cho Windows) và `.github/scripts/check-hardcoded-root.sh`.
- **`design-system/` — cây thứ bảy được deploy, giữ vai trò SSOT cho brand token.** JSON là nguồn, CSS là output sinh ra; `build.js` validate schema 15 role + 4 tín hiệu semantic rồi sinh `brands/*.css`, đồng thời chặn mọi hex literal trong `overlays/*.css` (kể cả `rgb()` thập phân mang màu — lỗ hổng này từng để lọt ba bug drift màu thật). Repo chỉ ship brand `neutral`: file brand là tài sản của chủ sở hữu hoặc của khách hàng, không phải nội dung framework — README hướng dẫn cách tự thêm brand riêng. Kèm 4 overlay (layout/mật độ/type scale/motion, tuyệt đối không có màu) và `verify-semantic-consumers.js`, script render CSS của **bên tiêu thụ** trong trình duyệt thật để chứng minh 4 tín hiệu semantic không trùng nhau sau khi resolve — điều mà lint ở tầng nguồn không bao giờ thấy được.
- **Skill `deck-narrative`** — tầng kiến trúc nằm *dưới* mọi skill làm deck: quyết định cái gì lên slide và theo thứ tự nào, trước khi bất kỳ skill visual nào quyết định nó trông ra sao. Bao gồm action title vs topic title (phép thử động từ), một slide một thông điệp, trình tự top-down kiểu Minto (kết luận ở slide 2, không bao giờ để bất ngờ ở cuối), nhịp theo độ dài buổi họp, logic ngang (chỉ đọc riêng các title cũng phải thành một bài luận thuyết phục) và logic dọc (thân slide chứng minh title), chọn bảng hay biểu đồ, và ba khung dựng slide quyết định/phê duyệt. Mọi quy tắc viết dưới dạng kiểm tra pass/fail có thể audit được, không phải ý kiến thẩm mỹ. Kèm `scripts/audit_deck.py` — trình audit `.pptx` chạy được thật: cỡ chữ từng slide, số từ/số dòng của title, heuristic phép thử động từ, đếm bảng vs biểu đồ, ứng viên cần rà lại vì chứa nội dung chỉ dành cho người làm chứ không phải người xem, kiểm kê font toàn deck kèm cờ fail cứng khi phát hiện font hệ thống (Calibri/Arial...), và bản dump chuỗi title để đọc xuyên suốt. Co-load cùng skill visual (`skill-tekki-strategic-deck`, `marp`, ...) — skill này im lặng hoàn toàn về màu sắc, font thẩm mỹ và layout.
- Overlay **không** trung lập với brand, và điều này giờ được ghi rõ. `contrast-dark.css` tô canvas bằng `var(--brand-primary)`, nên nó chỉ "tối" với brand có primary tối. Đo thật trên một brand có primary xanh trung tính: **8/15 cặp chữ/nền trượt WCAG AA**, tệ nhất là accent-trên-card ở **1.30:1**. Mỗi overlay giờ ghi rõ điều kiện tiên quyết về brand của nó.

#### Fixed
- **Tám hook nữa âm thầm không ghi gì trên Windows — cùng lớp lỗi mà `emit-metric.sh` đã mắc.** Hook là script bash, nhưng trên Windows chúng chạy dưới Git Bash trong khi `python3` lại là bản **Python native của Windows**, không mở được đường dẫn kiểu MSYS (`/d/a/_temp/...`). Mọi hook đưa một đường dẫn tuyệt đối qua ranh giới bash → `python3 -c` đều hỏng — và hỏng trong im lặng, vì các hook này đều fire-and-forget (`set +e`, nuốt stderr, luôn exit 0). Đã sửa `loop-detector.sh`, `check-session-state.sh`, `session-end.sh`, `cost-tracker.sh`, `spawn-completion.sh` (hook này truyền đường dẫn qua **argv** — argv cũng vượt ranh giới y hệt), cộng thêm 3 file nằm ngoài danh sách ban đầu, tìm ra khi rà blast radius: `check-settings-secrets.sh`, `bg-job-warn.sh`, và `scripts/canary-session-check.sh` — file cuối này còn có sẵn một comment khẳng định nó an toàn vì đường dẫn đi qua biến môi trường chứ không phải string interpolation; biến môi trường mang đúng chuỗi MSYS đó và hỏng y hệt, nên comment sai lệch ấy đã được sửa luôn trong code. Tất cả dùng **đúng một idiom** của Wave 13: cd vào thư mục đích rồi đưa python một tên file trần, không có đường dẫn tuyệt đối nào vượt ranh giới trên bất kỳ nền tảng nào. Ba hook bị Wave 13 nghi oan (`write-evidence.sh`, `artifact-verify.sh`, `spawn-logger.sh`) đã được kiểm tra lại và **không dính lỗi** — chúng resolve root ngay bên trong python, không có gì được nội suy từ bash. CI Windows có thêm 2 bước assert cho `check-session-state.sh`/`session-end.sh` và `bg-job-warn.sh`.
- **Một bản cài, hai cái root.** Các installer tôn trọng `AGENCY_HOME`, nhưng **35 file** trong `hooks/` và `scripts/` thì hardcode `$HOME/.claude`. Hệ quả: cài với root tuỳ chỉnh thì ghi vào một thư mục nhưng đọc từ thư mục khác — hook append nhầm log, `startup-sync.sh` git-sync nhầm repo, `skill-audit.py` báo mọi tham chiếu của skill đã deploy là chết. Không có gì báo lỗi, vì hook ghi nhầm file vẫn exit 0. Toàn bộ 35 file đã được rà từng file (không sed mù) để đi qua resolver dùng chung; các script Python dùng bản twin nội tuyến đã được ghi rõ trong tài liệu. Xác minh bằng hai lần cài sandbox — mặc định và `AGENCY_HOME` tuỳ chỉnh — cộng thêm phép thử "không rò rỉ" mà trước đây không hề tồn tại.
- `install.sh` sinh ra `settings.json` với đường dẫn hook `~/.claude/hooks/...` cứng. Với `AGENCY_HOME` tuỳ chỉnh, đó là hai thư mục khác nhau, nên `settings.json` trỏ vào chỗ không có gì và toàn bộ hook im lặng không chạy. Giờ ghi đúng đường dẫn đã resolve.
- `install.ps1` và `cli/bin/agency.js` chưa xét `$CLAUDE_CONFIG_DIR`. Nếu user đã dời config dir của Claude Code, đó mới là nơi Claude Code đọc skill/agent/hook — cài vào `~/.claude` là cài vào thư mục không ai đọc. Cả ba installer giờ dùng chung đúng một thứ tự ưu tiên với `hooks/lib/resolve-root.sh`.
- `skills/html-plan-style/SKILL.md` bị sanitize sót từ lần đầu vào repo: frontmatter vẫn nói skill này dành cho tài liệu "intended for Tekki review", ghi nguồn palette là "the WebMoi/website-pitch home page", dặn người đọc "no visit to website-pitch needed", và so sánh với `tekki-standalone-deck` — một skill repo này không hề ship. Đã sửa cả bốn. Nhân tiện bổ sung phần **Page Skeleton (BẮT BUỘC)**: `.plan-container` và `.plan-section` mới là thứ mang max-width, canh giữa và nhịp dọc; `<main>`/`<section>` trần không kế thừa gì cả, nên trang render tràn viền không lề trái — mà header vẫn đúng (nó do `.plan-header` style), khiến bug này rất dễ lọt qua một lần nhìn nhanh. Kèm 2 lệnh grep để tự kiểm tra sau khi sinh file.
- **Lỗi portability trong 6 file được ship**: `mem-scorecard.py`, `mem-graph-build.py`, `mem-d8-sample.py`, `mem-find.sh`, `mem-gardener.sh` và `skills/lint-memory/SKILL.md` hardcode slug thư mục project của một máy cụ thể (`-Users-Tekki--claude`) và đường dẫn tuyệt đối tới venv graphifyy. Với mọi user khác, các script này trỏ vào thư mục không tồn tại và âm thầm không làm gì. Slug giờ được suy ra từ chính agency root (Claude Code mã hoá cwd bằng cách thay `/` và `.` thành `-`), còn đường dẫn venv dùng `$HOME`/`Path.home()`.
- `runbooks/dept-coord-protocol.md` là bản trùng lặp đã cũ (2026-05-13), thiếu toàn bộ v2.0.0 back-port (TIER_A/B, cổng 50% check-in, DIRECTION framing) vốn đã có trong `core/runbooks/dept-coord-protocol.md`. Bản mirror này dạy pattern cũ đã lỗi thời cho bất kỳ ai đọc nó. Đã đồng bộ lại cả hai bản.
- `scripts/` (save-state.py, mem-gardener.sh, setup-graphify.sh, v.v.) giờ được `agency init` và `agency upgrade` deploy vào `{agency root}/scripts/` — trước đây thư mục này chưa từng được sync, nên bất kỳ skill nào tham chiếu `~/.claude/scripts/...` (ví dụ `/save-state`) sẽ báo lỗi "file not found" trên một bản cài mới.
- Đã xóa các ví dụ đường dẫn tuyệt đối cá nhân (`/Users/Tekki/...`) hardcode trong 5 file agent/skill vốn được thiết kế để chạy chung cho mọi user — trong đó 2 trường hợp là bug chức năng thật sự (hướng dẫn agent ghi y nguyên chuỗi `/Users/Tekki` vào file của một user khác).
- **`install.sh` và `install.ps1` cài đúng 0 skill.** Cả hai vẫn glob theo layout phẳng `skills/*.md` mà repo đã bỏ từ lâu (layout canonical là `skills/<name>/SKILL.md`, đã có CI chặn qua `scripts/check-flat-skills.js`), nhưng vẫn in ra dòng `✓ 0 skills installed` như thể thành công. Giờ cả hai duyệt theo *thư mục* skill, copy luôn các asset đi kèm (style.css, branches/, scripts/), và cảnh báo lớn khi số skill trong repo lệch với số đã cài — đúng cơ chế guard mà đường CLI đã có sẵn. Xác minh: 287/287 skill trên cả hai đường cài.
- Thêm `design-system/` vào cả 4 installer trong cùng một commit, đúng theo quy tắc của `docs/INSTALL-LAYOUT.md` — bỏ sót một đường cài nào cũng khiến mọi tham chiếu `{agency-root}/design-system/...` treo lơ lửng trên đường đó. Đây là cây có kiểu hỏng **im lặng nhất** trong danh sách deploy: thiếu `hooks/` thì hook không chạy; thiếu `design-system/` thì skill design lặng lẽ quay về dùng hex nó hardcode lần cuối và xuất ra một deliverable trông vẫn hợp lý nhưng sai brand — không có gì báo lỗi. CI Linux giờ assert rằng bản đã deploy sinh lại CSS **giống hệt từng byte** từ JSON của chính nó (bắt được cả bản copy bị cụt lẫn file `.css` bị sửa tay), còn CI Windows assert rằng file brand SSOT thực sự có mặt dưới custom root.
- **`runbooks/` chưa từng được installer nào deploy.** Mọi tham chiếu `{agency-root}/runbooks/...` trong các agent def được ship đều 404 trên mọi bản cài. Đã thêm `runbooks/` vào cả 4 installer. Tương tự, `hooks/` trước đây chỉ có ở `install.sh` và `scripts/` chỉ có ở đường CLI — giờ cả ba tree đều được deploy đồng nhất trên `install.sh`, `install.ps1`, `agency init` và `agency upgrade`. Ma trận deploy được ghi lại tại `docs/INSTALL-LAYOUT.md`.
- `hooks/lib/` (trong đó có `resolve-project.sh`, được `spawn-completion.sh` `source`) không được `install.sh` copy vì vòng lặp chỉ quét `hooks/*.sh` ở cấp cao nhất. Đã sửa.
- **Đường dẫn script emit-metric đã sai ở 92 chỗ.** Các agent def, runbook, script và hook được ship đều trỏ tới `~/.claude/memory/metrics/emit-metric.sh` — nơi script này không hề tồn tại (nó nằm ở `hooks/emit-metric.sh`). Toàn bộ 92 tham chiếu đã được rà từng file rồi chuyển sang `{agency-root}/hooks/emit-metric.sh` (trong code thực thi thì dùng đúng dạng đường dẫn tương ứng). Đường dẫn *log* (`memory/metrics/events.jsonl`) là thứ khác và được giữ nguyên có chủ đích.

#### Changed
- **1M context (`[1m]`) áp dụng CHỌN LỌC, không áp dụng toàn fleet.** Hậu tố `[1m]` chỉ gắn cho các role điều phối — PD, Coord, Mini-Coord, Dept-Coord (21 file) — vì đây là những role duy nhất có context phình theo *khối lượng công việc* chứ không theo độ dài brief của chính nó. Toàn bộ agent còn lại giữ nguyên. Quyết định này đã chốt, không mở lại. Chính sách đầy đủ ở `core/ORG.md` § Model tiering. Kèm theo đó: `modelTier:` chỉ là tag tài liệu và hoàn toàn trơ khi spawn — `model:` mới là key Claude Code thực sự đọc, và là nơi `[1m]` được gắn vào.

### English

#### Added
- **Checkpoint Handshake Protocol** (`runbooks/checkpoint-handshake-protocol.md`) — the Exec/Member APPROACH and CHECKPOINT gates now run over a scratch-board file with a bounded (~5 min) poll, replacing the old upward-SendMessage-and-wait pattern. The roster is flat, so upward name-addressed SendMessage does not resolve — an Exec waiting on it deadlocks forever. On timeout the Exec proceeds but must mark `APPROACH_UNREVIEWED` / `CHECKPOINT_UNREVIEWED` in its report, and the Coord holds it to a stricter QA threshold instead of fast-ACKing. Applied across coord, mini-coord, task-executor, all 7 dept-coords, and dept-coord-protocol.
- New `critique-social` critic — scores social graphics and carousels (text coverage, safe zones, font floor, swipe continuity), requiring per-frame screenshots at native platform pixel dimensions.
- `scripts/mem-d8-sample.py` — correction→lesson/feedback-delta latency sampler; `scripts/mem-scorecard.py` now scores D8 from its output (labelled PROXY, not semantic detection).
- `agency upgrade` now prints the CHANGELOG.md entries covering what was just pulled after a successful upgrade — best-effort, date-header based (no commit-hash mapping, no new deps), capped at ~40 lines with a pointer to CHANGELOG.md for the rest. Silent when already up to date.
- **Installer CI** (`.github/workflows/installers.yml`) — runs `install.sh` on `ubuntu-latest` and `install.ps1` on `windows-latest` on every push and PR to main. Each job asserts: the full repo skill count is installed, every `{agency-root}/…` reference emitted by the deployed tree resolves to a real file, `hooks/emit-metric.sh` writes an actual event line, and a **second** install into a different `AGENCY_HOME` resolves there without leaking into `$HOME/.claude`. `install.ps1` had never been executed even once before this — it was written to mirror `install.sh` and reviewed by reading. No secrets required.
- `hooks/lib/resolve-root.sh` — the single source of truth for "where is the agency root?". Exports `AGENCY_ROOT`, resolved `$AGENCY_HOME` → `$CLAUDE_CONFIG_DIR` → `~/.claude`. Shipped with two CI guards: `.github/scripts/verify-agency-refs.sh` (plus a `.ps1` Windows twin) and `.github/scripts/check-hardcoded-root.sh`.
- **`design-system/` — a seventh deployed tree, holding the brand-token SSOT.** JSON is the source, CSS is generated: `build.js` validates the 15-role schema plus the 4 semantic signals, generates `brands/*.css`, and rejects any hex literal in `overlays/*.css` — including *chromatic* decimal `rgb()` values, a blind spot that had already shipped three real color-drift bugs. Only the `neutral` brand ships: a brand file is the owner's or the client's IP, not framework content, and the README documents how to add your own in its place. Ships with 4 overlays (layout/density/type-scale/motion, zero color of their own) and `verify-semantic-consumers.js`, which renders the **consumer's** CSS in a real browser to prove the four semantic signals stay distinct after resolution — something a source-level lint structurally cannot see, since it never looks at consumers at all.
- **`deck-narrative` skill** — the architecture layer *beneath* every deck skill: it decides what goes on the slides and in what order, before any visual skill decides what it looks like. Covers action titles vs topic titles (the verb test), one message per slide, Minto top-down sequencing (conclusion on slide 2, never a surprise ending), pacing by meeting length, horizontal logic (the titles alone must read as a persuasive essay) and vertical logic (the body proves the title), table-vs-chart selection, and three decision/approval-slide frameworks. Every rule is written as an auditable pass/fail check, not a style opinion. Ships `scripts/audit_deck.py`, a runnable `.pptx` auditor: per-slide font size, title word/line counts, a verb-test heuristic, table vs chart counts, review candidates that contain producer-facing rather than reader-facing content, a deck-wide font inventory with a hard fail flag on system fonts (Calibri/Arial/…), and a title-sequence dump for a read-through. Co-load it with whichever visual skill you are using (`skill-tekki-strategic-deck`, `marp`, …) — it is deliberately silent on color, aesthetic font choice and layout.
- Overlays are **not** brand-agnostic, and this is now written down. `contrast-dark.css` paints the canvas with `var(--brand-primary)`, so it is only "dark" for brands whose primary is dark. Measured against a brand with a mid-tone blue primary: **8 of 15 text/background pairs fail WCAG AA**, the worst being accent-on-card at **1.30:1**. Every overlay now states its brand precondition instead of leaving it to be discovered.

#### Fixed
- **Eight more hooks silently wrote nothing on Windows — the same defect class as `emit-metric.sh`.** The hooks are bash scripts, but on Windows they run under Git Bash while `python3` is normally **native Windows Python**, which cannot open an MSYS-style path (`/d/a/_temp/...`). Any hook handing an absolute path across the bash → `python3 -c` boundary fails there — silently, because these hooks are fire-and-forget (`set +e`, stderr muted, always exit 0). Fixed in `loop-detector.sh`, `check-session-state.sh`, `session-end.sh`, `cost-tracker.sh` and `spawn-completion.sh` (which passed the path via **argv** — argv crosses the boundary just the same), plus three files outside the original list found by walking the blast radius: `check-settings-secrets.sh`, `bg-job-warn.sh`, and `scripts/canary-session-check.sh` — the last of which carried a comment asserting it was safe *because* the path travelled in an environment variable rather than string interpolation. An environment variable carries the identical MSYS string and is equally unopenable; that actively misleading comment is now corrected in code. All use **one idiom**, Wave 13's: cd into the target directory and hand python a bare filename, so no absolute path crosses the boundary on any platform. The three hooks Wave 13 had flagged as suspects (`write-evidence.sh`, `artifact-verify.sh`, `spawn-logger.sh`) were re-checked and are **not affected** — they resolve the root inside python, with nothing interpolated from bash. Two assertion steps added to the existing Windows CI job for `check-session-state.sh`/`session-end.sh` and `bg-job-warn.sh`.
- **One install, two roots.** The installers honoured `AGENCY_HOME`; **35 files** under `hooks/` and `scripts/` hardcoded `$HOME/.claude` instead. A custom-root install therefore wrote to one directory and was read from another — hooks appended to the wrong log, `startup-sync.sh` git-synced the wrong repo, and `skill-audit.py` reported every deployed skill's references as dead. Nothing failed loudly, because a hook writing to the wrong file still exits 0. All 35 were migrated in an audited per-file pass (no blind sed) onto the shared resolver, with Python scripts using the documented inline twin. Verified with two sandboxed installs — default and a custom `AGENCY_HOME` — plus the no-leak assertion that did not exist before.
- `install.sh` generated a `settings.json` with hardcoded `~/.claude/hooks/...` hook commands. Under a custom `AGENCY_HOME` those are different directories, so `settings.json` pointed at nothing and every hook silently never ran. It now writes the resolved path.
- `install.ps1` and `cli/bin/agency.js` ignored `$CLAUDE_CONFIG_DIR`. If a user has relocated Claude Code's config dir, that is the only directory Claude Code reads skills, agents and hooks from — installing to `~/.claude` installs somewhere nothing reads. All three installers now share exactly the precedence in `hooks/lib/resolve-root.sh`.
- `skills/html-plan-style/SKILL.md` had been sanitized incompletely when it first landed here: the frontmatter still described the skill as being for documents "intended for Tekki review", credited the palette to "the WebMoi/website-pitch home page", told readers "no visit to website-pitch needed", and compared itself to `tekki-standalone-deck` — a skill this repo does not ship. All four fixed. While in the file, added the **Page Skeleton (REQUIRED)** section: `.plan-container` and `.plan-section` are what carry the max-width, centering and vertical rhythm; a bare `<main>` / `<section>` inherits none of it, so the page renders full-bleed with no left padding — while the header still looks correct, because it is styled by `.plan-header`. That is exactly what makes the bug easy to miss on a glance. Two grep commands are included to verify generated output.
- **Portability bug across 6 shipped files**: `mem-scorecard.py`, `mem-graph-build.py`, `mem-d8-sample.py`, `mem-find.sh`, `mem-gardener.sh` and `skills/lint-memory/SKILL.md` hardcoded one machine's project-dir slug (`-Users-Tekki--claude`) and an absolute graphifyy venv path. For every other user these pointed at directories that do not exist and silently did nothing. The slug is now derived from the agency root itself (Claude Code encodes cwd by replacing `/` and `.` with `-`), and venv paths use `$HOME`/`Path.home()`.
- `runbooks/dept-coord-protocol.md` was a stale duplicate (2026-05-13) missing the entire v2.0.0 back-port (TIER_A/B, 50% check-in gate, DIRECTION framing) that `core/runbooks/dept-coord-protocol.md` already had. The mirror copy was teaching the superseded pattern to anyone reading it. Both copies are now in sync.
- `scripts/` (save-state.py, mem-gardener.sh, setup-graphify.sh, etc.) is now deployed to `{agency root}/scripts/` by `agency init` and `agency upgrade` — previously it was never synced, so any skill referencing `~/.claude/scripts/...` (e.g. `/save-state`) would fail on a clean install with a "file not found" error.
- Removed hardcoded personal absolute-path examples (`/Users/Tekki/...`) from 5 shipped agent/skill files that are meant to run generically for any user — two of these were functional bugs (instructions that told the agent to literally write the string `/Users/Tekki` into another user's own files).
- **`install.sh` and `install.ps1` installed exactly 0 skills.** Both still globbed the flat `skills/*.md` layout the repo abandoned long ago (canonical is `skills/<name>/SKILL.md`, CI-enforced by `scripts/check-flat-skills.js`), while printing `✓ 0 skills installed` as if it had worked. Both now iterate skill *directories*, copy sibling assets (style.css, branches/, scripts/), and warn loudly on a repo-vs-installed count mismatch — the same guard the CLI path already had. Verified: 287/287 skills on both install paths.
- `design-system/` was added to all four installers in the same commit, as `docs/INSTALL-LAYOUT.md` requires — missing one install path would leave every `{agency-root}/design-system/...` reference dangling on that path. It is the **quietest** failure on the deploy list: a missing `hooks/` tree makes a hook not run, while a missing `design-system/` tree makes a design skill fall back to whatever hex it last hardcoded and ship a plausible-looking, off-brand deliverable with nothing erroring. Linux CI now asserts the deployed copy regenerates its CSS **byte-for-byte** from its own JSON (which catches both a truncated copy and a hand-edited `.css`), and Windows CI asserts the brand SSOT is actually present under the custom root.
- **`runbooks/` was deployed by no installer at all.** Every `{agency-root}/runbooks/...` reference in shipped agent defs 404'd on every install. `runbooks/` is now in all four installers. Likewise `hooks/` shipped only via `install.sh` and `scripts/` only via the CLI path — all three trees now deploy uniformly across `install.sh`, `install.ps1`, `agency init` and `agency upgrade`. The deploy matrix is written down in `docs/INSTALL-LAYOUT.md`.
- `hooks/lib/` (including `resolve-project.sh`, which `spawn-completion.sh` `source`s) was never copied by `install.sh`, whose loop only globbed top-level `hooks/*.sh`. Fixed.
- **The emit-metric script path was wrong in 92 places.** Shipped agent defs, runbooks, scripts and hooks all pointed at `~/.claude/memory/metrics/emit-metric.sh`, where the script does not exist — it lives at `hooks/emit-metric.sh`. All 92 references were audited per file and migrated to `{agency-root}/hooks/emit-metric.sh` (using the appropriate path form in executable code). The *log* path (`memory/metrics/events.jsonl`) is a different thing and was deliberately left untouched.

#### Changed
- **1M context (`[1m]`) is SELECTIVE, not fleet-wide.** The `[1m]` suffix is applied only to orchestrator roles — PD, Coord, Mini-Coord, Dept-Coord (21 files) — because they are the only roles whose context grows with the *size of the work* rather than the size of their own brief. Every other agent stays plain. This decision is closed and should not be re-opened as a fleet-wide proposal. Full policy in `core/ORG.md` § Model tiering. Recorded alongside it: `modelTier:` is a documentation tag and is inert at spawn time — `model:` is the key Claude Code actually reads, and the one `[1m]` attaches to.

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
