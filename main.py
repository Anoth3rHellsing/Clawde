#!/usr/bin/env python3
"""
Clawde - Desktop Companion Pet
Entry point. Run with: python main.py
"""

import sys
import os

# Ensure the package is importable when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clawde.app import ClawdeApp


def main():
    app = ClawdeApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()