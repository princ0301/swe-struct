# STATE (paste this at the start of every new chat)

Updated: 2026-10-03

## Project
Paper Track: Gemma 4 Developer Agent. Deadline 2026-11-12 23:59 UTC (target submit 2026-11-10). 3,000 words max.

## Question
How do delivery mechanism (optional / reminded / forced / passive) and model size (Gemma 4 E4B, 26B-A4B, 31B)
determine whether small local agents use, and benefit from, code-graph tools?

## Status
- [ ] Repo created and pushed
- [ ] Writeup created on Kaggle (ties go to earliest entry)
- [ ] Environment check passes (scripts/check_env.py)
- [ ] Kaggle feasibility notebook run (E4B)

## Decisions
See DECISIONS.md

## Open questions
- Does 4x L4 drain Kaggle quota 4x faster?
- Kaggle disk size / weight caching
- 26B and 31B QAT repo ids
- Modal support in SWE-bench harness
- Second benchmark: license and contamination

## Next 3 tasks
1. Finish setup
2. Create the Kaggle Writeup
3. Build core types, log schema, Backend/Tool protocols, mock backend (assistant writes, user runs)
