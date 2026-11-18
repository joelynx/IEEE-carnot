# Writing-style audit of the revised Working Notes

Reviewed 2 November 2026, against the revision of `main.tex` saved at 22:05. Source SHA-256: `4afd0929c65d89d55f3ca73ea08ea62264da95e51b57972a7d8b3658c0acca3d`.

Scope: the full manuscript, all six included tables, and the pipeline figure and caption. Locations below refer to lines in the modular `main.tex`, unless a different file is named. This is an editorial audit of the current report, not a probability estimate from an AI detector. Multiple entries can describe different effects of the same passage; they are not independent authorship indicators.

There is direct evidence of AI drafting: the Acknowledgment at line 193 says that the text of every section was drafted by Claude Fable 5.1, with specified sections and revisions drafted by Claude Opus 5.5, and then reviewed and edited by the author. That disclosure should remain. The question for the rest of this audit is where the writing retains formulaic, repetitive, or mechanically assembled features.

The dominant feature is an accumulation of assurances and qualifications. The prose repeatedly explains what was done, what was not done, what a result means, what it does not mean, and why the reader should trust the record. Most individual statements are justified. Their duplication and placement make the report sound like a sequence of generated summaries and responses to review comments.

## Observable patterns across the manuscript

### Repeated summaries instead of progression

| Repeated material | Locations | Editorial action |
|---|---|---|
| Model writes a program; sandbox executes it; formatter renders it; validator checks it | 30, 42, 73, figure caption; related explanation at 52 and 82 | Keep a short abstract description and one complete method description. Let the figure carry the sequence elsewhere. |
| Inspected errors are conventions rather than arithmetic or formatting | 30, 40, 45, 133, 148; remaining conventions recur at 188 | State the finding briefly in the abstract and substantiate it in error analysis. The contribution list and introduction need not repeat the same diagnosis. |
| Released labelled data cannot measure hidden-template gains | 30, 46, 66, 108, 136, 188 | Establish the data limitation once, then refer to the relevant evaluation consequence. Avoid restarting the explanation in each experiment. |
| Screens detect harm on familiar templates but establish no hidden-template benefit | 30, 46, 102, 108, 128, 183, 188 | Keep the definition and limitation of each screen. Shorten generic repetitions around them. |
| Cache enables reproducibility because sampling controls are unavailable | 91, 160, 169, 188; replay claims also at 30, 47, 190 | Explain access and caching in the methods; report the replay test in reproducibility. Remove the repeated mechanism explanation. |
| Test performance is lower, especially on hidden templates | 30, 49, 128, 188, 190 | Abstract plus results are sufficient for the full numbers. The conclusion should interpret the gap. |
| Synthetic evaluation did not discriminate systems | 30, 46, 136, 185, 188 | Distinguish the original synthetic set from the later study instead of repeating one general verdict. |
| No component-level causal conclusion follows | 44, 128, 188, 190 | Keep the ablation limitation and one statement about what the test aggregates cannot identify. |
| Candidate changes were registered, approved, logged, and not informed by test answers | 99, 108, 122, 163, 166, 177, 181, 183 | Preserve the audit facts, but place the protocol in methodology and the exceptions in disclosures. |
| The subscription and cost-equivalent qualification | 91, 160, 173, usage-table caption | Explain the accounting once and keep a short caption reminder if necessary. |

Abstract–introduction–conclusion repetition is normal. The problem here is that detailed mechanisms, caveats, and experimental verdicts recur almost verbatim between those sections and the body.

### Recurrent sentence machinery

