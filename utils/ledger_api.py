#!/usr/bin/env python3

from collections import namedtuple
import io
import re
import subprocess
import time


class Entry:
    """A single Ledger entry.

    >>> entry = Entry(
    ...    payee="Burger King",
    ...    account_from="Liabilities:Credit Card",
    ...    account_to="Expenses:Food",
    ...    amount="19.99 PLN",
    ...    date="2019-02-15",
    ... )

    >>> print(entry)
    <BLANKLINE>
    2019-02-15 Burger King
        Expenses:Food                              19.99 PLN
        Liabilities:Credit Card

    >>> entry = Entry(
    ...    payee="McDonald's",
    ...    account_from="Liabilities:Credit Card",
    ...    account_to="Expenses:Food",
    ...    amount="5 USD",
    ...    date="2019-02-16",
    ... )

    >>> print(entry)
    <BLANKLINE>
    2019-02-16 McDonald's
        Expenses:Food                              $5.00
        Liabilities:Credit Card

    >>> entry = Entry(
    ...    payee="McDonald's",
    ...    account_from="Liabilities:Credit Card",
    ...    account_to="Expenses:Food",
    ...    amount="5 $",
    ...    date="2019-02-16",
    ... )

    >>> print(entry)
    <BLANKLINE>
    2019-02-16 McDonald's
        Expenses:Food                              $5.00
        Liabilities:Credit Card
    """

    template = """
{date} {payee}
    {account_to:<34s}  {pp_amount:>12}{pp_currency}
    {account_from}
""".rstrip()

    def __init__(self, **kwargs):
        self.payee = kwargs['payee']
        self.account_from = kwargs['account_from']
        self.account_to = kwargs['account_to']
        self.date = kwargs.get('date', time.strftime("%F"))

        self.currency = kwargs.get('currency')
        if self.currency is None:
            self.currency = kwargs['amount'].split()[1]
            self.amount = "{:.2f}".format(float(kwargs['amount'].split()[0]))
        else:
            self.amount = "{:.2f}".format(float(kwargs['amount']))

        self.normalize_currency()

    def normalize_currency(self):
        conversions = {
            "USD": ("$", ""),
            "$": ("$", ""),
        }
        if self.currency in conversions:
            pre_currency, self.pp_currency = conversions[self.currency]
            self.pp_amount = "{}{}".format(pre_currency, self.amount)
        else:
            self.pp_amount = self.amount
            self.pp_currency = self.currency

        if self.pp_currency:
            self.pp_currency = " " + self.pp_currency

    def __str__(self):
        return self.template.format(**vars(self))


class Journal:

    class CannotRevert(Exception):
        pass

    class LedgerCliError(Exception):
        pass

    # Not used but let's keep it as documentation of the expected
    # fields of the passed objects.
    LastData = namedtuple(
        'LastData',
        [
            'last_entry',
            'old_position',
            'new_position',
        ],
    )

    def __init__(self, ledger_path, last_data=None):
        self.path = ledger_path
        self.last_data = last_data

    def can_revert(self):
        if self.last_data is None:
            return False

        with open(self.path, 'r') as ledger_file:
            current_end = ledger_file.seek(0, 2)
            if current_end != self.last_data.new_position:
                return False

            ledger_file.seek(self.last_data.old_position)
            stored_entry = str(self.last_data.last_entry)
            actual_entry = ledger_file.read().rstrip()
            if stored_entry != actual_entry:
                return False

        return True

    def revert(self):
        if self.last_data is None:
            raise Journal.CannotRevert()

        with open(self.path, 'a+') as ledger_file:
            if self.last_data.new_position != ledger_file.tell():
                raise Journal.CannotRevert()

            ledger_file.seek(self.last_data.old_position)
            if ledger_file.read().rstrip() != str(self.last_data.last_entry):
                raise Journal.CannotRevert()

            ledger_file.truncate(self.last_data.old_position)

    def append(self, entry):
        with open(self.path, 'a') as ledger_file:
            old_position = ledger_file.tell()
            print(entry, file=ledger_file)
            new_position = ledger_file.tell()
        return old_position, new_position

    def accounts(self):
        return self._call("accounts")

    def payees(self):
        return self._call("payees")

    def currencies(self):
        return self._call("commodities")

    def csv(self, *args):
        return io.StringIO("\n".join(self._call("csv", *args)))

    def _call(self, *args):
        try:
            output = subprocess.check_output(
                ["ledger", "-f", self.path] + list(args),
                universal_newlines=True,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            raise Journal.LedgerCliError() from e

        return output.strip().split("\n")

    def __iter__(self):
        def prepare_entry(entry_lines):
            match = re.match(
                r'(\d{4}-\d{2}-\d{2})(?: [!*])?\s+(.*)', entry_lines[0]
            )
            return {
                'body': "\n".join(entry_lines),
                'date': match.group(1),
                'payee': match.group(2),
            }

        entry = []
        with open(self.path, 'r') as ledger_file:
            for line in map(str.rstrip, ledger_file):
                if not entry:
                    # Skipping the empty space and non-entries between entries.
                    if re.match(r'\d{4}-\d{2}-\d{2} ', line):
                        # A beginning of a next entry.
                        entry.append(line)
                else:
                    # In the middle of parsing an entry.
                    if line:
                        # Let's parse some more of it.
                        entry.append(line)
                    else:
                        # End of an entry.
                        yield prepare_entry(entry)
                        entry = []
            if entry:
                yield prepare_entry(entry)


if __name__ == '__main__':
    import doctest
    import sys
    sys.exit(doctest.testmod()[0])
