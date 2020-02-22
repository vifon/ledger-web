from django import forms
from django.conf import settings
from django.forms import formset_factory, BaseFormSet
from django.utils.translation import gettext as _

import datetime
import re

from . import fields
from ledger_submit.models import Rule


class AccountForm(forms.Form):

    name = forms.CharField(widget=fields.ListTextWidget(
        name='accounts',
        data_list=None,
        attrs={'class': 'name-input'},
    ))
    amount = forms.DecimalField(
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'amount-input'}),
    )
    currency = forms.CharField(
        required=False,
        widget=fields.ListTextWidget(
            name='currencies',
            data_list=None,
            attrs={
                'tabindex': -1,
                'size': 5,
                'class': 'currency-input',
            },
        ),
    )

    field_order = ['name', 'amount', 'currency']

    def __init__(self, *args, default_currency=None, **kwargs):
        if default_currency is None:
            default_currency = settings.LEDGER_DEFAULT_CURRENCY
        initial = kwargs.pop('initial', {})
        if initial.get('amount') is None:
            initial['currency'] = default_currency
        super().__init__(*args, initial=initial, **kwargs)


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

    date = forms.DateField(initial=datetime.date.today)
    payee = forms.CharField(max_length=512)
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'tabindex': -1,
                'rows': 1,
                'cols': 20,
            },
        ),
    )

    amend = forms.BooleanField(
        # Even though it's a BooleanField, the HiddenInput widget is
        # textual. False would be cast to "False" which is true, so
        # let's use a false string instead.
        initial='',
        required=False,
        widget=forms.HiddenInput(),
    )
    save_rule = forms.BooleanField(
        label="Save as a new rule",
        initial=False,
        required=False,
    )

    def top_fields(self):
        return (
            self[field]
            for field in ['date', 'payee', 'note']
        )

    def __init__(self, *args, payees, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payee'].widget = fields.ListTextWidget(
            name='payees',
            data_list=payees,
            attrs={'autofocus': ''},
        )


class RuleModelForm(forms.ModelForm):

    class Meta:
        model = Rule
        exclude = ['user']

    def conditions(self):
        return (
            self[field]
            for field in ['payee', 'note']
        )

    def actions(self):
        return (
            self[field]
            for field in ['new_payee', 'new_note', 'account']
        )

    def __init__(self, *args, accounts, payees, user, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user

        self.fields['payee'].widget = fields.ListTextWidget(
            name='payee',
            data_list=map(re.escape, payees),
        )
        self.fields['note'].widget = forms.Textarea(
            attrs={
                'rows': 1,
                'cols': 20,
            },
        )
        self.fields['new_payee'].widget = fields.ListTextWidget(
            name='new_payee',
            data_list=payees,
        )
        self.fields['new_note'].widget = forms.Textarea(
            attrs={
                'rows': 1,
                'cols': 20,
            },
        )
        self.fields['account'].widget = fields.ListTextWidget(
            name='account',
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

        if errors:
            raise forms.ValidationError(errors)
