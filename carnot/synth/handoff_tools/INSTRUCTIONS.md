# Instructions: template authoring and blind cross-check

You are working for a research team that is preparing an entry to a financial-reasoning benchmark. The team needs two things from you, and the tools in this folder record everything it needs, so please follow these instructions exactly and in order.

1. **Phase 1: author 25 new question templates.** Each template is a parameterised finance problem with an exact reference program. The team will use your templates to build an evaluation set. Another author receives the same assignments and the same rules, and you never see their templates.
2. **Phase 2: solve 50 questions blind.** Another author wrote these questions. You write a program for each one. The team compares your answers with that author's reference values to find mistakes in their templates.

Work through everything without waiting for the operator. If you are genuinely blocked, make the most reasonable choice, record it in `outputs/REPORT.md`, and carry on.

---

## Ground rules (read these first)

1. **Stay inside this folder.** Do not read, list or search anything outside it.
2. **No internet.** Do not search the web, browse, download or install anything. Do not try to look up the benchmark, its data, the FinChain project or any other dataset. Everything you need is in this folder.
3. **Write only under `outputs/`.** Do not change anything in `reference/`, `tools/`, `lib/` or `phase2/`. `tools/start_phase2.py` creates `phase2/items/` itself. File hashes are checked when the folder comes back.
4. **Use the tools for every check and every answer.** They log every call. Never edit anything in `outputs/logs/`, `outputs/drafts/`, `outputs/programs/`, `outputs/solutions/` or `outputs/previews/` by hand.
5. **Keep the phases in order.** Do not open, decode or inspect `phase2/crosscheck_items.bin` yourself. `tools/start_phase2.py` unseals it when phase 1 is complete.
6. **Work independently.** Every template is your own design. Do not copy the structure of the existing templates shown in your assignments, and do not reuse one of your templates for another assignment.
7. **If a tool reports `TOOL_ERROR` or crashes, do not repair or work around the tools.** Describe what happened in `outputs/REPORT.md` and continue with whatever still works.
8. Use **Python 3.10 or newer**, standard library only. Run every command from this folder (the one containing this file).

## What is in this folder

| Path | What it is |
|---|---|
| `INSTRUCTIONS.md` | This file. |
| `RUN_INFO.md` | Filled in by the operator. Leave it alone. |
| `MANIFEST.sha256` | Hashes of every file provided. Leave it alone. |
| `reference/house_rules.txt` | **The rules every template must follow.** The other author received exactly this text. |
| `reference/assignments.json` | The 25 assignments: index, domain, topic, difficulty. |
| `reference/assignment_prompts/assignment_XX.txt` | Your assignment XX, with the existing templates in that topic. You must not duplicate them. The other author received exactly this text. |
| `reference/solving_rules.txt` | The rules for writing a solving program in phase 2. The team's own solvers receive exactly this text. |
| `reference/novelty_index.json`, `reference/length_limits.json` | Data used by the checker. You do not need to read them. |
| `tools/` | The commands listed below, plus `sample_template.json`, which shows the file format only (a basic practice template, far easier than your assignments). |
| `lib/` | The team's checking code and the benchmark's official validators. Used by the tools. |
| `phase2/crosscheck_items.bin` | The sealed phase-2 questions. |
| `outputs/` | Everything you produce goes here. |

---

## Phase 0: setup

1. Run `python tools/selfcheck.py`. It must print `OK`. If it does not, write what happened to `outputs/REPORT.md` and stop.
2. Write `outputs/agent_info.md` with: the model you are (name and version, as far as you know them), the application or tool you are running in, whether you can run code and write files here, and the current date and time with its time zone.

## Phase 1: author 25 templates

Do the assignments in order, `00` to `24`. For each assignment XX:

1. **Read** `reference/house_rules.txt` and `reference/assignment_prompts/assignment_XX.txt`. The house rules define the template format, the program rules and the quality rules. Read them closely. In particular:
   - every template is advanced and needs at least five computational steps;
   - it must include at least one of: a threshold or eligibility decision, a solve-for or iterative calculation, or multi-period cash flows with explicit timing;
   - it has 3 or 4 slots;
   - the difficulty must come from the reasoning required, never from vagueness.
