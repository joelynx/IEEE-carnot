# Organiser requirements for the Task 1 Working Notes

Recorded on 12 October 2026 from this repository at commit `983537c` (the organisers' public repo, The-FinAI/IEEE-bigdata-cup) and from the organiser's email reply of 12 October 2026. Quotes are verbatim and come from public sources only; what the email said is paraphrased. Dates and deadlines are deliberately left out: the team handles all timing.

Revised on 18 November 2026, before the public release of this folder: the two rows of R4 that quoted the private email now quote the organisers' public "Task 1 rules clarification · 12 October 2026" (`app/task1/rules-clarification.tsx` in their repository, added after commit `983537c`), which states the same points. No requirement changed.

**Before writing, check for newer guidance.** The organiser wrote that the clarifications would also be added to the public guidance, and they were (the rules clarification named above). Compare the live site (https://the-finai.github.io/IEEE-bigdata-cup/) and the remote repo with what is recorded here. Pulling new commits changes the working tree, including the toolkit, so ask the user before pulling.

---

## R1. Format, length, venue, review

| Requirement | Verbatim source |
|---|---|
| **At most 10 pages in total, including references** | "The FinReason Cup requirement is no more than ten pages total, including references." (`app/task1/submission-guide.tsx`); "Length: up to 10 pages total, including references" (`README.md`) |
| **IEEE two-column conference template** | "using the IEEE two-column conference template" (`app/task1/submission-guide.tsx`); template page: https://www.ieee.org/conferences/publishing/templates.html |
| **Submit the PDF through CyberChair SC03** | "Submit the paper PDF through CyberChair SC03" (`app/task1/submission-guide.tsx`); https://wi-lab.com/cyberchair/2026/bigdata26/scripts/submit.php?subarea=SC03. **The user submits; an agent never does.** |
| **Single-blind review: include author names and affiliations** | "Keep author names and affiliations in the PDF, following the conference's single-blind review policy." (`app/task1/submission-guide.tsx`); "Include author names and affiliations in the Working Notes PDF." (`app/terms/page.tsx`) |
| Working Notes are required for final ranking and awards | "Teams seeking final ranking and awards must also submit Working Notes through CyberChair SC03" (`app/task1/submission-guide.tsx`) |
| Acceptance is decided by the organisers | "The organizers review the Working Notes and decide paper acceptance. Selected accepted papers may be included in the conference proceedings, subject to conference publication, camera-ready, registration, and presentation requirements." (`README.md`) |

## R2. Required citations (Task 1)

| Requirement | Verbatim source |
|---|---|
| Cup overview, Task 1 overview and FinChain | "Task 1 Working Notes must cite the FinReason Cup overview, the Task 1 overview, and the FinChain benchmark paper." (`app/task1/submission-guide.tsx`) |
| Use the complete official BibTeX | "Task 1 Working Notes must cite FinChain, ACL 2026, using the complete official BibTeX displayed in the homepage citation block" (`README.md`) |
| Refresh the provisional entries | "Refresh the entries before final paper submission; citation keys remain stable." (`README.md`) |

The canonical BibTeX is in `public/references/`. Use the files verbatim:
- `finreason2026-overview.bib`: key **`finreason2026overview`** (`@unpublished`, "Manuscript in preparation; proposed author list and order").
- `finreason2026-task1-overview.bib`: key **`finreason2026task1overview`** (`@unpublished`).
- `finchain.bib`: key **`xie-etal-2026-finchain`** (ACL 2026, pages 14529–14553, DOI 10.18653/v1/2026.acl-long.662).

Herculean and FinAuditing are required only for Tasks 2 and 3 (`app/task-citation-note.tsx`, `app/terms/page.tsx`). Do not add them for a Task 1 paper.

## R3. Data and code attribution

| Requirement | Verbatim source |
|---|---|
| **Data licence: CC BY 4.0** (exact allowlist of the released files) | `public/task1/RIGHTS_AND_PROVENANCE.md` |
| Attribution | "Attribution should identify the published FinReason Cup Task 1 release, link to the canonical URL above and the CC BY 4.0 license, and indicate whether changes were made." (`public/task1/RIGHTS_AND_PROVENANCE.md`). Canonical URL: https://the-finai.github.io/IEEE-bigdata-cup/task1/ ; licence: https://creativecommons.org/licenses/by/4.0/ |
| Release identities to name | Development data contract `task1-v4`; rotated test release `task1-v4-test-questions-20260901-r2` (928 questions) (`public/task1/RIGHTS_AND_PROVENANCE.md`) |
| Toolkit licence: Apache 2.0 | Applies to `finreason_task1/{admission,baseline_b1,contracts,leaderboard,scoring}.py` and `scripts/task1_cli.py` (`public/task1/RIGHTS_AND_PROVENANCE.md`). If code is ever shared, keep the licence notice with any copied toolkit file. |
| **Our use: unchanged.** | We used the official downloads byte for byte (hash-checked against the release manifests on every run). The repo's own data copies were never used, because git line-ending conversion had altered them. |

## R4. What the paper must describe (organiser instructions and terms)

| Requirement | Verbatim source |
|---|---|
| **FinChain use** | "Describe the FinChain version, matching and execution procedure, and contribution to predictions in the Working Notes." (organisers' public rules clarification, `app/task1/rules-clarification.tsx`; the organiser email of 12 October 2026, kept privately in `experiments/organiser_correspondence/`, asked for the same) |
| **Baselines: by label, cite the leaderboard** | "Model identities and full configurations are not currently public. Cite the published baseline labels and development leaderboard." (same public page; the leaderboard is https://the-finai.github.io/IEEE-bigdata-cup/task1/leaderboard/). The organiser email asked in addition that the baselines not be attributed to a particular model. |
| How a result was produced | "The organizers may ask a team to describe how a result was produced before confirming a final ranking." (`app/terms/page.tsx`) |
| Training materials | "Public training materials may be used as described in their release documentation." (`app/terms/page.tsx`) |
| Code is optional | "Code and reproducibility materials may be shared voluntarily with your Working Notes." (`app/task1/submission-guide.tsx`) |
| Required solution materials | "required solution materials mean the canonical Test prediction ZIP for all 928 questions, submitted through the Task 1 Test portal." (`app/terms/page.tsx`). Met: the accepted test submissions are in `submissions/registry.jsonl`. |

## R5. Evaluation facts the paper may state (organiser-confirmed)

From the organiser email (`experiments/organiser_correspondence/2026-10-12_reply.txt`, kept privately), paraphrased; the organisers' public rules clarification states the ranking rule, the scorer version and the baseline scores as well:
- The official test scorer is `finreason_task1/scoring.py`, version `finreason.task1.scorer/2.0.0`, toolkit commit `983537c23fbb28c4fb67fb958ffcaf49f9f7c69e`. The development Space uses byte-identical scorer files.
- **Ranking:** descending lexicographic order of (CombinedFAC, HiddenFAC, CombinedCheckpoint), each quantized to six decimal places with round-half-even. The seen and hidden strata are weighted equally. Teams equal on all three keys share a rank, and submission time is not a tie-breaker.
- Test scores are hidden until final results. **We do not know our test score; the paper must not imply that we do.**
- Organiser baselines on the 580 development-leaderboard questions (Final answer / Reasoning steps): Lite 0.234048 / 0.555354, Standard 0.980556 / 0.987725, Advanced 0.984444 / 0.990000. These are model-based references that the organisers run without gold-answer inputs.

## R6. Team constraints that also bind the paper (from `finreason_planning_prompt_v2.md`)

- **Never fabricate numbers.** Every statistic comes from something run or read; mark findings as observed or inferred.
- Every test answer was produced by the system described in the paper, with no manual edits.
- No code path, prompt or rule was conditioned on test IDs or test texts. Few-shot pools and retrieval indexes come from train and dev only.
- All model selection happened on train, dev, the lockbox or the development leaderboard, never on test.
- **FinChain:** the team's rule is stricter than the organiser's permission. The repository was used only for planning-phase analysis, at pinned commit `146eaa8225bf867fe7386c2d4727b59e03170235`.

## R7. Camera-ready instruction of the conference

Recorded on 19 November 2026 from the public page "IEEE BigData 2026 Camera Ready Instruction -- FinReason Cup: Agentic Financial Reasoning, Hedging, and Audit Verification" (https://wi-lab.com/cyberchair/2026/bigdata26/scripts/BigData_2026_Camera_ready_instruction.php?subarea=SC03) and from the IEEE Author Center page "Meet IEEE Xplore Requirements" (https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/meet-ieee-xplore-requirements/). As elsewhere in this file, dates are left out. How the paper was checked against these rows is in `VERIFICATION.md`, section 11.

| Requirement | Verbatim source |
|---|---|
| Page limit | "Workshop Papers: 10 pages, including all figures, tables, and references." and "The authors could purchase two extra pages if necessary with US$100 per page." (instruction, STEP 1). The Cup's own limit is ten pages (R1) |
| Template | "Your final papers MUST be formatted to IEEE Manuscript Templates for Conference Proceedings" (STEP 4) |
| PDF settings | "Optimized, Acrobat 5.0 compatibility, ALL graphics at least 300 dpi resolution (higher if preferred), ALL fonts MUST be embedded and subset, Postscript settings DO NOT override distiller settings, Page size is 612.0 x 792.0 points (8.5" x 11")." (STEP 5.1, punctuation added) |
| Fonts must be checked by the author | "Authors must check their final PDF files before submission to verify that all fonts have been properly embedded and subset." (STEP 5.1) |
| IEEE Xplore compatibility | Author Center: "The PDF is version 1.4 (Acrobat 5) or later, but not Acrobat 9, X, or XI."; "All fonts are embedded or subset."; "No password or other security settings are included."; "No bookmarks or links are included."; "No PDF attachments are included."; no "crop marks, registration marks, date stamps, timestamps, or any other mark" |
| PDF eXpress | "Use PDF eXpress to obtain an IEEE Xplore-compatible PDF file." with "Conference ID: 70701X" (STEP 5.3); "After using PDF eXpress, you will still need to submit the IEEE Xplore-compatible PDF file of your final paper" (STEP 2). **The author does this; an agent never does.** |
| Copyright form | "Click the following link to go to the Electronic Copyright submission site." (STEP 3). **The author does this.** |
| Final PDF | "Click the following link to go to the final paper PDF file submission site." (STEP 6). **The author does this.** |
| Registration receipt | "All authors have to register the conference first, and then, submit the copy of the registration receipt" (STEP 7). **The author does this.** |
| Presentation mode | "Please select whether your paper is a "In-person presentation" or not." (STEP 8). **The author does this.** |
