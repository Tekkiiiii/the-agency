# Cover Letter Generator — Reference Notes

## Source
- Generated from the career-ops PDF generator's cover letter sub-mode
- Aligned with the 4-paragraph structure used in the career-ops pipeline
- Extends the `career-ops` skill (career-ops already had a Canva cover-letter workflow; this skill provides the markdown-first output path)

## References
- `career-ops/modes/pdf.md` — cover letter sub-mode in the PDF pipeline (Canva workflow)
- `career-ops/modes/_shared.md` — archetype system and scoring rules
- `career-ops/modes/oferta.md` — single evaluation A-F pipeline (proof paragraph logic)
- `career-ops/config/profile.yml` — candidate narrative template

## Design Decisions
1. **Markdown-first, not Canva-first**: career-ops pdf mode generates HTML for Canva or PDF. This skill outputs markdown for direct attachment/email/submission.
2. **4-paragraph prose structure**: No bullets in the final output — prose reads like a letter a peer wrote.
3. **Achievement scoring before drafting**: Scores cv.md bullets against JD keywords rather than picking by gut feel — more replicable, more honest.
4. **360° max word count**: Slightly more generous than the 250-word industry "standard" because ATS parsing handles markdown well.

## What This Adds to career-ops
| career-ops has | This skill adds |
|----------------|----------------|
| Canva visual cover letter workflow (pdf mode) | Markdown cover letter output |
| Cover letter inside the HTML cv-template | Standalone cover letter file |
| Implicit in oferta.md | Explicit /cover-letter invocation |
| Tied to PDF generation pipeline | Works independently with or without an evaluation |