- **Contrast as the default explanation.** Examples include “convention reading, not arithmetic or formatting” (45), “This validates the formatter, not the programs” (82), “a narrow sensitivity check, not evidence about hidden templates” (102), “a noise scale, not a justified maximum acceptable loss” (108), “direction, not significance” (122), “no observed final-answer harm ... not improvement” (183), and “supporting evidence, not independent human review” (188). Several distinctions are necessary. The repeated grammatical template becomes conspicuous. Some can be expressed positively by naming the actual estimand or result.
- **Symmetrical verdicts.** “Cut both ways” (30, 45), “helps where ... hurts where ...” (133), “generic in form and narrow in effect” (145), and “auditable and ... reproducible” followed by “It did not make them predictive” (190) make the prose sound repeatedly polished towards a neat ending.
- **Miniature lesson at the end of an experiment.** The stronger-model, synthetic-set, convention-example, safeguard, and final-study passages all move towards a compact moral. It is the recurrence of the arc, rather than any one conclusion, that feels templated.
- **Compliance cadence.** Repeated “every,” “only,” “no,” “never,” “nothing,” “before,” and “unchanged” frame the report as a defence of procedure. Keep the guarantees that readers need, but replace repeated assurances with one clear protocol and its exceptions.
- **Single-paragraph completeness.** A paragraph often contains its premise, exact implementation, counts, exceptions, result, decision, qualification, and interpretation. These are different reading tasks. Long source lines are not themselves a problem; the corresponding rendered paragraphs really do combine too many functions.
- **Nested qualification.** Parentheses contain extra definitions, exceptions, exact counts, model identifiers, and citations while semicolons connect further conditions. The sentence remains grammatical but its principal result becomes hard to identify.
- **Acronym and configuration recitation.** R0/R1/R2/R3/R4, S/H, P/D/J/V, and e_base/e_conv/e_hint are necessary labels. Repeated full sequences read like a registry export when the paragraph needs only the configuration being compared.
- **Registry vocabulary in narrative prose.** “Gate,” “look,” “forced,” “recipe,” “fresh identities,” “system of record,” “fixed/broken slots,” and “tuning-noex” come from the implementation and experiment logs. Define necessary terms, then write the result in ordinary research language where possible.
- **Repeated inferential connectors.** “So,” “because,” “which,” and “therefore” join observations to stronger explanations or conclusions. Check that each connector expresses an actual inference, rather than making the paragraph sound smoothly reasoned without adding evidence.
- **Abstract nouns in chains.** Phrases such as “the absence of detected harm on familiar templates,” “generation and validation process,” and “pre-registration with disclosed post-hoc choices” are precise in context but accumulate. Use an actor and a verb when the sentence does not need the formal noun phrase.

For an objective description, the 53 narrative source paragraphs/items contain 57 occurrences of “every,” 38 of “only,” 54 of “no,” 59 of “not,” 13 of “never,” 13 of “pre-registered,” and 114 semicolons. These counts include quoted prompt wording and LaTeX source notation, and exclude captions, bibliography, and most headings. They describe repetition; they do not establish an AI-authorship threshold. Fifteen narrative paragraphs/items contain at least 180 whitespace-separated source tokens. The largest include error analysis (333), the original synthetic set (303), the continuation (294), the abstract (289), and the decision-rule paragraph (285).

## Passage-by-passage inventory

“High” below means a high editorial priority or a conspicuous drafting artifact. It does not mean a statistically strong indicator of authorship. “Low” identifies ordinary academic wording that contributes to the pattern only through repetition.

### Title and abstract

| # | Location and wording | What stands out | Suggested treatment |
|---|---|---|---|
| 1 | 19: “Exact Program-of-Thought with Pre-Registered Evaluation for Verifiable Financial Chain Reasoning” | A stack of method and virtue labels makes the title read like a generated synthesis of the brief. **Medium.** | Shorten around the system and the empirical question. For example: “carnot at FinReason Cup 2026 Task 1: Program Execution and Template Generalisation.” |
| 2 | 30: “We describe team carnot's system ... in which a system must return ...” | Repeated “system” and a generic task-summary opening defer the specific contribution. **Low.** | Begin with what was built or what the evaluation found. |
| 3 | 30: the first sentence's task description, intermediate values, 348/928 count, and score weighting | It tries to satisfy several checklist items in the first sentence. **Medium.** | Keep only the task distinction needed to understand the result. Put detailed composition in the data section. |
| 4 | 30: “pipeline: a language model writes ... a sandbox executes ... a formatter renders ... validator gates ...” | The four-stage list becomes a repeated refrain in the introduction, method, and caption. **High across the document.** | Use one short abstract sentence and one full method description. |
| 5 | 30: “Every residual error we inspected ... not an arithmetic or formatting failure” | A useful scope qualification packaged as an absolute-sounding slogan; repeated shortly afterwards. **Medium.** | Tie the finding to the named labelled evaluation or retain it only once before the examples. |
| 6 | 30: “Extra samples did not fix ... cut both ways ... borrowing ... hurt ... corrections helped” | A four-part sequence of tidy experimental verdicts reads like an executive summary generated from notes. It compresses distinct evidence into one smooth sentence. **High.** | Choose the one or two findings central to the paper. Leave the remaining experiments to the body. |
| 7 | 30: “could detect harm ... but not measure hidden-template gains” | An essential distinction, repeated in several nearly equivalent forms. **Medium.** | Keep this version or the introduction version; avoid duplicating the full qualification in both. |
| 8 | 30: “found no confirmed general improvement” | The qualification is justified, but the phrase is abstract and report-like. **Low.** | State that no variant was promoted and identify the lack of confirmation where the study is described. |
| 9 | 30: “published after all of these decisions” | The abstract carries an integrity disclaimer inside the main test result. The same chronology appears elsewhere. **Medium.** | Establish the chronology once in the methods/results transition. |
| 10 | 30: “below its development scores on both strata, and most on hidden templates” | This sounds appended to interpret newly inserted numbers; “and most” is awkward compression. **Medium.** | Say directly that the largest development-to-test gap was on hidden templates, with the comparison defined in results. |
| 11 | 30: the full abstract | At approximately 289 source words it tries to cover almost every experiment, methodological defence, final metric, and replay result. The main empirical finding competes with the inventory. **High.** | Organise it around the system, development and test results, and the main evaluation limitation. |

