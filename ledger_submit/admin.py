from django.contrib import admin

from .models import Rule


class RuleAdmin(admin.ModelAdmin):
    list_display = ('payee', 'new_payee', 'acc_from', 'acc_to')

    # ACCOUNT_CHOICES = [(x,x) for x in ledger_accounts('/home/vifon/sync.d/Cloud/ledger.dat')]
    # acc_from = forms.ChoiceField(choices=ACCOUNT_CHOICES)
    # acc_to = forms.ChoiceField(choices=ACCOUNT_CHOICES)


admin.site.register(Rule, RuleAdmin)
