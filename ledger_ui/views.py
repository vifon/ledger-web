from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from .utils import ledger_api


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
    pass


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
