#!/usr/bin/env python3
"""
CLI Script to execute the Agentic Workflow Trajectory Evaluation.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.trajectory_eval import run_trajectory_benchmark, print_trajectory_table


def main():
    print("Executing Autonomous SRE Remediation Agent Trajectory Benchmark...")
    report = run_trajectory_benchmark()
    print(print_trajectory_table(report))


if __name__ == "__main__":
    main()
