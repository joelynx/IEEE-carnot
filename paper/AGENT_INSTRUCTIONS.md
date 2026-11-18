# Instructions: write team carnot's Working Notes for FinReason Cup 2026, Task 1

You are writing the team's Working Notes paper, the challenge paper the organisers require for final ranking. Everything you need is recorded in this repository. Read it in the order below, write the paper as LaTeX in the IEEE two-column conference format within **10 pages including references**, verify every number, and hand the result to the user. **The user submits the paper; you never do.**

Start every session with: `python -I paper/build_facts.py --check` (it must print "facts.json up to date").

**The final system is R4** (latest accepted test submission, receipt `test-20261012T170418Z-811e06a0…`, recorded in the registry; cached replay byte-identical). Confirm with `facts.json#submissions.latest_test`, and ask the user whether anything was uploaded after 12 October 2026.

---

## 1. Hard rules (non-negotiable)

1. **Never invent a number, result, citation or claim.**
   - Every number in the paper must come from `paper/facts.json`, `paper/TABLES.md`, or a file they name in `_source`.
   - Every factual claim about the system must match the code or the logs.
   - If you cannot find support for something, leave it out or ask the user.
2. **Never write BibTeX from memory.** The three required entries are in `public/references/` (already copied verbatim into `paper/working_notes/references.bib`). Add any other reference only from an authoritative export (ACL Anthology, DBLP, arXiv, the publisher) you can actually reach, or from the user.
3. **Read only.** Do not modify `runs/`, `experiments/`, `submissions/`, `cache/`, `synth/`, `configs/`, `carnot/`, `development_files/`, `test_questions/`, the organiser toolkit (`finreason_task1/`, `scripts/task1_cli.py`) or `PLAN.md`. Write only under `paper/working_notes/` (plus `paper/VERIFICATION.md`).
4. **Do not run models, upload anything, or submit anything** (no CyberChair, no portals). Do not commit or push unless the user asks.
5. **What the paper must not contain:**
   - **Our test score.** It is unknown (hidden until final results). Say so where relevant.
   - Statistics computed from test answers. Usage and cost of test runs are fine.
   - Case-level lockbox detail beyond the disclosed look-1 `taxcalc` note (DOSSIER §7). Lockbox results are aggregates only.
   - Deadlines or schedules (the team handles timing).
6. **Organiser baselines:** name them only by their labels (Lite, Standard, Advanced) and cite the development leaderboard, https://the-finai.github.io/IEEE-bigdata-cup/task1/leaderboard/. Never attribute them to a model.
7. **Calibrated claims.**
   - Hidden-template performance was **not measured**.
   - R3's gain is **small, slot-level and only directionally confirmed**.
   - The seen-template result is near ceiling, on the development leaderboard.
   - Do not call a difference significant unless its confidence interval excludes 0 *and* the pre-registered rule says so.
8. **Mark inference as inference.** The dossier tags facts [O] (observed) and [I] (inferred); keep that distinction in the wording ("we observed" / "we believe" / "suggests").

## 2. Before writing: ask the user, and check for updates

Ask the user (one message, all at once):
1. **The author list and affiliations, in order.** Required: review is single-blind. The repo's git user is Joel Jobi; confirm everyone else and every affiliation.
2. A preferred **title**, if any (offer 2–3 options; see §4).
3. Whether to **share code** with the paper (voluntary, per the organisers), and where (a public repo URL). If yes, the toolkit files keep their Apache-2.0 notice.
4. Acknowledgements, if any, and whether to report cost-equivalent figures (they are list-price equivalents; the work ran on a subscription).

