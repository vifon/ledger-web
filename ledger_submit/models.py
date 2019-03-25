from django.db import models

from ledger_ui.utils.ledger_api import accounts as ledger_accounts


class Rule(models.Model):
    payee = models.CharField(max_length=512, primary_key=True)
    new_payee = models.CharField(max_length=512, blank=True)
    ACCOUNT_CHOICES = [
        (x, x)
        for x
        in ledger_accounts('/home/vifon/sync.d/Cloud/ledger.dat')
    ]
    acc_from = models.CharField(
        'Account from',
        max_length=512,
        blank=True,
        choices=ACCOUNT_CHOICES,
    )
    acc_to = models.CharField(
        'Account to',
        max_length=512,
        blank=True,
        choices=ACCOUNT_CHOICES,
    )
