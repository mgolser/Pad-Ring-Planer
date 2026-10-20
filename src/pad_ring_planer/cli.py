"""Command line entry point. Without a subcommand the GUI starts.

    pad-ring-planer [PROJECT]
    pad-ring-planer export PROJECT [--csv FILE] [--svg FILE]
"""

import argparse
import sys

from . import APP_NAME, __version__, export_csv, export_svg, load


def _export(argv):
    ap = argparse.ArgumentParser(prog="pad-ring-planer export", description="Export a project without the GUI.")
    ap.add_argument("project", help="project file (.json)")
    ap.add_argument("--csv", metavar="FILE", help="write the pin list as CSV")
    ap.add_argument("--svg", metavar="FILE", help="write the drawing as SVG")
    args = ap.parse_args(argv)
    if not (args.csv or args.svg):
        ap.error("nothing to export, give --csv and/or --svg")
    try:
        project = load(args.project)
        if args.csv:
            export_csv(project, args.csv)
        if args.svg:
            export_svg(project, args.svg)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    for w in project.layout().warnings:
        print(f"warning: {w}", file=sys.stderr)
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] == "export":
        return _export(argv[1:])
    ap = argparse.ArgumentParser(prog="pad-ring-planer", description=f"{APP_NAME}: plan IC pad ring pinouts.",
                                 epilog="Subcommand: 'pad-ring-planer export -h' for exports without the GUI.")
    ap.add_argument("project", nargs="?", help="project file (.json) to open")
    ap.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    args = ap.parse_args(argv)
    try:
        from .gui import run
    except ImportError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return run(args.project)


if __name__ == "__main__":
    sys.exit(main())
