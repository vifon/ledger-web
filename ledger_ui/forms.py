from django import forms
from django.conf import settings
from django.forms import formset_factory, BaseFormSet
from django.utils.translation import gettext as _

import datetime
import re

from . import fields
from .models import Undo
from ledger_submit.models import Rule


class AccountForm(forms.Form):

    name = forms.CharField(widget=fields.ListTextWidget(
        name='accounts',
        data_list=None,
    ))
    amount = forms.DecimalField(decimal_places=2, required=False)
    currency = forms.CharField(widget=fields.ListTextWidget(
        name='currencies',
        data_list=None,
        attrs={
            'tabindex': -1,
            'size': 5,
        },
    ))

    field_order = ['name', 'amount', 'currency']

    def __init__(self, *args, **kwargs):
        initial_choices = {
            'currency': settings.LEDGER_DEFAULT_CURRENCY,
        }
        initial_choices.update(kwargs.pop('initial', {}))
        super().__init__(*args, initial=initial_choices, **kwargs)


class BaseAccountFormSet(BaseFormSet):

    def clean(self):
        if any(self.errors):
            return

        missing_amount_count = [
            form.cleaned_data.get('amount')
            for form in self.forms
        ].count(None)
        if missing_amount_count > 1:
            raise forms.ValidationError(
                _("Only one account can have the amount omitted.")
            )


AccountFormSet = formset_factory(
    AccountForm,
    formset=BaseAccountFormSet,
    min_num=2,
    extra=0,
    validate_min=True,
)


class SubmitForm(forms.Form):

    def __init__(self, *args, payees, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payee'].widget = fields.ListTextWidget(
            name='payees',
            data_list=payees,
            attrs={'autofocus': ''},
        )
        self.order_fields(self.field_order)

    amend = forms.BooleanField(
        # Even though it's a BooleanField, the HiddenInput widget is
        # textual. False would be cast to "False" which is true, so
        # let's use a false string instead.
        initial='',
        required=False,
        widget=forms.HiddenInput(),
    )
    date = forms.DateField(initial=datetime.date.today)
    payee = forms.CharField(max_length=512)

    field_order = ['date', 'payee']


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
