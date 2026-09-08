# Lunar MPC

**A lunar landing that learns its engine during flight.** Adaptive Model
Predictive Control (MPC), a small NumPy physics model, and a dependency-free
VanillaJS web application for exploring the decisions.

At every observation, the controller predicts short sequences of engine
commands, chooses a plan, and applies its first action. It then measures what
happened, updates its engine estimates, and plans again. There is no offline
policy training or checkpoint to download.

This is a standalone Python package with its own Git history and uv lockfile.
It needs neither the original research repository nor PyTorch. The browser app
uses only HTML, CSS, JavaScript, and locally generated JSON.

## Quick start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git.
Python 3.12 is selected by `.python-version`; uv can provision it if necessary.
Box2D may need a platform C/C++ compiler to build; SWIG is supplied through uv's
isolated build dependencies. On macOS, install Xcode Command Line Tools if a
compiler is missing. No GPU or Node packages are required.

```bash
git clone https://github.com/mraad/lunar-mpc.git
cd lunar-mpc
uv sync --locked
uv run python scripts/record_demo.py
uv run python -m http.server 8765 --bind 127.0.0.1 --directory dist/web
```

Open **http://127.0.0.1:8765/**. Stop the server with **Ctrl+C**. Recording runs
32 episodes on the CPU; allow a few minutes depending on the machine. The
script generates all four scenario/controller combinations, then builds the app.
Generated recordings, replays and logs stay in ignored `dist/`.

In the web app:

- Switch between normal flight and a 30% main-engine power loss at two seconds.
- Compare adaptive and fixed-model MPC across eight starting positions.
- Play, pause, change speed, scrub, or jump to the fault.
- See actual motion, the predicted path, engine estimates and terminal checks.

The browser replays actual recorded Python decisions. Switching a scenario
loads another experiment; it does not optimize or run new physics in JavaScript.
After recording, the static app has no network or Python dependency beyond
serving its local files. No external fonts, CDNs, API, npm or frontend build tool.

## Run the controller

```bash
uv run lunar-mpc --episodes 8 --seed 0 \
  --out dist/nominal.json --replay dist/nominal.html
uv run lunar-mpc --episodes 8 --seed 0 --thrust-scale 0.7 \
  --out dist/fault-adaptive.json --replay dist/fault-adaptive.html
uv run lunar-mpc --episodes 8 --seed 0 --thrust-scale 0.7 --fixed-model \
  --out dist/fault-fixed.json
uv run lunar-mpc --help
```

The single-file HTML replays open directly without a server. `--fixed-model`
disables learning while retaining replanning after every observation. The
evaluator introduces the fault; the controller never receives its timing or
the true power multiplier. Each episode starts with a fresh nominal model.

Defaults: 16 predicted action blocks, four physics steps per block, beam width
32. That is 1.28 seconds of foresight with a new command every 0.02 simulated
seconds. This is approximate **finite-control-set MPC with beam search**, not
a QP/MIQP solver and not an exhaustive search.

## Understand and extend it

| Document | Contents |
|---|---|
| [Adaptive MPC introduction](docs/adaptive-mpc.md) | MPC from first principles, online estimation, prediction equations, costs and search |
| [Evaluation](docs/evaluation.md) | Strict landing protocol, historical results, validation and reproduction |
| [Web application](web/README.md) | Assets, recording format, playback and browser checks |
| [Contributing](CONTRIBUTING.md) | Environment, source checks and research-change workflow |
| [Research TODO](TODO.md) | Recovery, deadlines, uncertainty, noise and MIQP experiments |

```text
src/lunar_mpc/mpc.py          controller, online model, evaluator and CLI
src/lunar_mpc/environment.py  starting pose and evaluator-only terrain helpers
src/lunar_mpc/mpc_replay.html single-file replay template
web/                         VanillaJS application, builder and regression check
scripts/record_demo.py       generate the four demo experiments and build
tests/                       controller and environment regression checks
docs/                        introductory and research documentation
```

The controller receives eight current state measurements plus its own running
parameter estimate. It does not read simulator bodies, terrain, future random
numbers, rewards, or an episode history. The evaluator can read simulator truth
to score landings and draw the replay. Adaptation needs prior assumptions and
observable engine response; one observation cannot identify arbitrary physics.

## Checks

```bash
uv lock --check --offline
uv run python -m unittest discover -s tests -v
node --check web/app.js
node web/app.test.cjs
```

Node is optional and used only for the JavaScript regression checks, which
need no packages. `uv run python scripts/record_demo.py` additionally exercises
all four controller/scenario paths and validates the generated web data.

## Research limits

Historical evaluation on seeds 200–249 passed 49/50 strict landing checks for
adaptive MPC under the engine fault versus 42/50 for fixed-model MPC; both
passed 49/50 normally. These pre-extraction measurements are described, with
their limitations, in [the evaluation notes](docs/evaluation.md).

A common horizontal-recovery failure, approximate leg/contact physics and
planning-time outliers remain. Soft penalties and bounded parameter estimates
do not certify safety. The simulator waits for each command, so a 50 Hz
simulation does not prove real-time deadline compliance. This project is a
research demonstration, not a flight-certified controller.

## License

[Apache-2.0](LICENSE). Copyright 2026 mraad. [NOTICE](NOTICE) records the source
attribution; no previous Git history or RL assets are included.
