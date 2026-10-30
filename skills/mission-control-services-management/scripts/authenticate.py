#!/usr/bin/env python3
"""Private local sign-in for Braingeneers skills; Python standard library only.

Maintained in mission_control/skills/mission-control-services-management/scripts.
Ship an identical copy in data-explorer-cli-access so both skills stand alone.
This checks local structure/expiry only; the protected API verifies access.
"""

import argparse
import base64
from datetime import datetime, timezone
import importlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import tempfile
import webbrowser


LOGIN_URL = "https://service-accounts.braingeneers.gi.ucsc.edu/generate_token"
MAX_RESPONSE = 1024 * 1024


class SignInError(Exception):
    """Messages must never include credential input or underlying exceptions."""


def select_path(explicit=None):
    if explicit:
        return Path(explicit).expanduser().absolute()
    preferred = Path.home() / ".ssh" / "braingeneers_jwt_token.json"
    if preferred.exists():
        return preferred
    try:
        package = importlib.import_module("braingeneers.iot")
    except ImportError:
        return preferred
    for root in package.__path__:
        candidate = Path(root) / "service_account" / "config.json"
        if candidate.is_file():
            return candidate
    return preferred


def validate_response(raw):
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError
        token = data.get("access_token")
        if not isinstance(token, str) or not isinstance(data.get("expires_at"), str):
            raise ValueError
        if not data["expires_at"].strip():
            raise ValueError
        parts = token.split(".")
        if len(parts) != 3 or not all(parts):
            raise ValueError
        payload = json.loads(base64.b64decode(
            parts[1] + "=" * (-len(parts[1]) % 4), altchars=b"-_", validate=True))
        exp = payload["exp"]
        if isinstance(exp, bool) or not isinstance(exp, (int, float)) or not math.isfinite(exp):
            raise ValueError
        expiry = datetime.fromtimestamp(exp, timezone.utc)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, OSError):
        raise SignInError("That is not a complete sign-in response. Copy the entire response from the login page.") from None
    if expiry <= datetime.now(timezone.utc):
        raise SignInError("That sign-in has expired. Sign in again to get a fresh response.")
    return data, expiry


def load_response(path):
    with path.open("r", encoding="utf-8") as source:
        raw = source.read(MAX_RESPONSE + 1)
    if len(raw) > MAX_RESPONSE:
        raise SignInError("The selected file is too large to be a sign-in response.")
    return raw


def save_response(path, raw):
    data, expiry = validate_response(raw)
    if path.is_symlink():
        raise SignInError("The selected credential path is a symbolic link. Select its intended local destination explicitly.")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # The temporary directory is private; the file is 0600 from creation.
    with tempfile.TemporaryDirectory(prefix=".braingeneers-sign-in-", dir=path.parent) as staging:
        temporary = Path(staging) / "credential.json"
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as target:
            json.dump(data, target)
            target.write("\n")
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    return expiry


def check_response(path):
    if not path.is_file():
        raise SignInError("Sign-in is needed to connect this computer to Braingeneers.")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise SignInError("The saved sign-in needs private file permissions. Import it with this helper to secure it.")
    return validate_response(load_response(path))[1]


def read_private_response(before_read):
    """Read multiline paste without terminal echo, including on agent PTYs.

    Never fall back to input()/getpass's echoing fallback on a missing terminal.
    Disable canonical input too so long pasted JSON lines are not truncated.
    """
    if not sys.stdin.isatty():
        raise SignInError("Run this command in your own interactive terminal, or use --import-file with a locally saved response.")
    if os.name == "nt":
        import msvcrt

        def read_char():
            char = msvcrt.getwch()
            if char == "\x03":
                raise KeyboardInterrupt
            return "\n" if char == "\r" else char

        before_read()
        return collect_response(read_char)

    import termios
    fd = sys.stdin.fileno()
    original = termios.tcgetattr(fd)
    hidden = termios.tcgetattr(fd)
    hidden[3] &= ~(termios.ECHO | termios.ECHONL | termios.ICANON)
    hidden[6][termios.VMIN] = 1
    hidden[6][termios.VTIME] = 0
    try:
        termios.tcsetattr(fd, termios.TCSANOW, hidden)
        # Hide input before displaying the paste invitation or opening a browser:
        # browser startup may block while a user pastes into this terminal.
        before_read()
        return collect_response(lambda: sys.stdin.read(1))
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, original)


def collect_response(read_char):
    chars = []
    while True:
        char = read_char()
        if not char or char in ("\x04", "\x1a"):
            raise EOFError
        if char == "\x03":
            raise KeyboardInterrupt
        if char in ("\x7f", "\b"):
            if chars:
                chars.pop()
            continue
        if char == "\r":
            char = "\n"
        if char == "\n" and (not chars or chars[-1] == "\n"):
            return "".join(chars)
        chars.append(char)
        if len(chars) > MAX_RESPONSE:
            raise SignInError("The pasted response is too large. Copy only the response from the login page.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Connect this computer to Braingeneers using your academic sign-in.")
    parser.add_argument("--token-file", help="Use an explicitly selected credential path.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--path", action="store_true", help="Print the selected path only; do not read credentials.")
    mode.add_argument("--check", action="store_true", help="Check the saved sign-in without opening a browser.")
    mode.add_argument("--import-file", type=Path, help="Privately import a response already saved locally.")
    parser.add_argument("--no-browser", action="store_true", help="Show the sign-in link without trying to open it.")
    args = parser.parse_args(argv)
    try:
        path = select_path(args.token_file)
        if args.path:
            print(path)
            return 0
        if args.check:
            expiry = check_response(path)
        else:
            if args.import_file:
                raw = load_response(args.import_file.expanduser())
            else:
                if not sys.stdin.isatty():
                    raise SignInError("Run this command in your own interactive terminal, or use --import-file with a locally saved response.")
                def present_login():
                    print("Sign in with the academic account you use for Braingeneers web services (UCSC or your institution).")
                    print(LOGIN_URL)
                    print("Copy the entire response from that page. Paste it here, then press Enter twice.")
                    print("Your paste stays hidden. Do not paste it into chat. Ctrl+C cancels.", flush=True)
                    if not args.no_browser:
                        try:
                            opened = webbrowser.open(LOGIN_URL)
                        except Exception:
                            opened = False
                        if not opened:
                            print("Open the sign-in link above in your browser.", flush=True)

                raw = read_private_response(present_login)
                print()
            expiry = save_response(path, raw)
        print(f"Sign-in file: {path}")
        print(f"Sign-in expires: {expiry.isoformat()}")
        print(f"Renewal due: {(expiry - datetime.now(timezone.utc)).total_seconds() <= 604800}")
        print("Local check passed. The agent should now verify access with a read-only Braingeneers API request.")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nSign-in canceled; the existing credential was kept.", file=sys.stderr)
        return 1
    except SignInError as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception:
        # Parsing, filesystem, and terminal errors may include credential contents.
        print("Could not complete local sign-in. Check the selected file and directory access; no credential details were displayed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
