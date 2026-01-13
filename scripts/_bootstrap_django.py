# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
"""
Django bootstrap for standalone scripts.
Sets up environment so scripts can safely use Django.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def bootstrap(*, settings_module: str | None = None, add_apps_dir: bool = True) -> None:
    """
    Prepare environment so scripts can safely use Django.

    - Adds src/ and src/apps to sys.path
    - Loads .env file
    - Sets DJANGO_SETTINGS_MODULE if missing
    - Calls django.setup()
    """

    # ------------------------------------------------------------------
    # Locate repo root (directory containing 'src/')
    # ------------------------------------------------------------------
    here = Path(__file__).resolve()
    repo_root = next(
        p for p in [here] + list(here.parents)
        if (p / "src").is_dir()
    )

    src_dir = repo_root / "src"
    apps_dir = src_dir / "apps"

    # ------------------------------------------------------------------
    # Fix Python path
    # ------------------------------------------------------------------
    sys.path.insert(0, str(src_dir))

    if add_apps_dir:
        sys.path.insert(0, str(apps_dir))

    # ------------------------------------------------------------------
    # Load environment (.env)
    # ------------------------------------------------------------------
    load_dotenv(str(repo_root) + "/deploy/env/psws.env", override=False)

    # ------------------------------------------------------------------
    # Configure Django
    # ------------------------------------------------------------------
    if settings_module:
        os.environ["DJANGO_SETTINGS_MODULE"] = settings_module
    else:
        os.environ.setdefault(
            "DJANGO_SETTINGS_MODULE",
            "psws.settings.dev"
        )

    # ------------------------------------------------------------------
    # Start Django
    # ------------------------------------------------------------------
    import django  # noqa: E402
    django.setup()