### Introduction and related work

| # | Location and wording | What stands out | Suggested treatment |
|---|---|---|---|
| 12 | 38: full task description and strata, followed by another full task/data section | Explanatory duplication makes the introduction read like a second abstract followed by a second introduction. **Medium.** | Keep the problem and motivation; defer record structure and scoring detail. |
| 13 | 40: “Two properties of the task shaped our design. First ... Second ...” | A standard essay scaffold. Here the two branches are long and overlap with later contributions. **Low alone; medium in context.** | Keep it only if each property leads directly to one design decision. |
| 14 | 40: “so neither adds error; ... approximations ...; and nothing guarantees ...” | The central claim has acquired successive qualifications inside one sentence. It reads as a revised assertion with patches attached. **High.** | Separate exact rational operations, approximate functions, and semantic correctness into distinct sentences. |
| 15 | 40: “once execution and rendering are exact” | A simplifying slogan returns immediately after the numerical-exactness qualification. **Medium.** | Refer to the actual evaluated outputs or the rational part of the system. |
| 16 | 40: the three “whether ... whether ... whether ...” examples | A conventional rhetorical triad that is then reproduced in error analysis and limitations. **Low alone.** | Let the detailed error examples do this work; retain at most one motivating example here. |
| 17 | 42: “Our system is an exact program-of-thought pipeline” and its full stages | Near-repetition of the abstract before the detailed system section. **High through duplication.** | Replace with the specific design choice that needs motivation. |
| 18 | 42: “The paper makes four points” | An explicit outline rather than substantive research content. **Medium.** | State the contributions compactly or remove the lead-in. |
| 19 | 44–47: four numbered contribution summaries | Each starts a small self-contained summary with a cross-reference and often a caveat. Together they replicate the abstract's structure. **Medium.** | Retain contributions only if each is distinct and not immediately restated in prose. |
| 20 | 44: “We ran no ablation, so we do not attribute this to any single component” | Correct limitation positioned as a defensive addendum to the first contribution. **Medium.** | Keep the limitation in the evaluation discussion rather than repeatedly interrupting the introduction. |
| 21 | 45: “cut both ways” and the entire extra-samples/model/examples/corrections list | Almost the same experimental synopsis as the abstract. **High.** | Remove this duplicate rather than finding synonyms. |
| 22 | 46–47: “Our validation could ...”; “The work is auditable and replayable” | Self-evaluative contribution labels rely on broad nouns and adjectives. **Medium.** | Identify the concrete artifact or evaluation property and its limit. |
| 23 | 49: results and “our development checks did not anticipate this gap” | The abstract's result and final interpretation appear again before results. **Low individually; medium through repetition.** | Use this as the introduction's main empirical motivation if the surrounding summary is shortened. |
| 24 | 52: related-work chain “X ...; we add ... Y ... motivate ... Earlier ...; ... this task ...” | A compressed citation tour connects each literature family to a system feature in a predictable way. **Medium.** | Explain the closest methodological difference first; shorten the benchmark catalogue. Keep the citations. |

### Task and data

| # | Location and wording | What stands out | Suggested treatment |
|---|---|---|---|
| 25 | 57: repeated “A ... specification ...”; “The ... specification ...” | Schema documentation rendered as a prose catalogue. **Low.** | A compact record example or table would reduce repetition if space permits. |
| 26 | 60: train counts, template difficulty counts, answer counts, slot histogram, gold-field histogram, test histogram | A large inventory appears without explaining which distributions matter to the argument. **Medium.** | Prioritise the distributions that motivate exact rendering and the seen/hidden shift; let a table carry secondary counts. |
| 27 | 60: “every file ... on every run” | A double universal assurance characteristic of the report's compliance voice. **Low alone.** | Keep the manifest-validation fact once in reproducibility. |
| 28 | 63: repeated “the mean over ... the mean over ... a ... mean ... the mean over ...” | Faithful scorer documentation but tiring as a single sentence. **Medium readability issue.** | Express the hierarchy as a compact formula or sequence. Do not remove the weighting information. |
| 29 | 63: organiser confirmation plus invalid-file explanation plus exact ranking rule | Too many distinct topics share one paragraph. **Medium.** | Separate matching rules from aggregation and ranking. |
| 30 | 66: “so we believe the two counts identify the same questions” | A smooth inferential connector makes a heuristic correspondence feel like a conclusion from matching totals. **Medium.** | State the train-based routing heuristic and mark its equivalence to the official stratum as an assumption. |
| 31 | 66: the final “No labelled example ... cannot be measured ...” | Another complete restatement of the central data limitation. **Medium through repetition.** | Keep the statement here as the authoritative data limitation and shorten its repetitions elsewhere. |

