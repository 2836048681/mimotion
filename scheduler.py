import sys

from app_core import scheduler_tick


if __name__ == "__main__":
    try:
        print(scheduler_tick())
    except Exception as exc:
        print(f"scheduler error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
