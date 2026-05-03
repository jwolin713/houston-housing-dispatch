---
date: 2026-05-03
topic: houston-housing-dispatch
---

# Houston Housing Dispatch Requirements

## Summary

Houston Housing Dispatch will be a mostly automated, editorially opinionated newsletter workflow for smart Houston homebuyers and real-estate-curious locals. The first version proves the bet with 1-2 weekly issues focused on a handful of inside-the-loop neighborhoods, each issue making readers smarter about Houston housing and pointing them toward a few listings genuinely worth attention.

---

## Problem Frame

Smart Houston buyers and real-estate-curious locals already spend time browsing HAR, Zillow, and agent Instagram feeds, but those sources leave most of the interpretation work to the reader. Listing portals provide inventory and specs. Agent feeds tend to be seller-oriented and inconsistent. Neither gives a steady buyer-oriented read on which homes are actually worth attention and why.

The audience is not looking for basic first-time-buyer education, generic listing syndication, or luxury-house spectacle. They can follow price per foot, lot quality, layout, build quality, neighborhood tradeoffs, and resale logic, but they want a sharp local filter that saves time and makes them feel more oriented in the Houston market.

Evidence for demand currently comes from conversations with people who spend meaningful time browsing homes and from analogous real-estate media formats in other markets. Houston-specific demand should be treated as a product bet to validate through the first issues.

---

## Actors

- A1. Reader: A smart Houston buyer or real-estate-curious local who wants curated listings with practical judgment and local context.
- A2. Editorial operator: The person accountable for spot-checking the automated output, preserving taste, and approving the final issue before publication.
- A3. Listing intake sources: HAR notification emails and supporting listing-detail sources that provide candidate homes for the issue.
- A4. Drafting workflow: The automated system that enriches listings, selects candidates, drafts the issue, and creates a Substack draft.

---

## Key Flows

- F1. Listing intake and enrichment
  - **Trigger:** New HAR listing notification emails arrive for the monitored area.
  - **Actors:** A3, A4
  - **Steps:** Candidate listings are collected, enriched with additional listing details, and made available for editorial selection.
  - **Outcome:** The workflow has enough structured listing context to judge whether a home has a meaningful editorial angle.
  - **Covered by:** R4, R5, R6, R11

- F2. Automated issue assembly
  - **Trigger:** The newsletter workflow runs for the next scheduled issue.
  - **Actors:** A4
  - **Steps:** The workflow evaluates enriched listings, chooses the strongest candidates, frames why each one matters, and drafts the issue.
  - **Outcome:** A Substack draft exists with a curated set of listings and an issue-level read on the market batch.
  - **Covered by:** R7, R10, R11, R12, R13, R14

- F3. Human spot-check and publication decision
  - **Trigger:** A Substack draft is ready for review.
  - **Actors:** A2
  - **Steps:** The editorial operator reviews the selected listings, catches obvious misses, adjusts tone or selection when needed, and decides whether the issue is ready to publish.
  - **Outcome:** Publication remains human-approved while the system handles most selection and drafting work.
  - **Covered by:** R12, R13, R14

---

## Requirements

**Audience and positioning**
- R1. The product must serve sophisticated Houston homebuyers and adjacent real-estate-curious locals who want taste, practicality, and local judgment together.
- R2. The product must avoid positioning itself as generic listing syndication, broker inventory, first-time-buyer education, agent promotion, pure luxury coverage, or national design content without Houston context.
- R3. Each issue must make the reader feel more oriented, more confident, and more curious about specific Houston homes.

**Editorial filter**
- R4. A listing should qualify for inclusion only when there is something substantive to say beyond specs.
- R5. The editorial filter must favor listings with at least one clear angle: rarity, value mismatch, character, strong tradeoff, location-specific hook, or buyer-usefulness.
- R6. The product must treat "interesting" as a buyer-relevant judgment, not simply as "nice house."
- R7. The issue should help readers understand what the included batch says about Houston housing right now, not only present individual listing blurbs.

**Issue shape**
- R8. The first version should publish 1-2 issues per week.
- R9. The first version should focus on a handful of specific inside-the-loop Houston neighborhoods.
- R10. Each issue should surface a memorable set of homes worth real attention, with the expectation that a few listings will stand out after reading.

**Automation and review**
- R11. The workflow should pull new HAR listing notifications, enrich candidate listings with additional property details, select listings for inclusion, draft the newsletter using the editorial voice, and create a Substack draft.
- R12. The automation endpoint must be a ready-to-review Substack draft, not direct publication.
- R13. The workflow should support mostly automated first-pass selection and drafting while preserving human spot-checking before publication.
- R14. Early workflow runs should support editorial calibration by preserving selected and rejected candidates with selection rationale so automated picks can be compared against human judgment before the selection process is fully trusted.
- R15. Planning must define credential handling and access control for mailbox access, enrichment tools, Spiral, Substack draft creation, workflow execution, and operator or administrator privileges.