### System description

| # | Location and wording | What stands out | Suggested treatment |
|---|---|---|---|
| 32 | 73: “Fig. ... shows the pipeline” | Generic figure-announcement boilerplate. **Low.** | Begin with the input or execution procedure; the figure reference can sit at the end. |
| 33 | 73: the full prompt composition, example prompt, retries, voting, validation, fallback, completeness, packaging, abandoned plans | A method paragraph tries to contain the whole implementation record. **High.** | Split prompt construction, execution/retries, and submission handling. Remove the abandoned-plan sentence unless it resolves an actual ambiguity. |
| 34 | 73: “declared in advance”; “no value is ever edited”; “No run needed the fallback” | Repeated procedural assurances interrupt the method explanation. **Medium.** | Define fallback behavior here and retain the relevant integrity statement once elsewhere. |
| 35 | 73: “were planned and never built” | The paper exposes the planning document's history instead of describing only the deployed method. **Medium.** | Omit unless the distinction is needed to interpret a named experiment. |
| 36 | 76: “fixed and ... chosen mechanically”; repeated “verified”; “all six ... first attempt” | Verification language is stacked around an otherwise concrete selection procedure. **Medium.** | Describe the selection rule and scorer acceptance directly. |
| 37 | 76: categories, selection algorithm, six named exemplar topics, exclusion policy in one paragraph | Specification completeness displaces a clear explanation of why three examples are used. **Medium.** | Keep the algorithm; move topic lists or alternatives into a compact table if necessary. |
| 38 | 79: whitelist catalogue plus rewrite catalogue plus helper catalogue plus sandbox configuration | Reads like a generated expansion of source-code comments. Most details are legitimate, but relevance is not ranked. **Medium.** | Order the paragraph by numerical semantics and execution isolation. Keep exact settings needed for reproducibility. |
| 39 | 82: “The formatter is the only component that writes a value” | Ambitious categorical opening that leads to another categorical closing. **Medium.** | State what the formatter receives and emits. |
| 40 | 82: “This validates the formatter, not the programs” | Important correction, but visibly shaped as a response to a previous objection. **Medium.** | Integrate the scope: “The round-trip test checks rendering of gold values.” Preserve the distinction. |
| 41 | 82: “and nothing else” | Emphatic reassurance adds little after a concrete processing description. **Medium.** | Delete the emphasis; retain the provenance fact. |
| 42 | 85: the final complete-row limitation | Technically valuable, but another paragraph-ending corrective contrast. **Low; keep substance.** | A shorter positive formulation is possible: “The vote guarantees field-level provenance, not a common generating program.” Avoid repeating the same limitation in full later. |
| 43 | 88: “reads only ... built from train only ... applied identically to every question” | Three successive assurances establish genericity. **Medium.** | State once that the fixed rule is derived from train and uses the listed public fields. |
| 44 | 91: invocation flags, empty directory, scrubbed environment, long cache-key list, model-ID agreement | A run manifest is converted into narrative without prioritisation. **Medium.** | Separate the access method, cache identity, and integrity check. |
| 45 | 94: R0 through R4 recited after Table I; exact old/new prompt wording; final caveat | The paragraph doubles the table, then appends an exception. **High.** | Let the table define the version history; discuss only the two prompt changes in the text. |
| 46 | 94: “One caveat:” | A generic conversational repair marker. **Medium in this already qualified paragraph.** | State the remaining system-prompt instruction directly as part of the implementation description. |

### Evaluation methodology

