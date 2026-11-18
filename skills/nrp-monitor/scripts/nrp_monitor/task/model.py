"""NRP monitor task/model (mechanical extraction; R3a)."""
import argparse
import collections
import contextlib
import fcntl
import getpass
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


def resize_advice(line):
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    out = []
    for kind, use, req, pct, mx in _m_state.FLAG_RES.findall(line):
        use, req = float(use), float(req)
        peak = float(mx) if mx else use
        if kind == "mem":
            new = max(1, -(-peak * 1.5 // 1))
            if new < req:                                                    # no advice when it would not shrink
                out.append("memory %gGi -> %dGi (peak %.1fGi)" % (req, new, peak))
        elif kind == "cpu":
            out.append("cpu %g -> %g (mean %.2f)" % (req, max(0.5, -(-peak * 3 // 1) / 2), use))
        else:
            out.append("gpu at %s%% of %g GPU: run on CPU or bundle more work per GPU" % (pct, req))
    return "; ".join(out) or "see the flag line"

