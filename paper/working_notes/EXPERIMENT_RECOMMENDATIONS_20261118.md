# Recommended experiments for the FinReason Task 1 camera-ready paper

**Recommendation, 18 November 2026.** Prioritize the controlled comparison of worked examples, reasoning effort and voting, and the replay of cached programs under two arithmetic implementations. Both address Reviewer 1's request to separate component contributions. Add a small challenge panel only if the team can independently verify its reference answers in time. These are proposals for post-submission analysis. The existing results and their limitations are documented in the [revision assessment](REVIEW_REVISION_ASSESSMENT_20261118.md).

## 1. Compare worked examples, reasoning effort and voting

The current examples comparison pairs an October run with examples and a November run without them. A change in the served model could contribute to the difference. Reviewer 2's single-sample comparison is already available for medium effort with examples. A fresh experiment would show whether the value of voting changes with effort or with the examples in the prompt. [Existing component table](tables/components.tex) and [zero-shot study design](../../experiments/ablation_zeroshot_20261118/preregistration.json).

Use the same 580 labeled tuning-eval questions across all four conditions. Cross **zero or three worked examples** with **low or medium Sonnet reasoning effort**. Generate five samples per question in every condition, for **11,600 planned samples plus retries**. The same five outputs support both individual-sample and voting analyses.

- Freeze question IDs, prompts, exemplars, model identifier, retry policy, formatter, vote and tie rules before the first call. Interleave the four conditions over time. Assign fresh cache identities to each planned draw and reuse them on resume.
- Score each sample and the five-sample per-field vote with the official scorer. Report final-answer correctness (FAC), checkpoint score, wrong finals and missed slots. Show the vote against sample 1 to answer Reviewer 2 directly, and against the mean of all five single-sample scores to show how representative sample 1 was.
- Compare examples on/off at each effort and low/medium effort at each example setting. Keep comparisons paired by question and account for the 290 shared templates in the uncertainty estimates. Record fresh calls, retries, tokens, wall time and cost equivalent.
- Report every condition, including ties. If the differences amount to one or two cases, show those counts alongside the intervals. All 580 questions come from familiar templates, which limits the generalization claim.

**Runtime planning.** The latest 580-question low-effort run took 1,018 seconds, with 577 fresh calls and three cache hits. Linear extrapolation gives about 5.7 hours for 11,600 samples at that throughput. Benchmark all four conditions early, since longer prompts, medium effort, retries and service quota can change the estimate. For this Claude pipeline, model-call throughput determines feasibility more directly than local GPU capacity. [Run record](../../experiments/ablation_zeroshot_20261118/run/summary.json).

## 2. Replay identical programs with exact and floating-point arithmetic

Use cached generated programs from a fixed labeled run. This gives a direct measurement of what arithmetic handling changes for programs the system actually produced. The current count of gold values that fail one float-to-text conversion cannot establish a score loss for every floating-point implementation. [Arithmetic claim and counterexamples](REVIEW_REVISION_ASSESSMENT_20261118.md).

1. Freeze the case list, cached program selection and handling of failed attempts. First reproduce the original predictions with the existing sandbox and formatter. Resolve discrepancies before interpreting the comparison.
2. Execute the same programs with binary64 floating-point arithmetic under the same sandbox protections. Specify the treatment of literals, arithmetic helpers, rounding and serialization in advance. Give both paths the public output specification and validator. Check ordinary decimals, nonterminating fractions, rounding boundaries and enum outputs before scoring.
3. Compare paired FAC and checkpoint scores. Count correct-to-wrong and wrong-to-correct fields, execution failures, numeric changes and rendering or validation failures. If arithmetic and formatting both change for a field, record that attribution as unresolved. To measure rendering alone, hold computed values fixed and score two specified renderers on those values.

Report the measured difference for the implementations tested. This replay requires **zero fresh model calls** and can run alongside experiment 1.

## 3. Test convention ambiguity on an independently checked panel

The previous synthetic panels approached ceiling, and their authors and checkers shared a model family. A small paired panel could test why a particular convention or wording change causes errors. The official test answers remain private, so the panel can test proposed mechanisms but cannot identify which official questions the system missed. [Earlier experimental record](IMPROVEMENT_EXPERIMENTS.md) and [organizers' results note](https://the-finai.github.io/IEEE-bigdata-cup/task1/leaderboard/test/).

- Build problem pairs that change one feature at a time, such as making the sign convention explicit, adding an irrelevant number or adding a conditional step. Record whether the correct answer should stay the same or change.
- Use executable reference solutions, a blind checker from a different model family and human adjudication of disputed cases. Rewrite or exclude questions with multiple defensible answers before scoring.
- Separate pilot and evaluation families before trying the system. Use the pilot to check label quality and whether the tasks reveal meaningful differences. Freeze the evaluation families and report all of them, including those on which every system agrees.

Proceed only if the pilot yields verified, informative cases early enough to finish the two primary experiments. Otherwise defer this extension and keep the hidden-template discussion at the level of hypotheses.

## Two-day allocation

| Elapsed time | Work |
| --- | --- |
| First 4 hours | Freeze comparisons and reporting rules, benchmark model throughput, validate the arithmetic replay. |
| Next 20 hours | Run experiments 1 and 2. Develop the optional challenge panel independently if people are available to check it. |
| Next 12 hours | Score complete conditions, compute paired differences and uncertainty, and inspect discrepancies. |
| Final 8–12 hours | Add one compact results table to the paper, put detailed diagnostics in the supplement, update the response to reviewers and verify the release records. |

Reserve the writing buffer against the actual deadline. The published camera-ready cutoff is **19 November 2026 at 23:59 AoE**, or **20 November at 15:59 in Dubai**. [Official schedule](https://the-finai.github.io/IEEE-bigdata-cup/).
