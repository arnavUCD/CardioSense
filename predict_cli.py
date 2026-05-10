"""CLI entry point: run the model on a CSV/JSON file and print JSON output."""
from __future__ import annotations

import argparse
import json
import sys

from cardiosense.predict import predict_ecg


def main() -> int:
    p = argparse.ArgumentParser(description="CardioSense ML layer inference")
    p.add_argument("input", help="path to ECG CSV or JSON file")
    p.add_argument("--sample-rate", type=int, default=None,
                   help="sample rate of the input (overrides JSON 'sample_rate')")
    p.add_argument("--stride-seconds", type=float, default=5.0,
                   help="window stride in seconds (default 5)")
    args = p.parse_args()

    result = predict_ecg(args.input,
                         sample_rate=args.sample_rate,
                         stride_seconds=args.stride_seconds)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
