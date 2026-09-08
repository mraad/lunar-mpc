"""Generate fresh demo recordings and build the static app. Run with uv."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    for name, flags in (
        ('nominal', []),
        ('nominal-fixed', ['--fixed-model']),
        ('fault-adaptive', ['--thrust-scale', '0.7']),
        ('fault-fixed', ['--thrust-scale', '0.7', '--fixed-model']),
    ):
        subprocess.run([sys.executable, '-m', 'lunar_mpc.mpc', '--episodes', '8',
                        '--seed', '0', '--out', f'dist/{name}.json', *flags],
                       cwd=ROOT, check=True)
    subprocess.run([sys.executable, 'web/build.py'], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