Then check for newer organiser guidance:
- Compare the live site (https://the-finai.github.io/IEEE-bigdata-cup/, Task 1 submit page, `#paper-references`) with `paper/ORGANISER_REQUIREMENTS.md`.
- Check the remote repo: `git fetch` (read-only), then `git log HEAD..origin/main -- README.md app public/references`. Ask the user before pulling, because pulling changes the toolkit too.
- **Refresh the three required BibTeX entries** from the current official files before the final version, as the organisers ask; the keys stay the same.

## 3. Reading order

| # | Read | Take from it |
|---|---|---|
| 1 | `paper/ORGANISER_REQUIREMENTS.md` | The rules the paper must satisfy (format, length, citations, attribution, required statements) |
| 2 | `paper/DOSSIER.md` | **The whole story**, with every fact tagged and sourced. This is your primary source. |
| 3 | `paper/TABLES.md`, `paper/facts.json`, `paper/REPLAY_CHECK.md` | Every number, with provenance |
| 4 | `PLAN.md`: §0 (decisions), §0.1 (build status), §2.3–2.5 (task contract, data, scoring), §2.8 (FinChain test), §3.3–3.7 (sandbox, voting, formatter, fallback), §4a, §4b, §4c, §5.2–5.6 (evaluation design) | Detail and rationale. **The plan describes some things that were never built** (same-template retrieval, a chain-of-thought fallback, an LLM judge). Describe only what DOSSIER §3 says was built. |
| 5 | Code: `carnot/solver.py`, `carnot/sandbox/{policy,finq,executor,worker}.py`, `carnot/formatter.py`, `carnot/routing.py`, `carnot/exemplars.py`, `carnot/compare.py`, `carnot/run.py`, `carnot/llm_client.py`, `carnot/prompts/pot_system_v1.txt`, `configs/{r0,r1,r2,r3}.json` | Exact method details for the system section |
| 6 | `experiments/preregistration.jsonl` | Each candidate's pre-registered rule, result and disclosures, in order |
| 7 | `experiments/organiser_correspondence/2026-10-12_reply.txt` | Ranking rule, scorer version, baseline numbers, FinChain disclosure request |
| 8 | `public/references/*.bib`, `public/task1/RIGHTS_AND_PROVENANCE.md` | Citations, data licence and attribution wording |
| 9 | `FinChain_A_Symbolic_Benchmark_for_Verifiable_Chain-of-Thought_Financial_Reasoning.pdf` (repo root) | Background for the related-work paragraph (cite the official BibTeX) |

## 4. The paper

**Format.** `\documentclass[conference]{IEEEtran}`, the skeleton in `paper/working_notes/main.tex`. At most **10 pages including references and any appendix**. Author names and affiliations are visible.

**Title options** (confirm with the user):
- "Exact Program-of-Thought with Pre-Registered Evaluation for Verifiable Financial Chain Reasoning"
- "carnot at FinReason Cup 2026 Task 1: Exact Programs, Spec-Driven Rendering, and What Did Not Transfer to Hidden Templates"

**The story, in four messages:**
1. **Exact program-of-thought plus spec-driven rendering puts seen-template questions at ceiling.** The model writes a program; an exact-arithmetic sandbox runs it; a formatter renders every field from its spec, round-tripping all 8,888 gold fields; the official validator gates every row. Development leaderboard: R0 0.998333 / 0.998056, then **R4 1.000000 / 0.999167**, above the organisers' published baselines (Advanced 0.984444 / 0.990000).
2. **What remains is convention reading, not computation.** Every residual error on labelled data is a misread slot convention.
   - Extra samples do not fix systematic errors.
   - A stronger model reads slot descriptions more literally, which cut both ways.
   - Borrowing conventions from other templates fails, because slot names are not used consistently.
   - A wrong unit hint in our own prompt caused errors, and fixing it (R3, then R4 on the seen route) helped. A narrow rule for the tax "Report X" confusion (R4) removed the last wrong final on the leaderboard.
3. **Measuring hidden-template generalisation is the hard part.**
   - We used fixed splits with a lockbox, a noise-calibrated paired bootstrap, pre-registration, and a non-inferiority rule for the stratum no labelled data can measure.
   - A synthetic "hidden-like" set failed instructively: fully specified problems were trivial even for the smallest model.
4. **Reproducible and auditable.** Every submission regenerates byte-identically from cached responses, and every decision is logged.

**Suggested structure and page budget** (about 9.5 pages plus references; adjust to fit):

| Section | ≈ Pages | Content (DOSSIER section) |
|---|---|---|
| Abstract | 0.2 | the four messages; dev-leaderboard numbers; test scores pending |
| 1 Introduction | 0.6 | task, the seen/hidden split, contributions (§1, §2) |
| 2 Task, data and scoring | 0.6 | data counts, rendering conventions, hierarchical scoring, ranking (§2) |
| 3 System | 2.0 | pipeline, prompt, verified exemplars, sandbox, formatter and validator gate, retries and fallback, voting, routing rule, R0/R1/R3/R4 table (§3) |
| 4 Evaluation methodology | 1.0 | splits and lockbox, S/H modes, official-score recomputation, σ_run, paired bootstrap, decision rules incl. non-inferiority, pre-registration (§4) |
| 5 Results | 1.4 | labelled-data table, leaderboard vs baselines, decision table, submissions (§5.1–5.3) |
| 6 What did not transfer | 1.5 | Opus (R2) and the diagnostic; the synthetic set; cross-template conventions; the hint fix (§6) |
| 7 Error analysis | 0.7 | residual convention errors with 2–3 concrete examples from tuning data (§7) |
| 8 Integrity, reproducibility, resource use | 0.7 | FinChain statement, data attribution, model disclosure, disclosures, replay check, usage table (§5.4, §8, §10) |
| 9 Limitations and conclusion | 0.4 | §9 |
| References | ≈ 0.4 | the three required entries plus any verified related work |

**Tables to include** (convert from `paper/TABLES.md`; keep only what fits):
- **T-A:** results on labelled data (DOSSIER §5.1).
- **T-B:** development leaderboard vs organiser baselines (§5.2).
- **T-C:** pre-registered decisions: candidate, rule, Δ with CI, decision (§5.3).
- **T-D:** systems R0/R1/R2/R3/R4 (§3.7).
- Optional **T-E:** usage by model (§5.4).
- A pipeline figure (TikZ or a simple box diagram) if space allows.

**Required statements** (each must appear somewhere):
- **FinChain** (DOSSIER §8.4): version (pinned commit), no template matching or execution, no FinChain data, no contribution to predictions; the organisers later permitted these uses, and the team's stricter rule excluded them.
- **Data attribution:** "We use the FinReason Cup 2026 Task 1 release (development data `task1-v4`; test release `task1-v4-test-questions-20260901-r2`), https://the-finai.github.io/IEEE-bigdata-cup/task1/, licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/); we made no changes to the data." Adapt the wording, but keep all four elements.
- **Models:** `claude-sonnet-5-5` (R0, R1, R3, R4) through the Claude Code CLI (2.1.296) in headless mode, with effort settings and N. Opus 5.5, Fable 5.1 and Haiku 5.5 appear only in experiments not used for submissions. The CLI offers no sampling controls, so the response cache provides reproducibility.
- **Integrity:** no manual edits of predictions; no decision used test outputs (with the thinking-token caveat, DOSSIER §8.2); generic rules only; the disclosures in DOSSIER §8.7–8.8 and the look-1 note in §7.
- **Test scores pending**, and hidden-template performance not measured.
- **Required citations:** `\cite{finreason2026overview}`, `\cite{finreason2026task1overview}`, `\cite{xie-etal-2026-finchain}`.

**Related work** (only with verifiable BibTeX; see rule 2): program-of-thought prompting and program-aided language models; self-consistency decoding; chain-of-thought prompting; financial numerical-reasoning benchmarks (FinQA, TAT-QA, ConvFinQA); FinChain (required). If you cannot obtain authoritative BibTeX, describe the ideas without citing and ask the user.

**Style.**
- IEEE conference tone: precise and modest. Define FAC (final-answer correctness) and the checkpoint (reasoning-steps) score once.
- Give official scores to 6 decimal places as the organisers do; give Δ as an exact fraction with a decimal, plus the 95% CI.
- Use consistent names: R0, R1, R2, R3, R4; "seen route" / "novel route"; S-mode / H-mode.
- Say "list-price equivalent" for costs.

## 5. Procedure

1. Run `python -I paper/build_facts.py --check`. If it reports a difference, run it without `--check`, review the diff, and tell the user.
2. Ask the user the §2 questions; check for organiser updates.
3. Read everything in §3; make notes keyed to DOSSIER sections.
4. Draft `paper/working_notes/main.tex` section by section. Put tables in `paper/working_notes/tables/` and figures in `paper/working_notes/figures/`.
5. Compile: `pdflatex` → `bibtex` → `pdflatex` ×2 (or `latexmk -pdf main.tex`). **Observed on 12 October 2026:** MiKTeX's `pdflatex` is installed (`%LOCALAPPDATA%/Programs/MiKTeX`), but the `IEEEtran` class is not ("File `IEEEtran.cls' not found"). **Ask the user before installing anything.** Options: MiKTeX Console → install package `ieeetran`; or `mpm --install=ieeetran`; or put `IEEEtran.cls` and `IEEEtran.bst` from the official template (https://www.ieee.org/conferences/publishing/templates.html) or CTAN into `paper/working_notes/`. The skeleton otherwise needs only standard packages (amsmath, booktabs, graphicx, url, hyperref). If compiling is impossible, deliver the source and say so.
6. **Check the length:** the PDF must be ≤ 10 pages in total. Cut prose before cutting required statements.
7. **Write `paper/VERIFICATION.md`:** a table mapping **every number and factual claim** in the paper to its source (`facts.json` key path or file and line). Any number without a source must be removed.
8. Run the checklist in §6 and record the result at the end of `VERIFICATION.md`.
9. Hand over to the user:
   - the PDF (if compiled) and the source;
   - the open questions;
   - the list of anything refreshed from the organisers' site.
   - Remind them that only they submit through CyberChair.

## 6. Final checklist

- [ ] IEEE two-column conference format (`IEEEtran`, `conference` option)
- [ ] **≤ 10 pages total, including references** (and any appendix)
- [ ] Author names and affiliations present (single-blind)
- [ ] Cites `finreason2026overview`, `finreason2026task1overview` and `xie-etal-2026-finchain` with the official BibTeX, refreshed from the organisers' current files
- [ ] Data attribution: release named, canonical URL, CC BY 4.0 link, "no changes made"
- [ ] FinChain statement: version, procedure (none: no matching, no execution), contribution (none)
- [ ] Baselines named only by label, development leaderboard cited
- [ ] Model disclosure: IDs, access route, effort, N, no sampling controls, the cache
- [ ] Test scores stated as unknown and pending; hidden-template performance stated as unmeasured
- [ ] Disclosures: look-1 case inspection; the post-hoc hint candidate; the R2 diagnostic seen before pre-registration; the thinking-token caveat; incidents (no effect on submissions)
- [ ] Reproducibility: byte-identical cached replay of the final submission (`paper/REPLAY_CHECK.md`)
- [ ] No case-level lockbox detail beyond the disclosed note; no test-answer statistics; no deadlines
- [ ] Every number traced in `paper/VERIFICATION.md`
- [ ] The PDF compiles cleanly, with no overfull margins hiding text

## 7. If something is missing or contradictory

Stop and ask the user. Do not fill gaps with plausible-sounding text. If DOSSIER and `facts.json` disagree, `facts.json` wins; record the discrepancy in `VERIFICATION.md`.
