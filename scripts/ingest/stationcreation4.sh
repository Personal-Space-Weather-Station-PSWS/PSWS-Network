#!/usr/bin/env bash
# stationcreation4.sh — create a 'stations' user and set password
# --------------------------------------------------------------------
# Adapted from stationcreation3.c (Cole Robbins, Nicholas Muscolino, W. Engelke)
# Copyright 2025 The University of Alabama
# Author: Evan C Hardt
# --------------------------------------------------------------------

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Must run as root." >&2
  exit 1
fi

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 USERNAME PASSWORD" >&2
  exit 1
fi

user="$1"
pass="$2"

# USERNAME: one capital letter (A–Z) followed by 6 digits (e.g., S012345, A123456)
[[ $user =~ ^[A-Z][0-9]{6}$ ]] || { echo "Invalid username (expected A–Z followed by 6 digits)"; exit 1; }
# PASSWORD: exactly 32 chars
[[ ${#pass} -eq 32 ]] || { echo "Password must be 32 characters"; exit 1; }


# refuse if user exists
id -u "$user" >/dev/null 2>&1 && { echo "User exists"; exit 1; }

# create user with primary group 'stations' and home dir
useradd -m -g stations -s /bin/bash "$user"

# set password via stdin
printf '%s:%s\n' "$user" "$pass" | chpasswd