| # | Location and wording | What stands out | Suggested treatment |
|---|---|---|---|
| 47 | 99: long sequence of split names and parenthetical counts | The reader must reconstruct a set diagram from a registry-like paragraph. **Medium.** | Give a compact split table or equation; use prose for the isolation policy. |
| 48 | 99: “split once ... never redrawn”; “each logged with a reason”; “aggregates only” | Repeated integrity conditions are mixed into data allocation. **Medium.** | Keep the exact split policy and consolidate access restrictions. |
| 49 | 102: “We originally called H-mode a hidden simulation” | A visible revision seam: the manuscript discusses its previous terminology. **High.** | Define current H-mode directly. Historical naming is unnecessary unless it matters to interpreting archived protocol names. |
| 50 | 102: “not independent replications ... a narrow sensitivity check, not evidence ...” | Two consecutive exclusions deliver the same important limit. **Medium.** | State the shared requests and the actual scope of the sensitivity check in one sentence. |
| 51 | 105: “Every labelled run ... all reported ... each run's ... must equal ...” | Verification is expressed as repeated global assurances rather than one reproducible procedure. **Medium.** | Name the scorer and describe the weight-recomputation check once. |
| 52 | 108: “Two rules were written down before any candidate was run” | Vague procedural preamble that becomes redundant with the exact rules and registration details. **Low.** | Start with the rules and their registration dates or identifiers if those are material. |
| 53 | 108: “which the pre-registration called ... and we call ...” | Another response-to-review seam: two naming systems and the act of renaming dominate the definition. **High.** | Give the current definition first, then a short parenthetical historical label. |
| 54 | 108: conditions (a)–(e), interpretation, example of harm, noise-margin critique, historical decision policy, logging | A 285-token source paragraph combines a protocol, statistical explanation, self-critique, and provenance statement. **High.** | Separate the historical screen from its inferential limitation and from recordkeeping. |
| 55 | 108: “We report its decisions unchanged” | Sounds addressed to the reviewer who requested a correction. **High.** | The paper should report the decisions directly. Explain the historical rule accurately without narrating the editorial response. |
| 56 | 108: “each candidate was approved before it was built” | Approval-workflow wording suggests a supervising user and an implementing assistant, without identifying who approves. **Medium.** | Specify the research action: candidate specifications were registered/frozen before evaluation. Retain any distinct author-approval fact where relevant. |

### Results

| # | Location and wording | What stands out | Suggested treatment |
|---|---|---|---|
| 57 | 116, 119, 122: three consecutive sections begin “Table ... gives/compares/lists ...” | Repetitive table-announcement scaffolding. **Medium.** | Begin each paragraph with the principal finding. |
| 58 | 116: “by a handful of slots” | Casual vagueness in a section otherwise committed to exact results. **Low.** | Use the count or leave numerical comparison to the table. |
| 59 | 119: “which we read as evidence that the pipeline and format are sound” | A general quality judgment follows two nearby scores. “Sound” is less specific than the evidence. **Medium.** | Identify the actual observation: similar aggregate scores, valid packaging, or no observed format errors, as applicable. |
| 60 | 119: “so its score here is optimistic, and it says nothing about hidden templates” | A valid selection caveat expressed as another emphatic closing contrast. **Medium.** | State selection on the leaderboard once; keep the data's scope clear. |
| 61 | 122: “we summarise the decisions and their evidential strength” | Announces the writer's operation instead of presenting a finding. **Medium.** | Delete the announcement and start with the accepted/rejected changes. |
| 62 | 122: “on our recommendation it was not uploaded” | Agent–user voice leakage is plausible here. In a single-author paper, who recommends to whom? **High as an agency problem.** | “We retained R1 rather than submitting R2,” or “The author did not submit R2,” depending on the intended account. |
| 63 | 122: “confirms the direction, not significance” | A polished qualification compresses a statistical limitation into a slogan. **Medium.** | State the positive point estimate and interval including zero; do not make the reader decode “directional confirmation.” |
| 64 | 122: long version-by-version recap of the decision table | Numerical facts are repeated along with approval verdicts and their exceptions. **High.** | Keep a short explanation of the few decisions that need interpretation. Let the table hold all comparisons. |
| 65 | 125: receipt prefix, hash prefix, exact timestamp, “no test upload followed it” | Operational provenance becomes narrative clutter. **Low as authorship evidence; medium editorial concern.** | Preserve a receipt reference if needed to identify the evaluated submission; the audit file can carry the full metadata. |
| 66 | 127: “Official test results (update of 2 November 2026)” | The heading makes the paper look like a patched working document. **Medium.** | Use “Official Test Results”; state publication chronology in its opening sentence. |
| 67 | 128: “Everything above was decided ... the rest of this paper keeps that separation” | Direct editorial management of the document; “everything above” includes descriptive material, not just decisions. **High.** | “All model-selection decisions preceded publication of the test results.” |
| 68 | 128: “derived by us; not published” | The derivation needs attribution, but the phrase sounds like an appended provenance correction. **Low.** | Give the equation and mark the value approximate. |
| 69 | 128: “of the same order as” | A smooth but loose comparison: the values are all near one. **Medium.** | Give the absolute differences or say “close to the earlier lockbox scores.” |
| 70 | 128: “it is not a ceiling of the task” | Rhetorical explanation after the result, followed by yet more exclusions. **Medium.** | State the direct comparator: eight teams achieved hidden FAC 1.000000. |

### Rejected variants and error analysis

