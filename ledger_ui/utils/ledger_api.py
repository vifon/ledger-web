#!/usr/bin/env python3

import re
import subprocess


def accounts(ledger_path):
    return _call(ledger_path, ["accounts"])


def _call(ledger_path, args):
    output = subprocess.check_output(
        ["ledger", "-f", ledger_path] + args,
        universal_newlines=True
    )
    return output.strip().split("\n")


def read_entries(fd):
    entry = []
    for line in fd:
        if entry:
            # In the middle of parsing an entry.
            if line == "\n":
                # End of an entry.
                yield "".join(entry)
                entry = []
            else:
                # Let's parse some more of it.
                entry.append(line)
        else:
            # Skipping the empty space between entries.
            if re.match(r'\d{4}-\d{2}-\d{2} ', line):
                # A beginning of a next entry.
                entry.append(line)
    yield "".join(entry)