2. **Write** the template as a single JSON object and save it as `outputs/templates/assignment_XX.json`. The house rules say "inside a ```json code block" because the other author answered in a chat. You save only the JSON object itself, with no code fences.
3. **Check** it: `python tools/check_template.py outputs/templates/assignment_XX.json`
   - `PASS`: the template is final. Open `outputs/previews/assignment_XX.md` and read the six generated questions and their reference values. If you notice a real mistake (a wrong formula, an unstated convention, an unrealistic case), do not change the file; record it in `outputs/REPORT.md` under "Known issues in my templates".
   - `REJECTED`: read the reason, revise the same file and check again. Each assignment allows **3 checks in total** (the first draft plus 2 revisions).
   - Still rejected after 3 checks: write `outputs/templates/assignment_XX.FAILED.md` with two or three sentences on what failed and why. Then move on.
4. You may run your own quick experiments in Python while designing (for example to test a formula), but only `tools/check_template.py` decides whether a template passes.

**What the checker verifies:**
- the format and the house-rule limits (word-only slot descriptions of at most 15 words, a question text of at most 1,269 characters, 3 or 4 slots, difficulty `advanced`);
- that your domain, topic and difficulty match the assignment;
- that your program runs in an exact-arithmetic sandbox for six random parameter draws, and that every output renders under its spec;
- that the benchmark's official validators accept every generated question and reference row;
- that the question is genuinely new: its wording pattern and its slot list must not occur among the benchmark's existing questions;
- that the six final answers are not all the same.

The quality rules in the house rules cannot be checked automatically: an unambiguous text, stated conventions, realistic parameters, and real multi-step reasoning. They are still the most important part of the task.

When all 25 assignments have a passed template or a `FAILED.md` note, go to phase 2.

## Phase 2: blind cross-check of 50 questions

1. Run `python tools/start_phase2.py`. It confirms phase 1 is complete, freezes your templates and unseals the questions into `phase2/items/item_01.json` … `item_50.json`.
2. For each item NN, in order:
   1. **Read** `reference/solving_rules.txt` and the item's `prompt` field. The prompt is the full task exactly as the team's solvers see it: worked examples, then the question with its required outputs. The item's `question` field holds the same question as structured data.
   2. **Write** a program that defines `solve()` and returns a dict with `"final"` and every required slot, following the solving rules. Save it anywhere under `outputs/`, for example `outputs/work/item_NN.py`.
   3. **Record** it: `python tools/solve_question.py phase2/items/item_NN.json outputs/work/item_NN.py`
      - `OK`: done; go to the next item.
      - `FAILED` (the program did not run) or `INCOMPLETE` (a field is missing or cannot be rendered under its spec): fix the program and run the command again. Each item allows **3 attempts in total**, and no retries after an `OK`.
3. **Solve each question on its own merits, from its text alone.** You have no reference answers. Do not try to infer them, and do not compare items with each other or with your own templates to guess answers. Where the wording leaves a convention open, choose the reading you think a careful expert would choose, and note the item in `outputs/REPORT.md`.

## Phase 3: finish

1. Write `outputs/REPORT.md` with these sections:
   - **Who and where:** your model and tool, as in `outputs/agent_info.md`, and when you started and finished.
   - **Phase 1 summary:** how many templates passed and failed, and anything notable about the process.
   - **Known issues in my templates:** any template (by assignment number) that you believe has an error, an ambiguity, or an unrealistic or too-easy design. Be candid; this is reviewed by a person.
   - **Phase 2 notes:** any question (by item number) that you found ambiguous, inconsistent or suspicious, and what you think is wrong with it.
   - **Problems:** any tool errors or confusing instructions.
   - **Departures:** anything you did differently from these instructions, and why. Write "None" if there were none.
2. Run `python tools/finish.py`. It must print `Finished`. If it lists open items, complete them first.
3. Tell the operator in one line that the run is complete. They will collect the whole folder.

---

## Quick reference

| Step | Command |
|---|---|
| Setup | `python tools/selfcheck.py` |
| Check a template | `python tools/check_template.py outputs/templates/assignment_XX.json` |
| Open phase 2 | `python tools/start_phase2.py` |
| Record an answer | `python tools/solve_question.py phase2/items/item_NN.json <your program>` |
| Finish | `python tools/finish.py` |

**Limits:** 3 checks per assignment; 3 attempts per phase-2 item; no internet; write only under `outputs/`.