| # | Location and wording | What stands out | Suggested treatment |
|---|---|---|---|
| 71 | 130: “What Did Not Transfer” | A persuasive thematic heading suggests direct evidence about transfer that the evaluation largely could not measure. **Medium.** | “Rejected Variants and Synthetic Evaluation” is more literal. |
| 72 | 133: “so we asked whether a stronger model reads conventions better” | A tidy question–experiment narrative introduces a humanlike reading trait. **Low alone.** | Name the comparison and target error classes directly. |
| 73 | 133: “The verdict ... supported a stronger model” | The procedure is personified and “stronger” is left broad. **Medium.** | State that the diagnostic favored Opus on one of the two tested conventions. |
| 74 | 133: “helps where ... hurts where ...”; “on a knife-edge” | Balanced moral plus dramatic metaphor. **High relative to the report's technical register.** | Report the two corrected and three introduced errors and the small margin to the adoption threshold. |
| 75 | 136: every authoring/filtering setting and stopping result in one paragraph | An experiment log has been polished into a single 303-token account. **High.** | Separate construction, quality checks, difficulty screening, and outcome. |
| 76 | 136: “Our reading is narrow:” | Visible corrective qualification; the phrase advertises restraint rather than simply making a narrow claim. **High.** | “This process did not produce a discriminating evaluation set.” Preserve the limitation about wider generalisation. |
| 77 | 136: “which does not show ...; leaving conventions unstated would instead ...” | A methodological result expands into a neatly balanced counterfactual. **Medium.** | Keep the observed result; put the ambiguity concern in the limitations discussion. |
| 78 | 139: “a borrowed example misleads about as often as it helps” | An aphoristic generalisation is smoother and broader than the reported three fixes/eight breaks. **High.** | State the observed counts and the cross-template convention mismatch. |
| 79 | 139: “As pre-registered, R1 stayed and the candidate was not tweaked” | Chatty experiment-decision language plus another adherence assurance. **Medium.** | “We rejected the candidate under the registered rule.” |
| 80 | 142: “The dimensionless hint was our own error” | Unusually candid, concrete ownership. **Low; largely keep.** | The useful point is the incorrect scaling instruction. Name that error directly and retain responsibility. |
| 81 | 142: “pre-registered post hoc” | Compressed procedural language is hard to parse and sounds like an agent reconciling conflicting instructions. **Medium.** | Say that the candidate was selected after inspecting an earlier experiment, then registered before its own evaluation. |
| 82 | 145: “generic in form and narrow in effect”; “nil by construction” | Two polished, balanced verdicts frame otherwise concrete trigger counts. **Medium.** | Let the triggering rule and zero novel-route matches establish the scope. |
| 83 | 148: “All case-level analysis uses tuning data” before the disclosed lockbox inspection | A sweeping assurance is followed by a qualification later in the same paragraph. This is a common patchwork effect, not evidence of deception. **Medium.** | State the scope and the disclosed three-case exception together. |
| 84 | 148: “Every remaining error we inspected ... we found no ...” | Repeats the abstract, motivation, contribution, and diagnostic verdict. **Medium.** | Use the error taxonomy and examples as evidence rather than restating the slogan. |
| 85 | 148: three examples, several systems, two splits, lockbox disclosure, sampling result, effort confound | The 333-token paragraph has too many functions despite its useful specificity. **High.** | Separate error taxonomy, configuration comparisons, and limitations/disclosures. Preserve the numerical examples. |

### Integrity, resource use, later study, and conclusion

