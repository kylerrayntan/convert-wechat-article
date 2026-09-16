#!/usr/bin/env python3
"""Run public synthetic regression without private documents or repository output."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", default="node", help="Node.js executable")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    skill = root / "convert-wechat-article"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    with tempfile.TemporaryDirectory(prefix="wechat-public-tests-") as directory:
        result = Path(directory) / "regression"
        subprocess.run([sys.executable, str(skill / "tests/regression.py"),
                        "--workdir", str(result), "--node", args.node],
                       check=True, env=env)
        for case in ("synthetic-a", "stress-200-result"):
            subprocess.run([args.node, str(skill / "tests/page_unit.cjs"),
                            str(result / case / "article.html")], check=True, env=env)
    print("PASS: public synthetic regression and mock-DOM clipboard tests")


if __name__ == "__main__":
    main()
