# Contributing

Use `uv sync --locked` and the checked-in `uv.lock`. Python dependencies are
Gymnasium with Box2D and NumPy. Keep the controller independent of PyTorch and
the original research repository. Do not add a frontend package manager.

Before committing:

```bash
uv lock --check --offline
uv run python -m unittest discover -s tests -v
node --check web/app.js
node web/app.test.cjs
git diff --check
```

For evaluator or packaging changes, run a real episode and produce a replay:

```bash
uv run lunar-mpc --episodes 1 --seed 0 --thrust-scale 0.7 \
  --out dist/smoke.json --replay dist/smoke.html
```

For web or trace-format changes, run `uv run python scripts/record_demo.py` and
the [visual checks](web/README.md). Keep generated replays, logs and recordings
under ignored `dist/`. Never commit virtual environments or secrets.

For controller changes, compare adaptive and fixed models on identical seeds,
actuator rules, faults and compute budgets. Record the configuration and source
hash, strict landing counts, failure categories and latency distribution. Do
not present seeds used for tuning as a fresh evaluation set. See
[the evaluation protocol](docs/evaluation.md) and [research TODO](TODO.md).

The current fault injector temporarily changes a process-local Gymnasium
constant. Run one environment at a time per process, or use separate processes.
Do not introduce hidden simulator state into the controller's action interface.
