from django import forms
from django.conf import settings
from django.contrib import admin

from .models import Rule, Token

from utils.ledger_api import accounts as ledger_accounts


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ('user', 'payee', 'new_payee', 'acc_from', 'acc_to')


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'short_token']

