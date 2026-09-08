"""Record one real adaptive-MPC landing as MP4 plus a README GIF preview."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess

import gymnasium as gym
from gymnasium.envs.box2d import lunar_lander as LL
import numpy as np

from lunar_mpc.environment import StartPose
from lunar_mpc.mpc import AdaptiveMPC, MPCConfig, landing_result


class Encoder:
    def __init__(self, output: Path, frame: np.ndarray):
        self.output = output
        self.output.parent.mkdir(parents=True, exist_ok=True)
        height, width = frame.shape[:2]
        self.process = subprocess.Popen([
            "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
            "-pixel_format", "rgb24", "-video_size", f"{width}x{height}",
            "-framerate", "50", "-i", "-", "-vf", "scale=720:-2:flags=lanczos",
            "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "23",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
        ], stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    def write(self, frame: np.ndarray) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(np.ascontiguousarray(frame, dtype=np.uint8).tobytes())

    def close(self) -> None:
        assert self.process.stdin is not None and self.process.stderr is not None
        self.process.stdin.close()
        error = self.process.stderr.read().decode()
        if self.process.wait():
            raise RuntimeError(error)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(self.output),
            "-vf", "fps=10,scale=480:-2:flags=lanczos,split[a][b];"
                   "[a]palettegen=max_colors=64[p];[b][p]paletteuse=dither=bayer",
            "-loop", "0", str(self.output.with_suffix(".gif")),
        ], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--thrust-scale", type=float, default=.7)
    parser.add_argument("--out", type=Path, default=Path("docs/showcase.mp4"))
    args = parser.parse_args()
    if not shutil.which("ffmpeg"):
        parser.error("ffmpeg is required to encode the showcase")
    if not 0 < args.thrust_scale <= 1:
        parser.error("thrust-scale must be in (0, 1]")

    env = StartPose(gym.make("LunarLander-v3", render_mode="rgb_array"), 6, .5)
    controller = AdaptiveMPC(MPCConfig())
    obs, _ = env.reset(seed=args.seed)
    first = env.render()
    encoder = Encoder(args.out, first)
    total = 0.0
    steps = 0
    try:
        encoder.write(first)
        terminated = truncated = False
        while not (terminated or truncated):
            action = controller.act(obs)
            original_power = LL.MAIN_ENGINE_POWER
            try:
                if steps >= 100:
                    LL.MAIN_ENGINE_POWER = original_power * args.thrust_scale
                nxt, reward, terminated, truncated, _ = env.step(action)
            finally:
                LL.MAIN_ENGINE_POWER = original_power
            controller.observe(obs, action, nxt)
            frame = env.render()
            encoder.write(frame)
            obs = nxt
            total += reward
            steps += 1
        for _ in range(25):
            encoder.write(frame)
        if not landing_result(env, terminated, truncated, obs)["passed"]:
            raise RuntimeError("seed did not pass the strict landing checks")
    finally:
        env.close()
        encoder.close()
    print(f"Recorded seed {args.seed}: return {total:.1f}, {steps} steps, "
          f"main-engine scale {args.thrust_scale:.0%}")
    print(f"Wrote {args.out} and {args.out.with_suffix('.gif')}")


if __name__ == "__main__":
    main()