---

## Acceptance Examples

- AE1. **Covers R4, R5, R6.** Given a generic new-build townhome with no meaningful pricing edge, layout distinction, lot advantage, character, or location-specific tradeoff, when the workflow evaluates it for inclusion, it should not select the listing only because it is recently listed or visually polished.
- AE2. **Covers R4, R5, R10.** Given an older inside-the-loop home with a rare lot, compromised updates, and a price that creates a real buyer tradeoff, when the workflow evaluates it, it should be considered eligible because there is a useful judgment to make.
- AE3. **Covers R7, R11, R12, R13.** Given enough eligible listings for an issue, when the workflow runs, it should create a Substack draft that includes both listing-specific angles and a batch-level read, then stop for human review before publication.
- AE4. **Covers R13, R14.** Given an early automated issue run, when the workflow selects listings, the editorial operator should be able to compare selected and rejected candidates with the rationale for each selection decision.

---

## Success Criteria

- Readers finish an issue feeling smarter about Houston housing and remember 2-5 specific homes.
- Readers trust that the Dispatch notices things that raw portals and agent feeds do not.
- The editorial operator can review and publish an issue with spot-checking rather than rebuilding the selection and draft from scratch.
- The first version generates enough reader retention, replies, forwards, clicks, or qualitative feedback to validate continuing the product.
- A downstream planner can design the pipeline without inventing the audience, editorial inclusion rules, issue cadence, human review boundary, calibration needs, credential/access-control expectations, or initial geographic scope.

---

## Scope Boundaries

- Direct Substack publication without human review is out of scope for the first version.
- Houston suburbs are deferred until the inside-the-loop version proves the editorial filter.
- Broader market essays, neighborhood guides, and other content formats are deferred until the core listing dispatch works.
- Generic listing syndication is outside the product identity.
- Broker-oriented raw inventory feeds are outside the product identity.
- First-time-buyer education is outside the product identity as a primary product.
- Pure luxury coverage is outside the product identity unless a luxury listing has a concrete buyer-relevant angle.

---

## Key Decisions

- Start with inside-the-loop neighborhoods: This keeps the first version focused on a coherent local reader and avoids diluting the editorial filter before proving demand.
- Publish 1-2 issues weekly: This is frequent enough to become habit-forming while keeping the first version operationally realistic.
- Make "smart buyer would pause here" the inclusion test: This keeps the newsletter distinct from portals, agent promotion, and generic pretty-house content.
- Stop at Substack draft creation: Human review protects trust while allowing the workflow to automate the repetitive intake, enrichment, selection, and drafting steps.
- Treat editorial judgment as the product advantage: The workflow exists to scale a sharp local filter, not just to move listings between tools.
- Calibrate automation before fully trusting selection: The workflow should make selected and rejected candidates inspectable until automated judgment has proven close enough to the editorial operator's standard.

---

## Dependencies / Assumptions

- HAR notification emails are available and reliable enough to use as the primary listing intake source.
- Additional listing details can be enriched through the Zillow Details Scraper or an equivalent source.
- Spiral can draft in a voice close enough to the desired editorial style for human spot-checking to be efficient.
- Substack draft creation is available enough to support the intended workflow.
- Houston-specific demand is not yet proven beyond conversations and analogous media examples in other markets.
- The editorial operator can define and refine taste through spot-checking before the automation becomes fully trusted.
- The implementation will need access to connected accounts or credentials for mailbox intake, enrichment, drafting, and Substack draft creation; planning must define least-privilege access before build work begins.

---

## Outstanding Questions

### Deferred to Planning

- [Affects R9][User decision] Which inside-the-loop neighborhoods should be included in the first monitored set?
- [Affects R5, R11][Technical] What listing data is required to reliably detect rarity, value mismatch, character, tradeoffs, and buyer-usefulness?
- [Affects R11, R13][Technical] How should the workflow expose candidates and rejected listings so the editorial operator can spot-check efficiently?
- [Affects R11, R12][Technical] What Substack draft creation path is available and reliable enough for automation?
- [Affects R15][Technical] What credential storage, access control, logging redaction, and environment-separation approach should govern the connected accounts?
- [Affects R3, R7][Needs research] What voice and issue structure best balances practical buyer judgment, local media personality, and concise listing coverage?
