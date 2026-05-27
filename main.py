"""Legacy entry point. Use `python -m config_sync` or `config-sync` CLI instead."""

import sys
import os

# Ensure the src directory is on the path for direct execution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from config_sync.cli import main

if __name__ == "__main__":
    main()
