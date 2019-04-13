from django import forms
from django.conf import settings

from . import fields
from ledger_submit.models import Rule


def account_choices(accounts):
    yield None, "---------"
    for account in accounts:
        yield account, account


class LedgerForm(forms.Form):

    def __init__(self, *args, currencies, payees, accounts, **kwargs):
        initial_choices = {
            'currency': settings.LEDGER_DEFAULT_CURRENCY,
            'acc_from': settings.LEDGER_DEFAULT_FROM,
            'acc_to': settings.LEDGER_DEFAULT_TO,
        }
        super().__init__(initial=initial_choices, *args, **kwargs)
        self.currencies = currencies
        self.fields['payee'].widget = fields.ListTextWidget(
            name='payees',
            data_list=payees,
        )
        self.fields['acc_from'] = forms.ChoiceField(
            label='Account from',
            choices=lambda: account_choices(accounts),
        )
        self.fields['acc_to'] = forms.ChoiceField(
            label='Account to',
            choices=lambda: account_choices(
                [settings.LEDGER_DEFAULT_TO] + accounts
            ),
        )
        self.fields['currency'] = forms.ChoiceField(
            choices=[(x, x) for x in self.currencies],
            required=False,
        )
        self.order_fields(self.field_order)

    payee = forms.CharField(max_length=512)
    amount = forms.DecimalField(decimal_places=2)

    field_order = ['payee', 'amount', 'currency', 'acc_from', 'acc_to']


class RuleModelForm(forms.ModelForm):

    class Meta:
        model = Rule
        exclude = ['user']

    def __init__(self, *args, accounts, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['acc_from'] = forms.ChoiceField(
            label='Account from',
            required=False,
            choices=lambda: account_choices(accounts),
        )
        self.fields['acc_to'] = forms.ChoiceField(
            label='Account to',
            required=False,
            choices=lambda: account_choices(
                [settings.LEDGER_DEFAULT_TO] + accounts
            ),
        )
