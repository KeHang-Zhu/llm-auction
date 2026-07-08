# How to make the DA "OSP" implementation actually OSP

Context: the current `osp` mode in `src/util_da.py` labels the iterative DA interface as "OSP" but the game form is standard DA with simultaneous round-by-round proposals. Agents are asked for their favorite school in the full remaining set (`da_osp_choice.txt`), with no guaranteed fallback. That requires contingent beliefs about other students and fails Li (2017) obviousness and the Ashlagi–Gonczarowski (2018) tree for acyclic priorities. This note spells out what must change in the harness and prompts so the simulation really implements an OSP mechanism.

## Evidence that the current code is not OSP
- **Parallel queries:** `DA_OSP._run_one_osp_round` queries *all* unmatched students each round and then runs the standard DA step. Each student must forecast whether others will bid for the same school; this is not obviously dominant.
- **Choice set is not a guaranteed menu:** The prompt (`rule_template/DA/da_osp_choice.txt`) shows the entire remaining set. A student with high value for a school where she has low priority might gamble on it and be rejected later. The worst outcome under the truthful action can be strictly worse than the best outcome under a deviation, so Li's obvious-dominance test fails.
- **No acyclic-specific tree:** Ashlagi–Gonczarowski show OSP only under acyclic priorities and give a specific decision tree (serial dictatorship if one top-ranked student; otherwise a/b trees when two students are top-ranked). The implementation does not follow that tree and would not be OSP even under acyclic priorities.

## Minimal OSP spec for the acyclic priorities used in this repo
Assume the fixed Ergin-acyclic priorities already in the code (A/B top; C/D bottom):

- If only one student has top priority at some remaining school, the mechanism collapses to a serial dictatorship: ask that student to pick her favorite remaining school; assign; recurse.
- If two students (call them a and b) are top-ranked across the remaining schools (the only acyclic case with 4×4), use the Ashlagi–Gonczarowski tree:
  1) For each school where **a** has priority 1, ask a **yes/no** question: “Do you want to take w now?” If YES → assign w to a, remove w and a, recurse. If NO → w stays available and we continue down the tree.
  2) If a declined all of her priority‑1 schools, do the symmetric loop for **b** over the schools where b has priority 1.
  3) If neither loop yields an assignment, ask a for her top remaining school, assign it; then ask b for his top remaining school from what is left; recurse on the remaining students/schools.
- Every query has a deterministic guarantee that makes truthful play obvious: answering YES yields an immediate match to w; answering NO forfeits w forever but cannot make the student worse off than getting w when w is not her top choice.

## Harness changes (what to code)
1) **Replace the round-based loop** in `DA_OSP.run` with a recursive `run_osp_tree(state)` that follows the spec above and queries *one student at a time*.
2) **Maintain explicit menus (“budgets”)** in state: for each query, compute `guaranteed_if_yes` and `guaranteed_if_no` (fallback set) and pass them to the prompt so the worst/best comparisons are transparent (the “obviousness witness” Li uses).
3) **Use the guaranteed yes/no prompt**, not the full choice list. Point to `rule_template/DA/da_osp_yesno_guaranteed.txt` so each node is a binary decision about a single school with its guarantee.
4) **Keep DA as the fallback allocator** for students without remaining priority‑1 claims: once the top‑priority students are assigned, run the ordinary DA among the rest (or continue the recursion; both are fine because obviousness has already been resolved for the queried students).
5) **Truthfulness metric:** Redefine `DA_OSP._compute_osp_truthfulness` to check whether each response matches the obvious action at that node (YES iff the queried school is the student’s top among remaining when asked; NO otherwise) instead of comparing to ex‑post utilities.

## Prompt changes
Use `rule_template/DA/da_osp_yesno_guaranteed.txt`, which exposes the guarantee and fallback set at each node. Required variables (all currently in the template): `student_id`, `remaining_set`, `candidate`, `fallback_set`, `preference_order`, `pw/px/py/pz`, `global_ranking`. This matches the house style of the other DA templates.

🔴 Bug we fixed: previously the prompt said NO “gives up the candidate forever.” That is *not* the AG mechanism and destroys OSP. The correct text now says NO “keeps all remaining schools (including the candidate).” The code must pass `fallback_set = remaining_schools` so the candidate stays available after NO. Only an actual acceptance removes a school.

If you hit a serial-dictatorship node (only one student has top priority everywhere), you may ask that student for her top remaining school in one shot; that is OSP. You can reuse the existing `da_osp_choice.txt` or a stripped-down one-line “Choice: <school>” prompt for that single-agent pick. Do **not** use the full-set choice prompt for the general two-top-student case; it breaks obviousness.

## Offer order and multiple-available schools (what happens with many options?)
- Obviousness requires single-school offers in a fixed, public order derived from priorities, not a free-choice menu. When a student could be admitted to multiple schools, the mechanism still asks about one school at a time, with “take now or give it up forever” guarantees. This is exactly the Ashlagi–Gonczarowski construction.
- Order to use (acyclic case with 4 students, 4 schools):
  1) Identify `top_by_school` = argmin-priority for each remaining school.
  2) Let `top_students` be the unique set of priority‑1 students. Acyclicity ⇒ |top_students| ≤ 2.
  3) If |top_students| = 1: serial dictatorship for that student (pick top remaining school once).
  4) If |top_students| = 2 with students a, b: iterate the schools where a has priority 1 in a fixed order (e.g., alphabetical by school label) with the yes/no prompt; if none taken, iterate b’s priority‑1 schools in the same fixed order; if still none taken, ask a for her top remaining school, assign; then ask b for his top remaining school from what is left.
- The fallback set shown in the prompt is always `remaining_set - {candidate}` at that node. This provides the “obviousness witness”: if `candidate` is truly the student’s favorite among `remaining_set`, YES weakly dominates NO; otherwise NO weakly dominates YES.

## Quick pseudocode sketch

```
def run_osp_tree(students, schools, priorities):
    if not students: return matches

    top_by_school = {s: argmin_priority(students, s)}
    top_students = unique(top_by_school.values())

    if len(top_students) == 1:
        s_star = top_students[0]
        w = ask_pick_top(s_star, schools)  # multiple choice OK here
        assign(s_star, w); recurse(without s_star, schools - {w})
        return matches

    # len == 2 in the acyclic 4×4 case
    a, b = top_students
    for w in schools where top_by_school[w] == a:
        if ask_yes_no(a, w, fallback=schools - {w}):
            assign(a, w); return recurse(without a, schools - {w})

    for w in schools where top_by_school[w] == b:
        if ask_yes_no(b, w, fallback=schools - {w}):
            assign(b, w); return recurse(without b, schools - {w})

    w_a = ask_pick_top(a, schools)
    assign(a, w_a)
    w_b = ask_pick_top(b, schools - {w_a})
    assign(b, w_b)
    return recurse(without {a,b}, schools - {w_a, w_b})
```

This tree mirrors Ashlagi–Gonczarowski’s construction and is OSP for any acyclic priority profile. The harness should log each node with the `fallback_set` used so we can audit obviousness ex post.

## What to tell the coauthor
- The “OSP” mode currently tested in the figures is not OSP; it is standard DA with a different UI. Any claims about OSP gains are therefore unsupported.
- Implement the tree above, switch to the guarantee-bearing yes/no prompts, and rerun the OSP experiments. Keep the non-OSP (direct) baseline unchanged for comparison.
- Document in the draft that OSP holds **only under the fixed acyclic priority profile**; if you randomize priorities, rerun the acyclicity check or fall back to the non-OSP label.
