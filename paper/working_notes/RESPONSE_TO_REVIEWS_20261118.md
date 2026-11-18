# Response to the reviews: camera-ready revision of 18 November 2026

Paper: "Exact Program-of-Thought with Pre-Registered Evaluation for Verifiable Financial Chain Reasoning: Team carnot at FinReason Cup 2026 Task 1". Both reviews recommend "Accept: a regular paper". Section numbers below refer to the camera-ready version. The source of every new number is in `paper/VERIFICATION.md`, sections 8 and 9.

This letter was revised later on 18 November 2026, after an outside assessment of the first camera-ready build (`paper/VERIFICATION.md`, section 9). The assessment found that the answer to W1 overstated the shortening and that the arithmetic claim under W2 was too strong. Both answers below are corrected, and the arithmetic claim is replaced by a measurement.

It was revised once more the same day, after an outside audit of the paper's wording (`paper/VERIFICATION.md`, section 10). Neither outside document is part of the public repository. That revision changed wording only: it corrected sentences whose short form said more than their source, and removed repetition. The descriptions below follow the final text.

## Reviewer 1

**W1. The paper is long and dense; condense Sections IV and IX and move details to an appendix.**
Section IV (evaluation methodology) now has two subsections instead of four, and the post-submission section (now Section X) has three paragraphs instead of seven. The account of the synthetic set (Section VII-B) is shorter as well, and the derivation behind Section V-F moved to the supplement. These accounts are kept in full in a supplementary document in the public repository, which the paper cites. A few template names and example values were dropped from the main text; they remain in the run records and in the version submitted for review (`archive/submitted_20261102/`). We did not add an appendix to the paper itself, because the ten-page limit includes it.

The paper as a whole did not get shorter. It is still ten pages, and its source grew from 7,135 to 7,601 whitespace-separated tokens (8,470 to 9,134 words of extracted PDF text), because the space freed went to the analyses the reviewers asked for (W2, W3). The request is therefore met only in part: the two sections named by the reviewer are condensed, and the reader's total load is not lower.

**W2. No ablation is reported.**
New Section VI and Table V examine four components on the 580 tuning-eval questions. The four comparisons are not equally controlled, and the section says so.

- Worked examples: one new pre-registered run without them. It missed five slots, as R0 did and in the same three conventions, and two final answers, both the known tax confusion (FAC 0.996667 against 1.000000; paired interval [−0.006667, 0]). The run with examples is five weeks older, so a change of the served model cannot be excluded; the paper now says so.
- Effort and sampling: stored runs rescored one sample at a time. The five-sample vote returns exactly the fields of its first sample, and single medium-effort samples fall in the range of the low-effort runs.
- Exact arithmetic: a pre-registered replay without a model call. The 580 stored programs of the first R0 run were executed again exactly, which reproduced every stored field, and in binary64 arithmetic. Under three pre-declared ways of writing a float into an exact field the replay loses 3 or 4 final answers and misses 64 to 178 slots, against 0 and 5 (FAC 0.994286 to 0.995952, checkpoint 0.839775 to 0.948571). Every lost half-up final is an exact rounding tie. A further 1,734 programs from the R0 run on tuning-noex give the same picture (10 more half-up finals lost under every rule, all exact ties). This replaces the gold-based count of the first camera-ready build, whose wording ("cannot be matched by any double-precision value … would forfeit them") claimed more than the count showed; the corrected count is in the supplement as a statement about representation only.

The formatter was not ablated, the replay measures three float renderings of programs written for an exact pipeline, and the analysis covers familiar templates only; these limits are stated.

**W3. The hidden-template failure remains unexplained.**
New Section V-F. If the 348 questions that our rule routes as novel are the hidden ones, which we assume and cannot verify, the published scores imply 3 wrong finals among the 580 seen-stratum questions and 8 among the 348 hidden-stratum questions. The novel-route questions are longer and use conditional wording more often, and the five samples disagreed on the final in 10 of 348 of them, against none of 580 on familiar templates with the same configuration. The causes are given as hypotheses, because no hidden reference answer is public.

**W4. Limited novelty.**
The introduction now states that program-of-thought prompting and self-consistency are established and that the paper proposes no new prompting technique. The contributions it lists are the pipeline, the error and component analysis, the evaluation design with its limit, and the replayable submissions with the public record.

**W5. The adopted fixes are narrow.** Agreed and already stated under "Scope of the fixes" (Section XI); unchanged.

**W6. Synthetic panels authored and validated in one model family.** Agreed and already stated; kept in Sections VII-B, X and XI.

**Minor: σ comes from three runs.** Now noted where σ is defined (Section IV-B) and where it is used as R2's limit (Section V-C).

**Minor: the Opus hypothesis.** Reworded as one possible reading that two conventions cannot establish (Section VII-A).

**Minor: release of code, prompts and cache.** Section IX, "Reproducibility and availability", names what is public and gives the repository address.

## Reviewer 2

**Which implementation records and cached responses are available for inspecting the replay claims.**
Section IX lists them: code, prompts, configurations, worked examples, splits, pre-registration and experiment logs, per-case run records, the response cache, and the paper sources with the number trace. They are public at https://github.com/joelynx/IEEE-carnot, the cache and the run records as archives of release `v1.0`. With the cache, both test replays can be repeated without a model call; the repository's README gives the commands with `--cache-only`, and says that the replay still needs the recorded version of the Claude Code CLI and a claude.ai login. The supplement's last section says where each record is in the repository.

**Optional: one medium-effort sample against five-sample voting on the same cached questions.**
Done from the stored runs (Section VI, Table V). On tuning-eval the vote returned exactly the fields of the first sample; the five samples disagreed on 2 of 1,616 fields.

## Other changes

- The abstract and the limitations reflect the new results.
- Disclosure (6) in Section IX records the three additions made after the official results: the sample-agreement statistic on our own test outputs, the zero-shot ablation run and the arithmetic replay. None informed a decision.
- The usage table and the cached-call count include the ablation run (69,277 calls).
- The Acknowledgment thanks the reviewers and names the model that drafted this revision.
