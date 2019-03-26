from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render

from .utils import ledger_api


def index(request):
    with open(settings.LEDGER_PATH, 'r') as ledger_fd:
        entries = list(ledger_api.read_entries(ledger_fd))
    reverse = request.GET.get('reverse', 'false').lower() not in ['false', '0']
    if reverse:
        entries = reversed(entries)
    return render(
        request,
        'ledger_ui/index.html',
        {
            'entries': entries,
            'reverse': reverse,
        },
    )


def submit(request):
    pass


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
