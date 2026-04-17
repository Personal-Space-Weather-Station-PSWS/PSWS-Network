#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
"""
install_ssh_key.py  —  Privileged SSH key installer

Called from Django via sudoers rule:
    www-data ALL=(root) NOPASSWD: /usr/local/bin/install_ssh_key.py

Usage:
    sudo /usr/local/bin/install_ssh_key.py <station_id> <public_key>

    station_id  : station Unix account name  (e.g. S000128)
    public_key  : validated SSH public key string  (e.g. "ssh-ed25519 AAAA...")
"""

import sys
import os
import re
import base64
import stat
import pwd
import grp
import logging

# ── Configuration ─────────────────────────────────────────────────────────────

KEYS_BASE_DIR  = "/home/keys"
STATIONS_GROUP = "stations"
USERNAME_REGEX = re.compile(r'^[A-Za-z]\d{6}$')   # e.g. S000128, U123456
MAX_KEY_BYTES  = 8192
LOG_FILE       = "/var/log/dcsl_ssh_keys.log"

ALLOWED_KEY_TYPES = {
    'ssh-rsa',
    'ssh-ed25519',
    'ecdsa-sha2-nistp256',
    'ecdsa-sha2-nistp384',
    'ecdsa-sha2-nistp521',
    'sk-ssh-ed25519@openssh.com',
    'sk-ecdsa-sha2-nistp256@openssh.com',
}

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s  %(levelname)s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger(__name__)

# ── Validation ────────────────────────────────────────────────────────────────

def validate_username(username: str) -> str:
    """Reject anything that is not a plain station ID (e.g. S000128)."""
    if not USERNAME_REGEX.fullmatch(username):
        raise ValueError(f"Invalid station ID format: {username!r}")
    return username


def validate_public_key(key: str) -> str:
    """
    Re-validate the SSH public key even though the Django form already did so.
    This script runs as root — it must never trust its caller blindly.
    """
    if len(key.encode()) > MAX_KEY_BYTES:
        raise ValueError("Key exceeds maximum allowed length.")

    parts = key.strip().split()
    if len(parts) < 2:
        raise ValueError("Key must have at least a type and a base64 body.")

    key_type, key_data = parts[0], parts[1]

    if key_type not in ALLOWED_KEY_TYPES:
        raise ValueError(f"Disallowed key type: {key_type!r}")

    if not re.fullmatch(r'[A-Za-z0-9+/=]+', key_data):
        raise ValueError("Key body contains invalid characters.")

    try:
        decoded = base64.b64decode(key_data)
    except Exception as exc:
        raise ValueError(f"Key body is not valid base64: {exc}") from exc

    if len(decoded) < 32 or len(decoded) > 4096:
        raise ValueError("Decoded key length is outside expected bounds.")

    # Return only type + data — drop any comment the caller may have appended
    return f"{key_type} {key_data}"

# ── Account lookup ────────────────────────────────────────────────────────────

def lookup_station_account(username: str):
    """
    Look up the station's UID from /etc/passwd and the shared 'stations' GID
    from /etc/group. Raises ValueError if either does not exist on the system.
    """
    try:
        pw = pwd.getpwnam(username)
    except KeyError:
        raise ValueError(
            f"No Unix account found for station {username!r}. "
            f"Has stationcreation4.sh been run for this station?"
        )

    try:
        gr = grp.getgrnam(STATIONS_GROUP)
    except KeyError:
        raise ValueError(
            f"No Unix group '{STATIONS_GROUP}' found on this system."
        )

    return pw.pw_uid, gr.gr_gid

# ── Path helpers ──────────────────────────────────────────────────────────────

def safe_key_path(username: str):
    """
    Build the authorized_keys path and verify it stays inside KEYS_BASE_DIR.
    Raises ValueError on any path traversal attempt.
    """
    user_dir    = os.path.join(KEYS_BASE_DIR, username)
    target      = os.path.join(user_dir, "authorized_keys")
    real_base   = os.path.realpath(KEYS_BASE_DIR)
    real_target = os.path.realpath(os.path.abspath(target))

    if not real_target.startswith(real_base + os.sep):
        raise ValueError(f"Path traversal detected: {target!r}")

    return user_dir, target

# ── Core logic ────────────────────────────────────────────────────────────────

def install_key(username: str, public_key: str) -> None:
    username   = validate_username(username)
    public_key = validate_public_key(public_key)
    uid, gid   = lookup_station_account(username)

    user_dir, auth_keys_path = safe_key_path(username)

    # ── Create /home/keys/Sxxxxxx/ if it doesn't exist ───────────────────────
    if not os.path.exists(user_dir):
        os.makedirs(user_dir, mode=0o700, exist_ok=True)
        log.info("Created directory: %s", user_dir)

    # Directory: owner=S000128, group=stations, mode=700
    os.chown(user_dir, uid, gid)
    os.chmod(user_dir, stat.S_IRWXU)                        # 700

    # ── Write authorized_keys atomically ─────────────────────────────────────
    tmp_path = auth_keys_path + ".tmp"
    try:
        fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(public_key + "\n")
        os.replace(tmp_path, auth_keys_path)   # atomic on POSIX
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    # authorized_keys: owner=S000128, group=stations, mode=600
    os.chown(auth_keys_path, uid, gid)
    os.chmod(auth_keys_path, stat.S_IRUSR | stat.S_IWUSR)   # 600

    log.info(
        "Installed SSH key for station %s (uid=%d gid=%d) -> %s",
        username, uid, gid, auth_keys_path
    )
    print(f"OK: key installed to {auth_keys_path}")

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if os.geteuid() != 0:
        print("ERROR: this script must run as root.", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <station_id> <public_key>", file=sys.stderr)
        sys.exit(1)

    try:
        install_key(sys.argv[1], sys.argv[2])
    except ValueError as exc:
        log.warning("Rejected key install for %r: %s", sys.argv[1], exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
    except OSError as exc:
        log.error("OS error during key install for %r: %s", sys.argv[1], exc)
        print(f"ERROR: filesystem error: {exc}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
