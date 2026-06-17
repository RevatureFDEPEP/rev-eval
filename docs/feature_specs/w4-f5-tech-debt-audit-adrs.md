# W4-F5 — Technical Debt Audit and ADR Documentation

*Identify, document, and rank the technical shortcuts taken across the four weeks, write Architecture Decision Records for the two or three most consequential choices, and produce a prioritized repayment backlog.*

* **Curriculum Fit**: Day 20 (Technical debt identification in own work, architectural decision reflection, defending AI-generated code, storytelling around technical work).
* **Prerequisites**: Day 20 topics, plus the full four weeks of accumulated decisions.
* **Cross-Week Dependencies**: Requires W4-F1 (Reporting Endpoints) — the cross-service data access decision (shared DB vs. API call vs. event projection) made in W4-F1 is one of the two required ADRs. Requires W3-F2 (Scoring Engine) — the partial-credit algorithm choice (full-match, Jaccard, or set-overlap) made in W3-F2 is the second required ADR. A meaningful debt inventory cannot be written without a substantially complete codebase, so all prior features should be at least partially implemented.
* **Time Estimate**: Without AI tools: 4–6 hours | With AI tools (Gemini/Claude Code): 2–4 hours

## Implementation Details

1. Conduct a structured walkthrough of the codebase to identify shortcuts: inline TODOs, missing input validation, hardcoded magic values, endpoints that return all rows without pagination, tests that use mocks where integration tests would give more confidence, and schema columns added without a migration.
2. Write a debt inventory in `docs/technical-debt.md`. For each debt item, record the name, the location in code, the condition under which the debt matters (e.g., works fine at 50 users, breaks at 5,000), and an urgency rating (low / medium / high based on whether the current scale is already close to the limit).
3. Write Architecture Decision Records (ADRs) in `docs/adr/` for at least two decisions made during the project: the cross-service data access pattern chosen for reporting (shared DB vs. API call vs. event projection) and the scoring algorithm chosen for multi-select questions (full-match, Jaccard, or set-overlap). Each ADR follows the standard structure: context, decision, consequences, alternatives considered.
4. For any code section that was drafted with AI assistance (Claude Code, Copilot, etc.), add an inline comment noting the AI involvement and the human review that followed. Prepare a short verbal defence of that section covering what the AI produced, what was changed, and why the final shape was chosen.
5. Produce a one-page technical narrative combining what/why/how storytelling for the two most interesting features built, tying each to a concrete technical decision and the ADR that documents it.
