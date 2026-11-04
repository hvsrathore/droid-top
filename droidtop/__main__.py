"""
DroidTop - Command Line Entry Point.
"""

import sys
import argparse
from .app import DroidTopApp
from .themes.palette import THEMES


def main():
    parser = argparse.ArgumentParser(
        prog="droidtop",
        description="DroidTop - A btop-like modern TUI resource monitor for Android & Termux.",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"droidtop {DroidTopApp.VERSION}",
    )
    parser.add_argument(
        "-t", "--theme",
        choices=list(THEMES.keys()),
        help=f"Color theme to use (available: {', '.join(THEMES.keys())})",
    )
    parser.add_argument(
        "-r", "--rate",
        type=float,
        help="Update refresh rate in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--view",
        choices=["overview", "cpu", "memory", "power", "thermal", "proc"],
        help="Starting view tab (default: overview)",
    )

    args = parser.parse_args()

    app = DroidTopApp()

    if args.theme:
        app.theme = THEMES[args.theme]
        app.config.set("theme", args.theme)

    if args.rate and args.rate > 0.1:
        app.refresh_interval = args.rate
        app.config.set("refresh_rate", args.rate)

    if args.view:
        view_map = {
            "overview": 0,
            "cpu": 1,
            "memory": 2,
            "power": 3,
            "thermal": 4,
            "proc": 5,
        }
        app.active_view_idx = view_map.get(args.view, 0)

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n[droidtop error] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
