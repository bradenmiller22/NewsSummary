# Fact-check feasibility test

From the proposal: can the checker (OpenAI) tell faithful summaries from ones
with planted errors?

**Setup**: 10 source/summary pairs from real GNews articles (150–300 words each).
4 summaries are faithful; 6 have a hand-planted error.

**Pass criteria**: checker flags ≥ 5 of 6 planted errors (recall > 80%) and
names the specific unsupported claim, not just "something is wrong".

**Fallback if it fails**: tighter checking prompt, or restrict summaries to
quoted sentences.

## How to run

1. Fill `pairs.json` with 10 entries (one example is included). For each
   errored pair, put the exact planted claim in `planted_error`; leave it
   `null` for faithful ones.
2. Set `OFFLINE_MODE=0` and `OPENAI_API_KEY` in `.env`.
3. Run from the repo root:

```bash
python experiments/factcheck_feasibility/run_test.py
```

Results print to the console and are saved to `results.json` for the report.
