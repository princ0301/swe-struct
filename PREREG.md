# Pre-registration (freeze before main runs; commit date = freeze date)

Status: DRAFT

## Research questions
RQ1 Adoption of optional structural tools vs model size (Gemma 4 family).
RQ2 Interaction of delivery mechanism with model size.
RQ3 Adoption and gain by hop distance.
RQ4 Do results hold on a second benchmark.

## Hypotheses
H1 Optional-tool adoption varies non-monotonically with size.
H2 Passive/forced delivery helps small sizes more than large sizes.
H3 Adoption is lowest on multi-hop tasks.

## Arms
A1 grep + file view only | A2 + optional graph tool | A3 A2 + end-of-prompt reminder
A4 forced first graph call | A5 passive injection | A6 random-edge control

## Metrics
Adoption rate, function-level localization (Recall@k), tokens, tool calls; resolve rate on a subset.

## Analysis plan
Paired by task, bootstrap CIs, mixed-effects logistic model. Report effect sizes.

## Stopping rule
No new runs after 2026-11-02.
