# Response to the reviews: camera-ready revision of 18 November 2026

Paper: "Exact Program-of-Thought with Pre-Registered Evaluation for Verifiable Financial Chain Reasoning: Team carnot at FinReason Cup 2026 Task 1". Both reviews recommend "Accept: a regular paper". Section numbers below refer to the camera-ready version. The source of every new number is in `paper/VERIFICATION.md`, section 8.

## Reviewer 1

**W1. The paper is long and dense; condense Sections IV and IX and move details to an appendix.**
Section IV (evaluation methodology) now has two subsections instead of four, and the post-submission section (now Section X) has four paragraphs instead of seven. The account of the synthetic set (Section VII-B) is shorter as well. Nothing was discarded: the three accounts are kept in full in a supplementary document in the public repository, which the paper cites. We did not add an appendix to the paper itself, because the ten-page limit includes it. The paper is still ten pages, because the space freed went to the analyses the reviewers asked for (W2, W3).

**W2. No ablation is reported.**
New Section VI and Table V separate three components on the 580 tuning-eval questions.

- Worked examples: one new pre-registered run without them. It missed five slots, as R0 did and in the same three conventions, and two final answers, both the known tax confusion (FAC 0.996667 against 1.000000; paired interval [−0.006667, 0]).
- Effort and sampling: stored runs rescored one sample at a time. The five-sample vote returns exactly the fields of its first sample, and single medium-effort samples fall in the range of the low-effort runs.
- Exact arithmetic: a bound from the gold. 618 of the 5,379 exact gold fields, all of them slots, cannot be matched by any double-precision value.

The formatter was not ablated, and the analysis covers familiar templates only; both limits are stated.

**W3. The hidden-template failure remains unexplained.**
New Section V-F. The published scores imply 3 wrong finals among 580 seen-stratum questions and 8 among 348 hidden-stratum questions. The hidden questions are longer and state more conditional rules, and the five samples disagreed on the final in 10 of 348 of them, against none of 580 on familiar templates with the same configuration. The causes are given as hypotheses, because no hidden reference answer is public.

**W4. Limited novelty.**
The introduction now states that program-of-thought prompting and self-consistency are established and that the paper proposes no new prompting technique. The contributions are the implementation, the audited evaluation record and the negative results.

**W5. The adopted fixes are narrow.** Agreed and already stated under "Scope of the fixes" (Section XI); unchanged.

**W6. Synthetic panels authored and validated in one model family.** Agreed and already stated; kept in Sections VII-B, X and XI.

**Minor: σ comes from three runs.** Now noted where σ is defined (Section IV-B) and where it is used as R2's limit (Section V-C).

**Minor: the Opus hypothesis.** Reworded as one possible reading that two conventions cannot establish (Section VII-A).

**Minor: release of code, prompts and cache.** Section IX, "Reproducibility and availability", names what is public and gives the repository address.

## Reviewer 2

**Which implementation records and cached responses are available for inspecting the replay claims.**
Section IX lists them: code, prompts, configurations, worked examples, splits, pre-registration and experiment logs, per-case run records, the response cache, and the paper sources with the number trace. With the cache, both test replays can be repeated without a model call. The supplement's last section says where each record is in the repository.

**Optional: one medium-effort sample against five-sample voting on the same cached questions.**
Done from the stored runs (Section VI, Table V). On tuning-eval the vote returned exactly the fields of the first sample; the five samples disagreed on 2 of 1,616 fields.

## Other changes

- The abstract and the limitations reflect the new results.
- Disclosure (6) in Section IX records the two additions made after the official results: the sample-agreement statistic on our own test outputs and the zero-shot ablation run. Neither informed a decision.
- The usage table and the cached-call count include the ablation run (69,277 calls).
- The Acknowledgment thanks the reviewers and names the model that drafted this revision.
