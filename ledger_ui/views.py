from django.http import HttpResponse
from django.shortcuts import render

import os

from .utils import ledger_api

LEDGER_PATH = os.environ.get('LEDGER_PATH', '/home/vifon/sync.d/Cloud/ledger.dat')


def index(request):
    with open(LEDGER_PATH, 'r') as ledger_fd:
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
    accounts = ledger_api.accounts(LEDGER_PATH)
    return render(
        request,
        'ledger_ui/accounts.html',
        {'accounts': accounts},
    )
