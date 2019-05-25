from django import forms
from django.conf import settings
from django.utils.translation import gettext as _

import datetime
import re

from . import fields
from .models import Undo
from ledger_submit.models import Rule
from utils import ledger_api


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

    amend = forms.BooleanField(
        initial=False,
        required=False,
        widget=forms.HiddenInput(),
    )
    date = forms.DateField(initial=datetime.date.today)
    payee = forms.CharField(max_length=512)
    amount = forms.DecimalField(decimal_places=2)
    acc_from = forms.CharField(label='Account from')
    acc_to = forms.CharField(label='Account to')

    field_order = ['date', 'payee', 'amount', 'currency', 'acc_from', 'acc_to']


class RuleModelForm(forms.ModelForm):

    amend = forms.BooleanField(
        initial=False,
        required=False,
        disabled=True,
        label='Apply to last entry',
    )

    class Meta:
        model = Rule
        exclude = ['user']

    def __init__(self, *args, accounts, payees, user, journal, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user
        self.journal = journal

        try:
            undo = Undo.objects.get(pk=user)
        except Undo.DoesNotExist:
            pass
        else:
            self.journal.last_data = undo
            if self.journal.can_revert():
                self.fields['amend'].disabled = False

        self.fields['payee'].widget = fields.ListTextWidget(
            name='payee',
            data_list=map(re.escape, payees),
        )
        self.fields['new_payee'].widget = fields.ListTextWidget(
            name='new_payee',
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

    def clean(self):
        errors = []
        cleaned_data = super().clean()

        payee = cleaned_data['payee']
        user = self.user
        try:
            Rule.objects.exclude(
                pk=self.instance.pk,
            ).get(
                payee=payee,
                user=user,
            )
        except Rule.DoesNotExist:
            pass
        else:
            errors.append(
                forms.ValidationError(
                    _("Non-unique data: payee=%(payee)s, user=%(user)s."),
                    params={'payee': payee, 'user': user},
                    code='invalid',
                )
            )

        try:
            undo = Undo.objects.get(pk=self.user)
        except Undo.DoesNotExist:
            pass
        else:
            if self.data.get('amend') and not self.journal.can_revert():
                self.add_error(
                    'amend',
                    forms.ValidationError(
                        _("Amend not possible."),
                        code='integrity',
                    )
                )

        if errors:
            raise forms.ValidationError(errors)
