#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv, find_dotenv

# Use an existing .env (found from cwd or this file's dir upward), else create one next to main.py.
# CHARCLI_ENV can be set manually to force a location.
ENV_PATH = (os.environ.get("CHARCLI_ENV")
            or find_dotenv(usecwd=True)
            or find_dotenv()
            or os.path.join(os.path.dirname(os.path.realpath(__file__)), ".env"))
os.environ["CHARCLI_ENV"] = ENV_PATH
load_dotenv(ENV_PATH)

from menu_curses import run_menu_curses

def main():
    """Main entry point - runs ASCII TUI by default"""
    run_menu_curses()

if __name__ == "__main__":
    main()
