from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .utils import ledger_api
from ledger_submit.utils.ledger_api import Entry


@login_required
def index(request):
    with open(settings.LEDGER_PATH, 'r') as ledger_fd:
        entries = list(ledger_api.read_entries(ledger_fd))
    reversed_sort = request.GET.get('reverse', 'false').lower() not in ['false', '0']
    if reversed_sort:
        entries = reversed(entries)
    return render(
        request,
        'ledger_ui/index.html',
        {
            'entries': entries,
            'reverse': reversed_sort,
        },
    )


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


@login_required
def submit(request):
    currencies = ledger_api.currencies(settings.LEDGER_PATH)
    accounts = ledger_api.accounts(settings.LEDGER_PATH)
    print(currencies)

    if request.method == 'POST':
        form = LedgerForm(
            request.POST,
            currencies=currencies,
            accounts=accounts,
        )
        if form.is_valid():
            validated = form.cleaned_data
            entry = Entry(
                payee=validated['payee'],
                account_from=validated['acc_from'],
                account_to=validated['acc_to'],
                amount=validated['amount'],
                currency=validated['currency'],
            )
            entry.store(settings.LEDGER_PATH)
    else:
        form = LedgerForm(
            currencies=currencies,
            accounts=accounts,
        )

    return render(
        request,
        'ledger_ui/submit.html',
        {'form': form},
    )


@login_required
def accounts(request):
    accounts = ledger_api.accounts(settings.LEDGER_PATH)
    search = request.GET.get('search', '').lower()
    if search:
        accounts = [account for account in accounts if search in account.lower()]
    return render(
        request,
        'ledger_ui/accounts.html',
        {
            'accounts': accounts,
            'search': search,
        },
    )
