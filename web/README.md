# Lunar Control Lab

Static HTML, CSS and Vanilla JavaScript. No npm, remote fonts, CDNs, browser-side
machine learning, or API. The canvas shows recorded decisions from the Python
controller, including the predicted path available at that precise step.

From the repository root:

```bash
uv run python scripts/record_demo.py
uv run python -m http.server 8765 --bind 127.0.0.1 --directory dist/web
```

Open http://127.0.0.1:8765/ and stop with Ctrl+C. Recording takes a few minutes
depending on the host. Once the four traces exist, `uv run python web/build.py`
rebuilds the assets without rerunning the simulation. No files are fetched from
the original RL repository, and no existing recordings are needed on a fresh clone.

`build.py` reads `dist/nominal.json`, `nominal-fixed.json`,
`fault-adaptive.json`, and `fault-fixed.json`, then writes `dist/web/`:

- Three static assets: `index.html`, `styles.css`, `app.js`.
- Four JSON files in `data/`, each containing eight episodes.
- Each episode contains starting pose, terrain, pad, strict result, final
  observation and the frames used for playback.
- Each frame contains observation `s`, action `a`, predicted positions `p`,
  main-engine estimates before/after the transition (`gain`/`nextGain`), and
  planning time `ms`. The final observation is separate from the last action.

The app assumes the default 50 Hz geometry, 1.28-second prediction horizon and
30% fault at step 100. Use `scripts/record_demo.py` to keep the recordings and
explanatory text consistent. Custom timing, faults or horizons require updating
the presentation as well as generating new data.

Native `fetch` and HTTP caching load the files. A request counter prevents
late responses from replacing newer selections. Restart, timeline scrubbing
and fault jumping share one reset function. The model chart only reveals
estimates available by the current playback time.

## Checks

```bash
node --check web/app.js
node web/app.test.cjs
```

The regression check uses Node's built-in tools and a minimal DOM to cover
controller explanations, request races, seed retention, playback, scrubbing and
failed-load recovery. It does not check canvas rendering. The builder validates
recorded frame counts and observation/action shapes.

For a visual check, jump to the fault, play to the final landing, scrub backward,
then change controller, scenario and seed. Verify that fixed-model estimates
stay at 18.0, the final frame shows the recorded terminal state, and the predicted
path disappears at the end. Check a narrow viewport as well as a desktop window.
Space toggles playback outside controls; native buttons, selects and timeline
support keyboard interaction. Reduced-motion preferences disable smooth scrolling.

## Drawing

`drawLander` is one chamfered-box lander shared byte for byte with lunar-laya and
lunar-mpc-laya. Its coordinates are in units of one eighth of the hull radius
with y pointing down; the scene's world frame is y up, so the lander is drawn in
screen pixels with the rotation reversed and the footpads land on the surface.
Recorded frames here are 20 ms apart, so playback needs no interpolation.
