"""Thin wrapper entry point that delegates to core/cli.py."""
from core.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
