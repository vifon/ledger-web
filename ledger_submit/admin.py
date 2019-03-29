from django import forms
from django.conf import settings
from django.contrib import admin

from .models import Rule, Token

from ledger_ui.utils.ledger_api import accounts as ledger_accounts


def account_choices():
    yield None, "---------"
    for account in ledger_accounts(settings.LEDGER_PATH):
        yield account, account


class RuleAdminForm(forms.ModelForm):
    acc_from = forms.ChoiceField(
        choices=account_choices,
        required=False,
        label="Account from",
    )
    acc_to = forms.ChoiceField(
        choices=account_choices,
        required=False,
        label="Account to",
    )

    class Meta:
        model = Rule
        fields = '__all__'


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ('payee', 'new_payee', 'acc_from', 'acc_to')
    form = RuleAdminForm


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'short_token']

