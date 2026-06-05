"""Entry point for the Edge Multi Profile application."""

import os
import sys

# Allow running directly from the project root (add src to sys.path)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from edge_multi.app import run  # noqa: E402


if __name__ == "__main__":
    run()
