'use strict';

const $ = id => document.getElementById(id);
const scene = $('scene'), chart = $('model-chart');
const ctx = scene.getContext('2d'), graph = chart.getContext('2d');
const names = ['Coast', 'Left thruster', 'Main engine', 'Right thruster'];
const playbackControls = ['play', 'restart', 'timeline', 'seed', 'jump'].map($);
let scenario = 'fault', controller = 'adaptive', data = null, flight = null;
let index = 0, playing = false, lastTime = 0, fraction = 0, request = 0;
let sceneSize = [0, 0], chartSize = [0, 0];

function physical(s) { return [s[0] * 10, s[1] * 20 / 3, s[2] * 5, s[3] * 7.5, s[4], s[5] * 2.5]; }
function seconds(step) { return (step / 50).toFixed(2).padStart(5, '0'); }
function pause() { playing = false; updatePlay(); }
function updatePlay() {
  $('play-icon').textContent = playing ? 'Ⅱ' : '▶';
  $('play-label').textContent = playing ? 'Pause descent' : index === 0 ? 'Start descent' : flight && index === flight.frames.length ? 'Replay descent' : 'Resume descent';
  $('play').setAttribute('aria-label', playing ? 'Pause replay' : 'Play replay');
}
function togglePlay() {
  if (!flight) return;
  if (index === flight.frames.length) index = 0;
  playing = !playing; lastTime = 0; fraction = 0;
  render();
}
function seek(step) {
  pause(); index = step; fraction = 0;
  render();
}
function selectFlight(seed) {
  flight = data.episodes.find(e => e.seed === Number(seed)) || data.episodes[0];
  $('seed').value = flight.seed;
  $('timeline').max = flight.frames.length;
  $('duration').textContent = seconds(flight.frames.length);
  const faultPercent = data.changeStep / flight.frames.length * 100;
  const hasFault = scenario === 'fault' && data.changeStep < flight.frames.length;
  for (const id of ['fault-label', 'fault-marker', 'jump']) $(id).hidden = !hasFault;
  $('fault-marker').style.left = `${faultPercent}%`;
  $('fault-label').style.left = `${Math.max(14, Math.min(83, faultPercent))}%`;
  $('fault-label').textContent = `ENGINE FAULT · ${seconds(data.changeStep)}`;
  $('load-status').textContent = `Seed ${String(flight.seed).padStart(2, '0')} · ${controller === 'adaptive' ? 'Adaptive' : 'Fixed-model'} MPC · Recorded decisions at 50 Hz`;
  $('episode-result').textContent = flight.passed ? `Episode result: PASS · foot margin ${flight.margin.toFixed(2)} u` : 'Episode result: FAIL · strict landing checks';
  $('episode-result').className = flight.passed ? 'pass' : 'fail';
  seek(0);
}
async function load() {
  const ticket = ++request, oldSeed = $('seed').value;
  pause(); data = null; flight = null;
  for (const control of playbackControls) control.disabled = true;
  $('load-status').textContent = 'Loading recorded flight…';
  $('episode-result').textContent = '';
  document.querySelectorAll('[data-scenario]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.scenario === scenario)));
  document.querySelectorAll('[data-controller]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.controller === controller)));
  $('model-mode').textContent = controller === 'adaptive' ? 'ADAPTING' : 'FIXED MODEL';
  $('model-copy').textContent = controller === 'adaptive'
    ? 'The controller compares expected motion with what actually happened, then updates its engine estimate.'
    : 'The controller replans from each new observation, while keeping its original estimate of engine strength.';
  render();
  try {
    const response = await fetch(`data/${scenario}-${controller}.json`);
    if (!response.ok) throw new Error(`Flight request failed: ${response.status}`);
    const result = await response.json();
    if (ticket !== request) return;
    if (!result.episodes?.length) throw new Error('No recorded episodes');
    data = result;
    $('seed').replaceChildren(...data.episodes.map(e => {
      const option = document.createElement('option');
      option.value = e.seed;
      option.textContent = `Seed ${String(e.seed).padStart(2, '0')} · ${e.start[0] > 0 ? 'right' : 'left'}`;
      return option;
    }));
    selectFlight(oldSeed);
    for (const control of playbackControls) control.disabled = false;
  } catch (error) {
    if (ticket !== request) return;
    $('flight-phase').textContent = 'Flight unavailable';
    $('load-status').textContent = 'Flight data could not be loaded. Reload the page to try again.';
    console.error(error);
  }
}

function drawScene(state, frame, terminal) {
  const [w, h] = sceneSize;
  if (!w || !h) return;
  ctx.clearRect(0, 0, w, h);
  const sky = ctx.createRadialGradient(w * .58, h * .58, 0, w * .58, h * .58, w * .65);
  sky.addColorStop(0, '#173239'); sky.addColorStop(1, '#0a1820');
  ctx.fillStyle = sky; ctx.fillRect(0, 0, w, h);
  for (let n = 0; n < 62; n++) {
    const rx = (Math.sin(n * 127.1 + 5) * 43758.5453) % 1;
    const ry = (Math.sin(n * 311.7 + 9) * 17932.1921) % 1;
    ctx.fillStyle = `rgba(184,214,212,${.12 + (n % 4) * .06})`;
    ctx.fillRect(Math.abs(rx) * w, Math.abs(ry) * h * .8, n % 7 === 0 ? 1.5 : 1, 1);
  }
  const unit = Math.min(w / 23, (h - 64) / 11.5);
  const X = x => w / 2 + x * unit, Y = y => h - 66 - y * unit;
  ctx.lineWidth = .5; ctx.strokeStyle = '#76999612'; ctx.setLineDash([2, 6]);
  for (let x = -30; x <= 30; x += 2) { ctx.beginPath(); ctx.moveTo(X(x), 0); ctx.lineTo(X(x), h); ctx.stroke(); }
  for (let y = 0; y <= 12; y += 2) { ctx.beginPath(); ctx.moveTo(0, Y(y)); ctx.lineTo(w, Y(y)); ctx.stroke(); }
  ctx.setLineDash([]);
  if (!flight || !state) return;
  const terrain = flight.terrain.map(p => [X(p[0] - 10), Y(p[1] - flight.pad[2] - .6)]);
  const ground = ctx.createLinearGradient(0, h - 100, 0, h);
  ground.addColorStop(0, '#233a3d'); ground.addColorStop(1, '#13262d');
  ctx.beginPath(); ctx.moveTo(0, terrain[0][1]);
  terrain.forEach(p => ctx.lineTo(...p));
  ctx.lineTo(w, terrain.at(-1)[1]); ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.closePath();
  ctx.fillStyle = ground; ctx.fill();
  ctx.beginPath(); ctx.moveTo(0, terrain[0][1]); terrain.forEach(p => ctx.lineTo(...p)); ctx.lineTo(w, terrain.at(-1)[1]);
  ctx.strokeStyle = '#547776'; ctx.lineWidth = 1; ctx.stroke();
  const padY = Y(-.6), left = X(flight.pad[0] - 10), right = X(flight.pad[1] - 10);
  ctx.shadowBlur = 13; ctx.shadowColor = '#a9e8d066'; ctx.strokeStyle = '#a9e8d0'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(left, padY); ctx.lineTo(right, padY); ctx.stroke(); ctx.shadowBlur = 0;
  for (const x of [left, right]) {
    ctx.strokeStyle = '#b5c9b7'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x, padY); ctx.lineTo(x, padY - 16); ctx.stroke();
    ctx.fillStyle = '#b5c9b7'; ctx.beginPath(); ctx.moveTo(x, padY - 16); ctx.lineTo(x + 8, padY - 13); ctx.lineTo(x, padY - 9); ctx.fill();
  }
  ctx.font = '8px ui-monospace, monospace'; ctx.fillStyle = '#71918d'; ctx.textAlign = 'center';
  ctx.fillText('LANDING ZONE', w / 2, padY + 18);
  const entry = physical(flight.frames[0].s);
  ctx.strokeStyle = '#66868166'; ctx.setLineDash([2, 5]); ctx.beginPath(); ctx.moveTo(X(entry[0]), Y(entry[1]) + 9); ctx.lineTo(X(entry[0]), Y(-.6)); ctx.stroke(); ctx.setLineDash([]);
  ctx.beginPath(); ctx.arc(X(entry[0]), Y(entry[1]), 5, 0, Math.PI * 2); ctx.stroke();
  ctx.textAlign = 'left'; ctx.fillText('ENTRY', X(entry[0]) + 11, Y(entry[1]) + 3);
  ctx.strokeStyle = '#a9e8d0aa'; ctx.lineWidth = 1.4; ctx.beginPath();
  for (let i = 0; i <= index && i < flight.frames.length; i++) {
    const p = physical(flight.frames[i].s); i ? ctx.lineTo(X(p[0]), Y(p[1])) : ctx.moveTo(X(p[0]), Y(p[1]));
  }
  if (terminal) ctx.lineTo(X(state[0]), Y(state[1]));
  ctx.stroke();
  if (!terminal && frame.p.length > 1) {
    ctx.setLineDash([4, 5]); ctx.strokeStyle = '#eaba7d'; ctx.lineWidth = 1.7; ctx.beginPath();
    frame.p.forEach((p, i) => i ? ctx.lineTo(X(p[0]), Y(p[1])) : ctx.moveTo(X(p[0]), Y(p[1]))); ctx.stroke(); ctx.setLineDash([]);
    const end = frame.p.at(-1); ctx.beginPath(); ctx.arc(X(end[0]), Y(end[1]), 4, 0, Math.PI * 2); ctx.strokeStyle = '#eaba7d99'; ctx.stroke();
  }
  ctx.save(); ctx.translate(X(state[0]), Y(state[1])); ctx.scale(unit, -unit); ctx.rotate(state[4]);
  if (!terminal && frame.a !== 0) {
    ctx.fillStyle = '#f2c17b'; ctx.shadowColor = '#eaba7d'; ctx.shadowBlur = 15;
    ctx.beginPath();
    if (frame.a === 2) { ctx.moveTo(-.16, -.34); ctx.lineTo(.16, -.34); ctx.lineTo(0, -(.83 + .16 * Math.sin(index * 1.7))); }
    else { const sign = frame.a === 1 ? -1 : 1; ctx.moveTo(sign * .5, .13); ctx.lineTo(sign * .5, -.04); ctx.lineTo(sign * .95, .045); }
    ctx.closePath(); ctx.fill(); ctx.shadowBlur = 0;
  }
  ctx.beginPath(); [[-.47,.57],[-.57,0],[-.57,-.33],[.57,-.33],[.57,0],[.47,.57]].forEach((p, i) => i ? ctx.lineTo(...p) : ctx.moveTo(...p)); ctx.closePath();
  ctx.fillStyle = '#d6e6de'; ctx.fill(); ctx.strokeStyle = '#f0f5eb'; ctx.lineWidth = 1 / unit; ctx.stroke();
  ctx.fillStyle = '#3a6265'; ctx.fillRect(-.18, .12, .36, .24);
  ctx.strokeStyle = '#b1d8c6'; ctx.lineWidth = 1.4 / unit;
  for (const sign of [-1, 1]) { ctx.beginPath(); ctx.moveTo(sign * .33, -.24); ctx.lineTo(sign * 2 / 3, -.6); ctx.stroke(); }
  ctx.restore();
  ctx.strokeStyle = '#a4c7c066'; ctx.lineWidth = .7; ctx.beginPath(); ctx.moveTo(X(state[0]) + 13, Y(state[1]) - 5); ctx.lineTo(X(state[0]) + 25, Y(state[1]) - 17); ctx.lineTo(X(state[0]) + 66, Y(state[1]) - 17); ctx.stroke();
  ctx.fillStyle = '#b6d0c7'; ctx.font = '7px ui-monospace,monospace'; ctx.fillText('LANDER', X(state[0]) + 28, Y(state[1]) - 22);
}

function drawModel(gain) {
  const [w, h] = chartSize;
  graph.clearRect(0, 0, w, h);
  if (!flight || !w) return;
  const X = k => 24 + k / flight.frames.length * (w - 29);
  const Y = v => h - 12 - (v - 5) / 30 * (h - 17);
  graph.font = '7px ui-monospace,monospace'; graph.textAlign = 'left';
  for (const v of [10, 20, 30]) {
    graph.fillStyle = '#668683'; graph.fillText(String(v), 0, Y(v) + 3);
    graph.strokeStyle = '#49676233'; graph.lineWidth = .5; graph.beginPath(); graph.moveTo(22, Y(v)); graph.lineTo(w, Y(v)); graph.stroke();
  }
  graph.setLineDash([3, 4]); graph.strokeStyle = '#7da19566'; graph.beginPath(); graph.moveTo(24, Y(18)); graph.lineTo(w, Y(18)); graph.stroke(); graph.setLineDash([]);
  if (scenario === 'fault') {
    graph.strokeStyle = '#eaba7d55'; graph.setLineDash([2, 3]); graph.beginPath(); graph.moveTo(X(data.changeStep), 2); graph.lineTo(X(data.changeStep), h); graph.stroke(); graph.setLineDash([]);
  }
  // Only reveal estimates available by this recorded step; don't leak the future.
  graph.beginPath(); graph.moveTo(X(0), Y(18));
  for (let k = 0; k < Math.min(index, flight.frames.length); k++) graph.lineTo(X(k + 1), Y(flight.frames[k].nextGain));
  graph.strokeStyle = '#a9e8d0'; graph.lineWidth = 1.5; graph.stroke();
  graph.lineTo(X(index), h - 4); graph.lineTo(X(0), h - 4); graph.closePath();
  const fill = graph.createLinearGradient(0, 0, 0, h); fill.addColorStop(0, '#a9e8d022'); fill.addColorStop(1, '#a9e8d000'); graph.fillStyle = fill; graph.fill();
  graph.beginPath(); graph.arc(X(index), Y(gain), 2.7, 0, Math.PI * 2); graph.fillStyle = '#b5eed3'; graph.fill();
}

function render() {
  if (!flight) {
    for (const id of ['height', 'velocity', 'angle', 'action', 'plan-time', 'gain-value', 'gain-change', 'mission-time', 'elapsed', 'duration']) $(id).textContent = '—';
    $('flight-phase').textContent = 'Loading recorded flight…';
    $('flight-phase').classList.toggle('fault', false);
    $('insight-title').textContent = 'Choose a recorded flight.';
    $('insight-copy').textContent = '';
    drawScene(null, null, false); graph.clearRect(0, 0, ...chartSize);
    return;
  }
  const terminal = index === flight.frames.length;
  const frame = flight.frames[Math.min(index, flight.frames.length - 1)];
  const observation = terminal ? flight.final : frame.s, state = physical(observation);
  const gain = terminal ? frame.nextGain : frame.gain;
  $('height').textContent = state[1].toFixed(2); $('velocity').textContent = state[3].toFixed(2);
  $('angle').textContent = (state[4] * 180 / Math.PI).toFixed(1) + '°';
  $('action').textContent = terminal ? 'Flight ended' : names[frame.a];
  $('plan-time').textContent = terminal ? 'Final recorded state' : `plan computed in ${frame.ms.toFixed(2)} ms`;
  $('mission-time').textContent = `T + ${seconds(index)} s`;
  $('elapsed').textContent = seconds(index); $('timeline').value = index;
  $('timeline').style.setProperty('--progress', `${index / flight.frames.length * 100}%`);
  $('timeline').setAttribute('aria-valuetext', `${(index / 50).toFixed(2)} seconds of ${(flight.frames.length / 50).toFixed(2)}`);
  $('gain-value').textContent = gain.toFixed(1);
  const change = (gain / 18 - 1) * 100;
  $('gain-change').textContent = Math.abs(change) < .5 ? 'INITIAL ESTIMATE' : `${change > 0 ? '+' : '−'}${Math.abs(change).toFixed(0)}% VS INITIAL`;
  const fault = scenario === 'fault' && index >= data.changeStep;
  const contact = observation[6] || observation[7];
  const phase = terminal ? (flight.passed ? 'Landing verified' : 'Landing checks failed') : contact ? 'Touchdown · settling' : fault ? 'Main-engine power reduced by 30%' : index === 0 ? 'Ready for descent' : 'Replanning every 20 ms';
  $('flight-phase').textContent = phase; $('flight-phase').classList.toggle('fault', fault && !contact && !terminal);
  let title, copy;
  if (terminal) { title = flight.passed ? 'A landing, checked.' : 'A limit worth investigating.'; copy = flight.passed ? 'Both legs are in contact, the body has settled, and both rendered feet are inside the pad.' : 'This episode did not meet every terminal landing check. A high reward alone does not establish a successful landing.'; }
  else if (scenario === 'nominal') { title = 'A steady engine. A useful baseline.'; copy = controller === 'adaptive' ? 'There is no scheduled fault. Small model changes reflect measured motion and the simulator’s engine dispersion.' : 'The initial physics estimate stays fixed. New observations still change the next plan.'; }
  else if (!fault) { title = 'A change is coming.'; copy = 'At 2 seconds, the main engine drops to 70% power. The controller won’t be told.'; }
  else if (controller === 'fixed') { title = 'The world changed. The estimate didn’t.'; copy = 'The planner sees the latest position and velocity, but still predicts with the original engine strength.'; }
  else { title = 'Less thrust. A revised model.'; copy = 'Measured velocity changes update the engine estimate. The next plan uses that estimate to reconsider descent and braking.'; }
  if ($('insight-title').textContent !== title) $('insight-title').textContent = title;
  if ($('insight-copy').textContent !== copy) $('insight-copy').textContent = copy;
  drawScene(state, frame, terminal); drawModel(gain); updatePlay();
}

document.querySelectorAll('[data-scenario]').forEach(b => b.addEventListener('click', () => { if (scenario !== b.dataset.scenario) { scenario = b.dataset.scenario; load(); } }));
document.querySelectorAll('[data-controller]').forEach(b => b.addEventListener('click', () => { if (controller !== b.dataset.controller) { controller = b.dataset.controller; load(); } }));
$('seed').addEventListener('change', () => selectFlight($('seed').value));
$('play').addEventListener('click', togglePlay);
$('restart').addEventListener('click', () => seek(0));
$('timeline').addEventListener('input', () => seek(Number($('timeline').value)));
$('jump').addEventListener('click', () => seek(Math.min(data.changeStep, flight.frames.length)));
document.addEventListener('keydown', e => { if (e.code === 'Space' && !e.target.closest('button,input,select,summary,a')) { e.preventDefault(); togglePlay(); } });
document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
const resize = new ResizeObserver(entries => {
  for (const entry of entries) {
    const canvas = entry.target, { width, height } = entry.contentRect;
    const ratio = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
    canvas.getContext('2d').setTransform(ratio, 0, 0, ratio, 0, 0);
    if (canvas === scene) sceneSize = [width, height]; else chartSize = [width, height];
  }
  render();
});
resize.observe(scene); resize.observe(chart);
function animate(now) {
  if (playing && flight && lastTime) {
    fraction += Math.min(now - lastTime, 250) / 1000 * 50 * Number($('speed').value);
    const frames = Math.floor(fraction);
    if (frames) { fraction -= frames; index = Math.min(flight.frames.length, index + frames); if (index === flight.frames.length) pause(); render(); }
  }
  lastTime = now;
  requestAnimationFrame(animate);
}
load(); requestAnimationFrame(animate);