| # | Location and wording | What stands out | Suggested treatment |
|---|---|---|---|
| 86 | 154: “No ...; no ...; no ...; ... nothing ...”; “our stricter rule” | Required provenance information is delivered as a repeated denial and a self-evaluative comparison. **Medium.** | Preserve every material FinChain-use disclosure in a compact factual statement. Remove any implication that stricter necessarily means better. |
| 87 | 160: “No temperature or seed ... so ... cache ...” | Full repetition of the model-access explanation. **Medium.** | Refer to the methods and focus this paragraph on model identities and experimental/submitted roles. |
| 88 | 163: “Every test answer ... no prediction ... All model selection ... no test output ... No code path ...” | An exceptionally dense block of universals and denials. **High as a style pattern; the facts matter.** | Separate the prediction-generation process from the explicit selection policy and the disclosed usage-statistic exception. |
| 89 | 166: five numbered disclosures with embedded qualifications | Can read like an agent's compliance checklist, but the disclosures are valuable. **Low as AI evidence; medium readability concern.** | Keep a distinct disclosure section or compact table. Do not delete exceptions to make the report sound cleaner. |
| 90 | 169: “every run's ... every comparison ... pre-registration ... access ... receipt” | Another comprehensive inventory closes the replay result. **Medium.** | Say where the artifacts are available and which replay checks were performed. |
| 91 | 173: all test-run call counts after the usage table | Further registry detail after full project accounting; not all numbers inform the argument. **Low.** | Retain counts necessary for the cost/performance discussion; otherwise let the artifact index carry them. |
| 92 | 177: “without any further upload, test run or lockbox look” | Integrity preface before a new experiment is described. It repeats other boundaries. **Medium.** | Establish the post-submission study's data policy once, then define the variants. |
| 93 | 177: P, D, J, V plus controls in one paragraph | Recipe definitions read like configuration export, with many inserted conditions. **Medium.** | Use a short recipe table; describe only the verifier's unusual constraint in prose. |
| 94 | 179: “Every difference lay in one ... family” | A valid finding with the document's familiar universal framing. **Low; largely keep.** | This is one of the concrete limitations worth retaining. Avoid repeating its moral in the abstract, interpretation, and conclusion. |
| 95 | 181: “identical requests, outputs and selections”; “Each family passed three gates” | Serial parallel lists lend an artificially complete audit cadence. **Medium in context.** | Keep the gates, but separate replay validation from family validation and performance. |
| 96 | 181: “A stress panel ... was more revealing” | Narrator commentary announces the significance of the next result instead of showing it. **Medium.** | Start with the bond-variant scores. |
| 97 | 181: “R4 remains the system of record” | Status-dashboard or agent-handoff language. **Medium.** | “No post-submission variant was submitted” or “We retained R4.” |
| 98 | 183: “A safeguard that can be met” | A conversational, story-shaped heading carries a verdict before the technical explanation. **High.** | “Revised Regression Safeguard” or a title naming the template-loss bound. |
| 99 | 183: full old gate, two estimands, feasibility calculation, replacement rule, full outcome, scope disclaimer | A 232-token paragraph mirrors an answer to the earlier critique. **High.** | Separate historical gate, replacement criterion, and observed result. |
| 100 | 183: “This shows ... not improvement, and P has not been submitted” | A recurring result–negation–status ending. **Medium.** | Report zero observed final-answer changes and the bound. State submission status once in the study overview. |
| 101 | 185: “Reading” | A generic heading announces interpretation without naming the subject. **Medium.** | Use “Limitations of the Synthetic Panels” or integrate the interpretation into the experiment discussion. |
| 102 | 185: “ambiguity is one observed mechanism, not the only one” | Balanced correction to an earlier overgeneralisation. Necessary substance, but recognisable response-to-review wording. **Medium.** | Name the ambiguity and units-conversion findings directly. |
| 103 | 188: a limitation for almost every component and experiment in one paragraph | It reads as an accumulated checklist of objections: hidden data, H-mode, R3, echo rule, ablation, voting, interface, residual errors, synthetic panels, oracle independence. **High.** | Group the limitations into evaluation coverage, causal attribution, and numerical/semantic scope. Avoid restating all of them after already explaining them locally. |
| 104 | 188: “small, slot-level ... directionally confirmed”; “supporting evidence, not independent human review” | Well-balanced qualification phrases have become another repeated register. **Medium.** | Retain the actual effect and confidence interval or the actual oracle limitation; avoid repeated verdict labels. |
| 105 | 190: “In sum” | A generic summary marker before a conclusion that mostly restates existing summaries. **Low alone.** | Start with the main finding. |
| 106 | 190: “The evaluation discipline, namely ...” | An abstract, self-assessing noun phrase introduces another list of methodological virtues. **Medium.** | State what the logs and replay checks establish. |
| 107 | 190: “made ... auditable ... reproducible. It did not make them predictive ...” | The report ends with a particularly tidy contrast. It sounds composed for rhetorical effect and over-compresses the evaluation's implications. **High relative to plainer alternatives.** | End with the specific empirical limitation: the familiar-template and synthetic evaluations did not reveal the hidden-template performance gap. |
| 108 | 193: AI drafting disclosure and author responsibility | **Direct disclosed provenance**, not a hidden stylistic clue. The formal responsibility language is conventional. | Preserve the disclosure and its accurate description of roles. Do not remove it as an editing tactic. |

## Tables, figure, and source artifacts

- **Pipeline caption:** repeats the complete method and ends “omitted, never edited.” Both the stage list and the assurance already appear in the body. The figure should clarify the flow rather than supply another manifesto of invariants. Keep the fallback rule if it is needed to interpret the diagram.
- **Systems caption:** “The systems.” is generic but harmless. The table itself is useful and conventional. The main issue is that line 94 narrates virtually the same version history again.
- **Labelled-results caption:** “Official scores ... seen stratum; 6 decimal places” and “Lockbox rows are aggregates only” add layered procedural labels. Most are useful here; remove duplicative reminders from surrounding prose rather than stripping the caption of scope.
- **Baseline caption:** “by their published labels,” “Portal values,” and “6 decimal places” make it resemble an internal verification note. Keep the dataset size and provenance needed to compare the scores; the decimal convention can be defined once globally.
- **Decision-table caption:** contains the estimand, exact-fraction format, location of decimal values, resampling scheme, replicate count, interval type, and definition of “forced.” This is unusually dense. Move the shared statistical method to methodology and keep the caption's reading instructions brief.
- **Usage caption:** repeats the full-project scope, cache provenance, cost-equivalent definition, and subscription qualification. All are legitimate. Consolidate them with lines 160 and 173 so the same accounting disclaimer is not repeatedly rebuilt.
- **Post-submission caption:** “R4 is the accepted system,” “Development evidence only,” and “none ... uploaded” repeat the same boundary in three ways. One clear statement of the study's non-submitted status is enough here.
- **Dense technical labels and abbreviations:** “S/H,” “Fam. 1,” “Fam. 2,” and the internal recipe names are not signs of AI writing by themselves. They can make tables feel exported from a run dashboard when the caption does not explain the experimental distinction.
- **Source-only comments:** `% TODO(user)` at line 170 and the generated standalone-file comments expose the editing workflow in the source, but do not appear in the rendered report. They should not be presented as visible PDF writing defects. The TODO is an unresolved publication choice, not evidence obtained from the prose.

