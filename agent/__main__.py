"""Entry point:  python -m agent <command>"""
import sys

from agent.cli import main

if __name__ == "__main__":
    sys.exit(main())
