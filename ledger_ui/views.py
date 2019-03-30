from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .forms import LedgerForm
from utils import ledger_api


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


@login_required
def submit(request):
    currencies = ledger_api.currencies(settings.LEDGER_PATH)
    accounts = ledger_api.accounts(settings.LEDGER_PATH)

    if request.method == 'POST':
        form = LedgerForm(
            request.POST,
            currencies=currencies,
            accounts=accounts,
        )
        if form.is_valid():
            validated = form.cleaned_data
            entry = ledger_api.Entry(
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