## Features that should not be treated as AI evidence

- First-person plural in a single-author technical paper is conventional. The specific problem with “on our recommendation” is unclear agency, not the word “we.”
- An abstract, contribution list, related-work section, tables, and a limitations section are ordinary research conventions. Their presence proves nothing.
- Exact figures, fractions, model identifiers, source hashes, and citations are often necessary. The issue is redundant placement and unranked detail, not precision itself.
- Parallel structure, passive voice, semicolons, hyphenated technical terms, and three-item lists are not standalone authorship clues. Their repeated use can make a passage monotonous.
- Correctly limiting a causal or statistical claim is good scientific writing. The revision should consolidate caveats, not suppress them.
- The report does not depend on the stereotyped florid vocabulary often associated with generated prose: the inspected text does not use “delve,” “tapestry,” “leverage,” “seamless,” or “foster.” There is no reason to invent examples of those habits here.
- It is not generally empty or content-free. The tax example, sign example, variance example, annual/cumulative multiplier discrepancy, actual rejected variants, and small effect counts are valuable specifics. Preserve them.
- Formal licensing language, required citations, and the AI-use acknowledgment should not be removed to make the manuscript appear less AI-assisted.

## How to revise without losing the science

1. **Consolidate the repeated explanations before changing vocabulary.** Synonym replacement would preserve the main problem and could make the report more artificial. Assign one main location to the pipeline, each evaluation limitation, model access, and integrity policy.
2. **Write each result paragraph around one finding.** For example: observed difference, relevant cases, decision. Put its general evaluation limitation in the section where that limitation is defined.
3. **Remove response-to-review wording.** “We originally called,” “we report ... unchanged,” “our reading is narrow,” and “the rest of this paper keeps that separation” should become direct statements about the study.
4. **Clarify agency.** Replace “on our recommendation” and unspecified approval wording with the actual research decision and who made it.
5. **Split the overloaded paragraphs.** Highest priorities: 40, 73, 94, 108, 122, 128, 133, 136, 148, 181, 183, and 188. Use a table where the material is intrinsically a mapping or inventory.
6. **Use concrete findings instead of repeated verdict adjectives.** Replace “sound,” “more revealing,” “on a knife-edge,” and “generic in form and narrow in effect” with the specific observation that justifies the description.
7. **Preserve scope and disclosures.** Do not remove the lockbox inspection, the post-hoc candidate selection, the original adoption screen's limits, the related-model oracle limitation, or the AI-drafting statement.

Examples of local edits:

| Current wording | Plainer alternative |
|---|---|
| “The paper makes four points.” | Omit the announcement; state the contributions if they add information beyond the abstract. |
| “We originally called H-mode a hidden simulation, but it holds no template out of development.” | “H-mode excludes same-template exemplars; the templates remain part of development.” |
| “We report its decisions unchanged.” | Omit; report each historical decision under the rule that was actually used. |
| “on our recommendation it was not uploaded” | “We did not submit R2.” |
| “Our reading is narrow: this generation and filtering process did not yield a set that separates systems.” | “This process did not produce a discriminating evaluation set.” |
| “A stress panel of paired variants was more revealing.” | “On the ambiguous bond variants, V scored 4/4 and R4 scored 2/4.” Keep the full panel results nearby. |
| “R4 remains the system of record.” | “No post-submission variant was submitted.” |
| “A safeguard that can be met” | “Revised Regression Safeguard.” |
| “The echo rule is generic in form and narrow in effect.” | State the generic matching rule and the observed trigger counts. |
| “It did not make them predictive of hidden-template performance.” | “The familiar-template checks and synthetic panels did not reveal the hidden-template performance gap.” |

These edits are intended to make the account clearer and less repetitive. They are not a method for concealing AI assistance or satisfying an authorship detector. The underlying experiments and disclosures should remain intact.
