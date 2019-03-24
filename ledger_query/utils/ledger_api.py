#!/usr/bin/env python3

import subprocess


def accounts(ledger_path):
    return _call(ledger_path, ["accounts"])


def _call(ledger_path, args):
    output = subprocess.check_output(
        ["ledger", "-f", ledger_path] + args,
        universal_newlines=True
    )
    return output.strip().split("\n")
