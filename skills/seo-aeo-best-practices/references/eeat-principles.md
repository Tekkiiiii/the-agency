# E-E-A-T Principles

Experience, Expertise, Authoritativeness, and Trustworthiness — Google's framework for evaluating content quality. Not a direct ranking algorithm input but informs the training of ranking signals. The same signals that build Google trust also build AI citation trust.

---

## What E-E-A-T Is (and Is Not)

**Is:** A framework used by human Quality Raters (Google's Search Quality Evaluator Guidelines). Their ratings train the ranking systems over time.

**Is not:** A direct ranking score, a checkbox, or something you can "hack." There is no E-E-A-T score in Google's algorithm.

**How it works in practice:** Google's systems have learned to recognize patterns that correlate with high-quality, trustworthy content — the same patterns that human raters identify using E-E-A-T criteria. Implementing E-E-A-T signals makes your content match what these systems have been trained to reward.

---

## Experience (the added "E" — 2022)

First-hand, real-world experience with the topic. Demonstrates you've actually done the thing you're writing about, not just researched it.

### Signals that demonstrate experience:
- Personal photos (not stock) showing direct involvement
- Specific product versions, tools, and dates tested ("I used Notion v2.34 for 6 months starting March 2025")
- Before/after metrics from your own implementation
- Mistakes made and lessons learned (impossible to fake authentically)
- Screenshots of your own dashboards, interfaces, results
- Time-stamped documentation of process ("Day 1... Day 30...")
- Specific client/project details (anonymized if needed)

### Implementation:
- Add "I tested this for X days/months" language where true
- Include original screenshots and photos
- Share specific quantitative outcomes from personal experience
- Write case studies from actual work (not hypothetical scenarios)
- Date your experience explicitly ("As of May 2026, this approach still works")

---

## Expertise

Credentials and demonstrated knowledge appropriate to the topic. The bar scales with topic risk.

### YMYL topics (health, finance, legal, safety):
- Formal credentials required (MD, CPA, JD, CFA, etc.)
- Professional licenses and certifications
- Institutional affiliation (hospital, law firm, university)
- Published research in peer-reviewed venues
- Board certifications, specializations

### Non-YMYL topics (how-to, lifestyle, opinion, tech):
- Depth of coverage demonstrates expertise without formal credentials
- Track record: number of years working in the field
- Published work: articles, talks, open-source contributions
- Demonstrated competence through specificity and accuracy
- Community recognition: followers, citations by peers

### Implementation:
- **Author bio on every content page** — linked to full author page
- **Author page** with: photo, credentials, experience summary, published works, social links
- **Person schema** on author page (see `structured-data.md`)
- **Consistent authorship** — same author across related topics builds topical expertise signal
- **Byline format:** "By [Name], [Title/Credential] at [Organization] | [X years experience in Y]"

---

## Authoritativeness

External recognition by others in the field. You can build expertise alone, but authority requires others to vouch for you.

### Signals:
- Backlinks from authoritative domains in your niche
- Mentions in press (linked or unlinked — both count)
- Wikipedia entry (for entities meeting notability criteria)
- Citations in academic papers, industry reports
- Speaking invitations at recognized conferences
- Awards and rankings from credible organizations
- Guest authorship in respected publications
- Social proof: follower counts, engagement from recognized peers

### Implementation (what you can control):
- Digital PR strategy: target industry publications for coverage
- Expert commentary: HARO/Connectively/Quoted responses
- Conference speaking: submit CFPs, present original research
- Guest posts: contribute to authoritative publications in your niche
- Brand mention monitoring: track where you're mentioned, convert unlinked mentions to links
- Wikipedia: if notable, ensure entry exists and is accurate (don't edit your own — conflict of interest)

### What you cannot fake:
Authority is the hardest E-E-A-T component to build because it requires third-party validation. This is also what makes it the strongest signal — it cannot be gamed through on-site changes alone.

---

## Trust

Accuracy, transparency, and safety. The foundation that the other three components rest on.

### Site-level trust signals:
- **HTTPS** — non-negotiable baseline
- **Clear ownership** — About page with real people, company info, contact details
- **Physical address** — especially for local businesses (Google Business Profile)
- **Contact information** — reachable email, phone number where applicable
- **Privacy policy** — clear, current, GDPR/CCPA compliant
- **Editorial policy** — how content is reviewed, fact-checked, updated
- **Corrections policy** — how errors are handled when discovered
- **Terms of service** — for products/services

### Content-level trust signals:
- **Dates visible** — publication date and last-updated date on every piece
- **Sources cited** — inline citations or references section for factual claims
- **No misleading claims** — content matches what the page title/meta description promises
- **Disclosures** — affiliate relationships, sponsored content, paid partnerships
- **Corrections inline** — strikethrough old info with updated info when corrections needed
- **Review methodology** — how you tested/evaluated (for review content)

### Implementation checklist:
1. [ ] About page exists with real people and credentials
2. [ ] Contact page with working email/phone
3. [ ] Privacy policy linked in footer
4. [ ] HTTPS active across entire site
5. [ ] Publication dates visible on all content
6. [ ] Last-updated dates on evergreen content
7. [ ] Sources cited for all factual claims
8. [ ] Affiliate/sponsor disclosures present where applicable
9. [ ] Editorial policy page (for publishers)
10. [ ] Google Business Profile claimed (for local businesses)

---

## YMYL Topics (Your Money Your Life)

Topics where content quality directly impacts reader health, financial stability, safety, or well-being. Google applies a higher E-E-A-T bar to YMYL content.

### YMYL categories:
- **Health:** medical conditions, symptoms, treatments, medications, mental health
- **Finance:** investing, taxes, retirement, loans, insurance, cryptocurrency
- **Legal:** legal rights, divorce, custody, immigration, criminal law
- **Safety:** product safety, emergency information, dangerous activities
- **News:** current events that affect public welfare
- **Civic:** voting, government services, social services

### Detection signals in content:
- Keywords: "treatment," "invest," "legal rights," "symptoms," "medication"
- Claims about health outcomes, financial returns, legal consequences
- Advice that, if wrong, could cause harm

### YMYL E-E-A-T requirements:
- Author MUST have formal credentials for the topic
- Content MUST be reviewed by a qualified professional
- Sources MUST be authoritative (peer-reviewed, government, professional organizations)
- Disclaimers required ("This is not medical/financial/legal advice")
- Regular review dates (medical content should be reviewed annually minimum)

**Failure mode:** YMYL content from unqualified authors is a strong demotion signal — not just neutral, actively penalized.

---

## E-E-A-T for GEO (AI Citation Authority)

The same signals that build Google trust build AI citation trust. AI systems must believe a source is authoritative before citing it.

### How E-E-A-T maps to AI citation:

| E-E-A-T signal | GEO impact |
|----------------|------------|
| Author with verifiable credentials | AI more likely to cite as expert source |
| Organization with Wikipedia/Wikidata entry | Entity recognized in training data |
| `sameAs` in Organization/Person schema | Entity disambiguation — AI knows exactly who you are |
| Third-party citations (press, academic) | Corroboration across multiple training data sources |
| Content freshness (dateModified) | Retrieval-based AI systems prefer recent content |
| Cross-platform consistency | Entity signals reinforce each other across training data |

### The entity authority flywheel:
1. Publish expert content with proper attribution
2. Earn third-party citations (press, backlinks)
3. Entity strengthens in knowledge graphs
4. AI systems more confidently cite the entity
5. AI citations drive branded search
6. Branded search further strengthens entity authority
7. Repeat

### Priority actions for GEO + E-E-A-T:
1. Ensure Organization schema has complete `sameAs` with Wikipedia/Wikidata if applicable
2. Author pages with Person schema and `sameAs` to LinkedIn, professional profiles
3. Earn at least 3-5 third-party mentions per quarter (press, guest posts, citations)
4. Keep content updated (pages within 2 months of update earn 28% more AI citations)
5. Maintain consistency across all platforms where the entity appears

---

## Implementation Priority

For a new site or content program, build E-E-A-T in this order:

1. **Trust (week 1):** HTTPS, about page, contact info, privacy policy, publication dates
2. **Expertise (week 2-4):** Author bios, author pages, Person schema, credentials documented
3. **Experience (ongoing):** First-hand content, case studies, original data, dated testing
4. **Authority (months 3-12):** Digital PR, guest posts, conference speaking, Wikipedia (if notable)

Trust is the foundation — without it, the others don't compound. Authority takes the longest but creates the strongest moat.
