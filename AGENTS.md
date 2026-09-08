# Repository instructions

- Use uv with the checked-in uv.lock. This is an independent project; never
  import, reference via PYTHONPATH, or share a virtual environment with lunar-rl.
- Keep the frontend in plain HTML, CSS and VanillaJS without external dependencies.
- Keep generated recordings, replays, logs, builds and caches under ignored dist/.
- Before committing, run the checks in CONTRIBUTING.md. For controller/evaluator
  changes also run a real episode; for web-data changes regenerate the demo.
- Distinguish replay from browser optimization and historical from fresh results.
- Preserve the observation-only controller boundary and report research limits.
- Bind local servers to 127.0.0.1. Do not open a browser or leave a server running
  unless requested. Stop a running server when asked.
