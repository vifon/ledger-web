#!/usr/bin/env python3

from collections import namedtuple
import io
import re
import subprocess
import time


EntryAccount = namedtuple(
    'EntryAccount',
    [
        'name',
        'amount',
        'currency',
    ],
)


class Entry:
    """A single Ledger entry.

    >>> entry = Entry(
    ...    payee="Burger King",
    ...    accounts=[
    ...      ("Expenses:Food", "19.99 PLN"),
    ...      ("Liabilities:Credit Card",),
    ...    ],
    ...    date="2019-02-15",
    ... )

    >>> print(entry)
    <BLANKLINE>
    2019-02-15 Burger King
        Expenses:Food                              19.99 PLN
        Liabilities:Credit Card

    >>> entry = Entry(
    ...    payee="McDonald's",
    ...    accounts=[
    ...      ("Expenses:Food", "5 USD"),
    ...      ("Liabilities:Credit Card",),
    ...    ],
    ...    date="2019-02-16",
    ... )

    >>> print(entry)
    <BLANKLINE>
    2019-02-16 McDonald's
        Expenses:Food                              $5.00
        Liabilities:Credit Card

    >>> entry = Entry(
    ...    payee="McDonald's",
    ...    accounts=[
    ...      ("Expenses:Food", "5 $"),
    ...      ("Liabilities:Credit Card",),
    ...    ],
    ...    date="2019-02-16",
    ... )

    >>> print(entry)
    <BLANKLINE>
    2019-02-16 McDonald's
        Expenses:Food                              $5.00
        Liabilities:Credit Card

    >>> entry = Entry(
    ...    payee="McDonald's",
    ...    accounts=[
    ...      ("Expenses:Food", "5", "$"),
    ...      ("Assets:Loans:John", "5 USD"),
    ...      ("Liabilities:Credit Card",),
    ...    ],
    ...    note=":loan:",
    ...    date="2019-02-16",
    ... )

    >>> print(entry)
    <BLANKLINE>
    2019-02-16 McDonald's
        ; :loan:
        Expenses:Food                              $5.00
        Assets:Loans:John                          $5.00
        Liabilities:Credit Card
    """

    def __init__(self, **kwargs):
        self.payee = kwargs['payee']
        self.date = kwargs.get('date', time.strftime("%F"))
        self.note = kwargs.get('note')

        self.accounts = []
        for account in kwargs['accounts']:
            try:
                # We got either the 3-argument form...
                name, amount, currency = account
            except ValueError:
                # ...or the 2-argument form with currency merged with amount...
                try:
                    name, amount = account
                except ValueError:
                    # ...or the single-argument form with no amount or currency.
                    name, = account
                    amount = None
                    currency = None
                else:
                    # We definitely got the 2-argument form, let's
                    # split it into amount and currency or just
                    # amount.
                    amount, _, currency = amount.partition(' ')
            finally:
                # amount may be None if we got the 1-argument form.
                if amount is not None:
                    amount = "{:.2f}".format(float(amount))
                else:
                    # Avoid storing a currency without a value, it
                    # doesn't make sense and leads to weird bugs.
                    currency = None
            self.accounts.append(EntryAccount(
                name=name,
                amount=amount,
                currency=currency,
            ))

    currency_conversions = {
        'USD': {
            'symbol': '$',
            'position': 'left',
        },
        '$': {
            'symbol': '$',
            'position': 'left',
        },
        '': {
            'symbol': '',
            'position': 'left',
        }
    }

    @classmethod
    def normalize_currency(cls, currency):
        rule = cls.currency_conversions.get(currency, '')
        if rule:
            return rule
        else:
            return {
                'symbol': currency,
                'position': 'right',
            }

    def __str__(self):
        output = ['']
        output.append('{date} {payee}'.format(**vars(self)))
        if self.note:
            for line in self.note.splitlines():
                output.append('    ; {note}'.format(note=line))
        for account in self.accounts:
            currency = self.normalize_currency(account.currency)
            if account.amount is None:
                template = '    {account}'
            else:
                if currency['position'] == 'left':
                    account = account._replace(
                        amount="{currency}{amount}".format(
                            currency=currency['symbol'],
                            amount=account.amount,
                        ),
                    )
                    template = '    {account:<34s}  {amount:>12}'
                else:
                    template = '    {account:<34s}  {amount:>12} {currency}'

            output.append(
                template.format(
                    account=account.name,
                    currency=currency['symbol'],
                    amount=account.amount,
                )
            )
        return "\n".join(output)


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

        return output.strip().splitlines()

    def __iter__(self):
        date_regexp = r'\d{4}-\d{2}-\d{2}|\d{4}/\d{2}/\d{2}'
        def prepare_entry(entry_lines):
            match = re.match(
                '({date}){cleared}\s+({payee})'.format(
                    date=date_regexp,
                    cleared=r'(?: [!*])?',
                    payee=r'.*'
                ),
                entry_lines[0],
            )
            date = match.group(1)
            payee = match.group(2)

            match = re.fullmatch(
                '\s*;\s*(.*)',
                entry_lines[1],
            )
            if match:
                note = match.group(1)
            else:
                # In Django strings usually aren't nullable, let's
                # keep this convention and just store an empty string.
                note = ''

            return {
                'body': "\n".join(entry_lines),
                'date': date,
                'payee': payee,
                'note': note,
            }

        entry = []

        ledger_file = self._call("print")

        for line in map(str.rstrip, ledger_file):
            if not entry:
                # Skipping the empty space and non-entries between entries.
                if re.match(r'{} '.format(date_regexp), line):
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
