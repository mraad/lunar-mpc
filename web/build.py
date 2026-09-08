"""Copy the dependency-free app and compact existing MPC runs into dist/web."""
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "web"
RUNS = {"nominal-adaptive": "nominal", "nominal-fixed": "nominal-fixed",
        "fault-adaptive": "fault-adaptive", "fault-fixed": "fault-fixed"}


def rounded(values):
    return [round(float(x), 4) for x in values]


def compact(run):
    episodes = []
    for e in run["episodes"]:
        frames = [{"s": rounded(r["state"]), "a": r["action"],
                   "p": [rounded(p[:2]) for p in r["prediction"]],
                   "gain": round(r["model_before"][0], 4),
                   "nextGain": round(r["model"][0], 4), "ms": round(r["solve_ms"], 3)}
                  for r in e["records"]]
        assert frames and len(frames) == e["steps"]
        assert all(len(f["s"]) == 8 and f["a"] in range(4) for f in frames)
        episodes.append({"seed": e["seed"], "start": rounded(e["start"]),
                         "terrain": e["terrain"], "pad": e["helipad"],
                         "passed": e["passed"], "margin": round(e["pad_margin"], 4),
                         "final": rounded(e["final_state"]), "frames": frames})
    return {"changeStep": run["change_step"], "thrustScale": run["thrust_scale"],
            "sourceSha256": run["source_sha256"], "episodes": episodes}


def main():
    # Check all inputs first so a missing experiment cannot leave a partial build.
    datasets = {name: compact(json.loads((ROOT / "dist" / f"{source}.json").read_text()))
                for name, source in RUNS.items()}
    (OUTPUT / "data").mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "styles.css", "app.js"):
        shutil.copyfile(ROOT / "web" / name, OUTPUT / name)
    for name, data in datasets.items():
        path = OUTPUT / "data" / f"{name}.json"
        path.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False) + "\n")
        print(f"{name}: {len(data['episodes'])} episodes, {path.stat().st_size / 1024:.0f} KB")
    print(f"Built {OUTPUT}")


if __name__ == "__main__":
    main()
