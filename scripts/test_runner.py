#!/usr/bin/env python3
"""
test_runner.py — Convenient pytest helper for common test scenarios.

This script provides simple commands for running tests with different profiles,
making it easier for developers to run the right tests for their workflow.

Usage:
    # Run all tests (default)
    uv run python scripts/test_runner.py

    # Run only unit tests (fastest, no PDFs needed)
    uv run python scripts/test_runner.py unit

    # Run BSP contract validation tests (no PDFs needed)
    uv run python scripts/test_runner.py contract

    # Run integration tests (needs anonymised PDFs; skips without them)
    uv run python scripts/test_runner.py integration

    # Run with verbose output
    uv run python scripts/test_runner.py unit -v

    # Run with coverage report
    uv run python scripts/test_runner.py unit --cov
"""

import argparse
import subprocess
import sys
from pathlib import Path


class Runner:
    """Helper for running pytest with profile-based filtering."""

    PROFILES = {
        "all": {
            "description": "Run all tests (integration tests skip without PDFs)",
            "paths": None,
            "marker": None,
        },
        "unit": {
            "description": "Run unit tests only (fast, no PDFs needed)",
            "paths": ["tests/unit/"],
            "marker": None,
        },
        "contract": {
            "description": "Run BSP contract validation tests (no PDFs needed)",
            "paths": ["tests/test_bsp_contract.py"],
            "marker": None,
        },
        "integration": {
            "description": "Run integration tests (needs anonymised PDFs; skips without them)",
            "paths": ["tests/test_integration.py"],
            "marker": None,
        },
    }

    def __init__(self) -> None:
        self.repo_root = Path(__file__).resolve().parent.parent

    def run(self, profile: str, extra_args: list[str]) -> int:
        """Run pytest with the specified profile and extra arguments.

        Args:
            profile: Profile name (unit, contract, integration, all)
            extra_args: Additional pytest arguments

        Returns:
            Exit code from pytest
        """
        if profile not in self.PROFILES:
            self._print_error(f"Unknown profile: {profile}")
            self._print_profiles()
            return 1

        config = self.PROFILES[profile]
        print(f"Profile: {config['description']}")
        print()

        cmd = ["pytest"]

        if config["paths"]:
            cmd.extend([str(self.repo_root / p) for p in config["paths"]])
        else:
            cmd.append(str(self.repo_root / "tests"))

        if config["marker"]:
            marker = str(config["marker"])
            cmd.extend(["-m", marker])

        cmd.extend(extra_args)

        print(f"Running: {' '.join(cmd)}")
        print("-" * 80)

        return subprocess.call(cmd)

    def _print_profiles(self) -> None:
        """Print available test profiles."""
        print("\nAvailable profiles:")
        print()
        for name, config in self.PROFILES.items():
            print(f"  {name:<20} {config['description']}")
        print()

    @staticmethod
    def _print_error(msg: str) -> None:
        """Print error message to stderr."""
        print(f"ERROR: {msg}", file=sys.stderr)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run tests with profile-based filtering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/test_runner.py                          # Run all tests
  uv run python scripts/test_runner.py unit -v                  # Verbose unit tests
  uv run python scripts/test_runner.py integration --tb=short   # Integration with short tracebacks
  uv run python scripts/test_runner.py all -k "test_parse"      # All tests matching pattern
        """,
    )

    runner = Runner()

    parser.add_argument(
        "profile",
        nargs="?",
        default="all",
        help=f"Test profile to run. Options: {', '.join(runner.PROFILES.keys())}",
    )

    parser.add_argument(
        "--profiles",
        action="store_true",
        help="Show available profiles and exit",
    )

    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to pytest (e.g., -v, --cov, -k pattern)",
    )

    args = parser.parse_args()

    if args.profiles:
        runner._print_profiles()
        return 0

    return runner.run(args.profile, args.pytest_args)


if __name__ == "__main__":
    sys.exit(main())
