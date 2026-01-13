#!/usr/bin/env python
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
APPS_DIR = SRC_DIR / "apps"

sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(APPS_DIR)) 

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "psws.settings.dev")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
