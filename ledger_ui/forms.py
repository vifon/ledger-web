from django import forms
from django.conf import settings


class LedgerForm(forms.Form):

    def __init__(self, *args, currencies, accounts, **kwargs):
        initial_choices = {
            'currency': settings.LEDGER_DEFAULT_CURRENCY,
            'acc_from': settings.LEDGER_DEFAULT_FROM,
            'acc_to': settings.LEDGER_DEFAULT_TO,
        }
        super().__init__(initial=initial_choices, *args, **kwargs)
        self.currencies = currencies
        self.fields['acc_from'] = forms.ChoiceField(
            label='Account from',
            choices=[(x, x) for x in accounts],
        )
        self.fields['acc_to'] = forms.ChoiceField(
            label='Account to',
            choices=[(x, x) for x in ([settings.LEDGER_DEFAULT_TO] + accounts)],
        )
        self.fields['currency'] = forms.ChoiceField(
            choices=[(x, x) for x in self.currencies],
            required=False,
        )
        self.order_fields(self.field_order)

    payee = forms.CharField(max_length=512)
    amount = forms.DecimalField(decimal_places=2)

    field_order = ['payee', 'amount', 'currency', 'acc_from', 'acc_to']
