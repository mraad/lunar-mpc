# Adaptive MPC research TODO

- [x] Implement discrete predictive control using a small airborne dynamics model.
- [x] Update engine gains and acceleration biases from observed transitions.
- [x] Keep fixed-model control as an ablation under identical actuator rules.
- [x] Add an unannounced mid-flight engine-power reduction in the evaluator.
- [x] Score termination, both leg contacts and rendered foot positions explicitly.
- [x] Record plans, parameter estimates, final state, impact diagnostics and latency.
- [x] Write an introductory guide and self-contained interactive replay.
- [x] Build a dependency-free VanillaJS control lab with recorded adaptive/fixed
  comparisons, fault/normal scenarios, playback, scrubbing and model estimates.
- [x] Review the web app: fix stale explanations and seed loss during overlapping
  loads; clear stale telemetry on errors and add a dependency-free regression check.
- [x] Simplify loading, playback resets and engine-estimate DOM updates.
- [x] Run focused tests, source checks and four 50-seed evaluation configurations.
- [ ] Investigate seed 235's horizontal boundary exit. Treat it as development
  data after investigation and use new seeds for the next reported evaluation.
- [ ] Add viewport/recovery constraints with an explicit infeasibility strategy.
- [ ] Enforce execution deadlines, validate a backup controller and include delay
  in the plant simulation; observed planning-time outliers exceed 20 ms.
- [ ] Replace hand-selected margins with justified uncertainty bounds and
  validated terminal conditions before making safety claims.
- [ ] Add sensor-noise, delayed-observation and changing-disturbance scenarios.
- [ ] Compare with an independently validated RL baseline using identical observations and scenarios.
- [ ] Evaluate MIQP as a separate search formulation with the same observations,
  actuator rules, disturbance scenarios and compute budget.
