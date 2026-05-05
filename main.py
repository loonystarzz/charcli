#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from menu_curses import run_menu_curses

def main():
    """Main entry point - runs ASCII TUI by default"""
    run_menu_curses()

if __name__ == "__main__":
    main()
