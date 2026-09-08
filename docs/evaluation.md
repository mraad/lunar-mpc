# Evaluation and reproduction

## What counts as success

An episode passes only if it terminates without a crash or time limit, the
lander is asleep with both legs contacting the surface, and both rendered foot
endpoints lie between the pad flags. Accumulated reward and body-center position
alone are insufficient. Failed checks include one-leg settled states and off-pad
landings as well as crashes; report the actual category.

Every episode resets the online model. `StartPose` samples left/right offsets
with magnitude 2.4–6 world units and tilt magnitude 0.2–0.5 radians using the
environment's seeded random generator. The central target and observation scales
are fixed prior knowledge, not information learned from scratch.

The engine-fault experiment reduces main-engine power by 30% at action 100.
Neither timing nor multiplier is passed to the controller. The fixed model
receives exactly the same observations and action options but does not update
its parameters. Seeds 0–7 are development cases.

## Historical results

The pre-extraction controller was evaluated on 2026-09-08 using NumPy on an
Apple-silicon CPU, with Python 3.12, Gymnasium 1.3.0 and NumPy 2.5.2. These
measurements came from the original research worktree, not this repository's
initial test run. The extraction changes imports and package layout, not the
controller equations, costs, search or adaptation rules.

| Seeds | Scenario | Adaptive passes | Fixed passes |
|---|---|---:|---:|
| 0–7, development | Normal | 8/8 | 8/8 |
| 0–7, development | Engine fault | 8/8 | 6/8 |
| 200–249, evaluation | Normal | 49/50 | 49/50 |
| 200–249, evaluation | Engine fault | 49/50 | 42/50 |

All four evaluation configurations failed seed 235 by leaving the viewport
before the fault. Adaptation improved the strict fault-case landing count but
reduced mean reward and increased flight duration. It did not improve the
normal-flight pass count. The detailed [implementation guide](adaptive-mpc.md)
reports returns and model limitations. The original raw traces are not bundled.

Historical planning time was about 1.35 ms median, with outliers reaching
73.8 ms. This measures `act()` including trace construction, excluding estimation
and environment stepping. The simulation waits for commands; it does not model
missed deadlines or certify real-time operation.

## Reproduce the experiments

Generate the development demo from a clean installation:

```bash
uv sync --locked
uv run python scripts/record_demo.py
```

Reproduce the four evaluation configurations:

```bash
uv run lunar-mpc --seed 200 --episodes 50 --out dist/heldout-nominal-adaptive.json
uv run lunar-mpc --seed 200 --episodes 50 --fixed-model --out dist/heldout-nominal-fixed.json
uv run lunar-mpc --seed 200 --episodes 50 --thrust-scale 0.7 --out dist/heldout-fault-adaptive.json
uv run lunar-mpc --seed 200 --episodes 50 --thrust-scale 0.7 --fixed-model --out dist/heldout-fault-fixed.json
```

Each JSON contains configuration, a hash of `mpc.py`, all observations/actions,
predicted trajectories, online model estimates, final observations, strict
results, returns, foot margins and planning latency percentiles. Record the Git
commit, platform and lockfile alongside results: the single-file hash does not
identify the environment helpers or dependencies. Timing depends on host load;
seeded Box2D runs are not a cross-platform bitwise reproducibility guarantee.

Because seed 235 has already been identified, use fresh seeds/scenarios for
claims about later controller improvements. Reserve an untouched evaluation set
before tuning, and report compute deadlines and recovery failures alongside
landing counts. Parameter clipping and heuristic margins are not confidence
bounds or certified safety constraints.

## Standalone validation

The initial release is checked with a new uv environment, controller unit tests,
JavaScript regressions, a packaged CLI run and regeneration of all 32 development
flights. Generated evidence remains under local `dist/`; these checks do not
claim a new 200-episode research evaluation.

Validated on 2026-09-08 with Python 3.12.12, Gymnasium 1.3.0 and NumPy 2.5.2
in this repository’s own `.venv`. Eight Python tests and the JavaScript
regression check passed. Fresh development recordings produced:

| Recording | Strict passes | Mean return |
|---|---:|---:|
| nominal | 8/8 | +283.3 |
| nominal-fixed | 8/8 | +284.6 |
| fault-adaptive | 8/8 | +223.2 |
| fault-fixed | 6/8 | +275.4 |

The two fixed-model fault failures were settled one-leg contacts, not crashes.
The standalone wheel and source distribution were built and checked to include
the replay template and exclude environments, caches and generated traces.
