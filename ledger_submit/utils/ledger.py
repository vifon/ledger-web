#!/usr/bin/env python3

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
    """

    template = """
{date} {payee}
    {account_to:<34s}  {amount:>12}{currency}
    {account_from}
""".rstrip()

    def __init__(self, **kwargs):
        self.payee = kwargs['payee']
        self.account_from = kwargs['account_from']
        self.account_to = kwargs['account_to']
        self.amount = "{:.2f}".format(float(kwargs['amount'].split()[0]))
        self.currency = kwargs['amount'].split()[1]
        self.date = kwargs.get('date', time.strftime("%F"))
        self.normalize_currency()

    def normalize_currency(self):
        conversions = {
            "USD": ("$", ""),
        }
        if self.currency in conversions:
            pre_currency, self.currency = conversions[self.currency]
            self.amount = "{}{}".format(pre_currency, self.amount)
        if self.currency:
            self.currency = " {}".format(self.currency)

    def __str__(self):
        return self.template.format(**vars(self))

    def store(self, ledger_path):
        with open(ledger_path, 'a') as ledger_file:
            print(self, file=ledger_file)


def accounts(ledger_path):
    return _call(ledger_path, ["accounts"])


def _call(ledger_path, args):
    output = subprocess.check_output(
        ["ledger", "-f", ledger_path] + args,
        universal_newlines=True
    )
    return output.strip().split("\n")


if __name__ == '__main__':
    import doctest
    import sys
    sys.exit(doctest.testmod()[0])
