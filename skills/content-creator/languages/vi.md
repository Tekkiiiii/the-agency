# Vietnamese Language Pack — Tiếng Việt

Loaded only when `language=vi`. Factual reference only (register, diacritics, regulation, platform facts). Not a voice source.

---

## Tránh dùng (Vietnamese AI/translation tells)

"trong thời đại ngày nay", "trong cuộc sống bận rộn", "đừng ngần ngại", "đừng bỏ lỡ cơ hội này", "hãy cùng khám phá", "đỉnh cao của chất lượng", "giải pháp toàn diện", "đột phá", "tiên phong" — đều là dấu hiệu copy bị máy dịch

---

## Power Words, Hook Templates, CTA Library

Voice comes from exemplars (brand/voice-exemplars-vi, pending). Do not copy phrasing from this file.

---

## Tone Registers — Cách Xưng Hô

- **Formal / professional** — Anh / chị + tên hoặc danh xưng nghề nghiệp; "quý khách". Dùng với B2B, dịch vụ tài chính, bất động sản, y tế.
- **Casual / peer** — Bạn / mình. Dùng với nội dung giáo dục, lifestyle.
- **Bestie / intimate** — Mấy nàng / các chế / chị em / em. Dùng với beauty, fashion, mẹ và bé, lifestyle nữ trẻ.
- **Gen-Z internet** — Mọi người / hội mình / fen. Dùng với F&B trẻ, streetwear, công nghệ tiêu dùng.

**Quy tắc**: chọn 1 register và giữ đến cuối bài. Không trộn "anh/chị" với "mấy nàng" hay "bạn" trong cùng một bài.

---

## Diacritic & Unicode Rules

- **Dùng tiếng Việt có dấu đầy đủ.** Bỏ dấu (viết "khong" thay vì "không") đổi nghĩa và đọc như spam.
- **Composite vs precomposed Unicode**: Vietnamese has two valid Unicode forms (NFC vs NFD). Some platforms collapse incorrectly. If creating slugs, defer to general-purpose + `/vietnamese-language`, `/style-guide-vi` (role file: see `{agency-root}/agents-archive/ROLE-MAP.md`) for safe NFD → ASCII conversion (e.g. `thành công` → `thanh-cong`, never `thnh-cng`).
- Tránh trộn từ tiếng Anh không cần thiết: "skincare routine của bạn" thay vì "skincare regimen của bạn"; "review chi tiết" thay vì "in-depth review".
- Loanword đã hòa nhập: "review", "skincare", "deal", "sale", "outfit", "vibe", "trend".
- Loanword chưa hòa nhập ("leverage", "synergy", "best practice") nên dịch hoặc bỏ.

---

## Platform-Local Conventions (Vietnam)

Voice comes from exemplars (brand/voice-exemplars-vi, pending). Do not copy phrasing from this file.

Platform facts only:
- TikTok VN, Facebook VN, Instagram VN, Threads VN: dùng cho kênh phổ biến tại Việt Nam. Format specs (giới hạn ký tự, tỉ lệ khung hình) xem `content-creator/references/platforms.md`.
- Zalo, LinkedIn VN, YouTube VN, Twitter/X VN: xem `vietnamese-language/references/platforms/`.

---

## Common Pitfalls — Lỗi Thường Gặp

- **Dấu câu Tây hóa**: tránh dùng "—" (em-dash) trong tiếng Việt. Dùng dấu phẩy hoặc dấu hai chấm.
- **Hoa mọi từ**: "Sản Phẩm Tốt Nhất" không phải convention tiếng Việt. Chỉ viết hoa chữ cái đầu câu và tên riêng.
- **Xưng hô không nhất quán**: bắt đầu bằng "anh/chị" rồi giữa bài chuyển sang "bạn" là lỗi.
- **Y tế / mỹ phẩm không được khẳng định**: "chữa khỏi", "miễn nhiễm", "100% hết mụn" — vi phạm quy định Bộ Y Tế / Cục An Toàn Thực Phẩm. Dùng "hỗ trợ", "cải thiện", "giúp giảm".

---

## Cultural Notes

- Dịp lễ chính: Tết, 8/3, 20/10, 20/11, Tết Trung Thu.
- Khu vực: miền Bắc / miền Trung / miền Nam có cách diễn đạt và từ địa phương khác nhau. Default tone trung tính nếu audience toàn quốc.
- Voice comes from exemplars (brand/voice-exemplars-vi, pending). Do not copy phrasing from this file.
