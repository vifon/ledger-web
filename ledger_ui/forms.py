from django import forms
from django.conf import settings

from . import fields
from ledger_submit.models import Rule


class SubmitForm(forms.Form):

    def __init__(self, *args, currencies, payees, accounts, **kwargs):
        initial_choices = {
            'currency': settings.LEDGER_DEFAULT_CURRENCY,
            'acc_from': settings.LEDGER_DEFAULT_FROM,
            'acc_to': settings.LEDGER_DEFAULT_TO,
        }
        super().__init__(initial=initial_choices, *args, **kwargs)
        self.fields['payee'].widget = fields.ListTextWidget(
            name='payees',
            data_list=payees,
        )
        self.fields['acc_from'].widget = fields.ListTextWidget(
            name='acc_from',
            data_list=accounts,
        )
        self.fields['acc_to'].widget = fields.ListTextWidget(
            name='acc_to',
            data_list=accounts,
        )
        self.fields['currency'] = forms.ChoiceField(
            choices=[(x, x) for x in currencies],
            required=False,
        )
        self.order_fields(self.field_order)

    payee = forms.CharField(max_length=512)
    amount = forms.DecimalField(decimal_places=2)
    acc_from = forms.CharField(label='Account from')
    acc_to = forms.CharField(label='Account to')

    field_order = ['payee', 'amount', 'currency', 'acc_from', 'acc_to']


class RuleModelForm(forms.ModelForm):

    class Meta:
        model = Rule
        exclude = ['user']

    def __init__(self, *args, accounts, payees, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_payee'].widget = fields.ListTextWidget(
            name='payees',
            data_list=payees,
        )
        self.fields['acc_from'].widget = fields.ListTextWidget(
            name='acc_from',
            data_list=accounts,
        )
        self.fields['acc_to'].widget = fields.ListTextWidget(
            name='acc_to',
            data_list=accounts,
        )
