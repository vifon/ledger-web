from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

import os
import json

from .models import Rules
from .utils import ledger_api


LEDGER_PATH = os.environ.get('LEDGER_PATH', '/dev/null')


def add_ledger_entry(account_from, account_to, payee, amount):
    try:
        replacement = Rules.objects.get(pk=payee)
    except Rules.DoesNotExist:
        pass
    else:
        payee = replacement.new_payee or payee
        account_from = replacement.acc_from or account_from
        account_to = replacement.acc_to or account_to

    entry = ledger_api.Entry(
        payee=payee,
        account_from=account_from,
        account_to=account_to,
        amount=amount,
    )
    entry.store(LEDGER_PATH)
    return entry


@require_http_methods(['GET', 'POST'])
@csrf_exempt
def submit_as_url(request, account_from, account_to, payee, amount):
    entry = add_ledger_entry(account_from, account_to, payee, amount)

    if request.method == 'GET':
        return render(
            request,
            'ledger_submit/entry.html',
            {'entry': entry},
            status=201,
        )
    elif request.method == 'POST':
        return JsonResponse(
            {
                'payee': entry.payee,
                'amount': entry.amount,
                'currency': entry.currency,
                'account_from': entry.account_from,
                'account_to': entry.account_to,
            },
            status=201,
        )


@require_POST
@csrf_exempt
def submit_as_json(request):
    params = json.loads(request.body)
    entry = add_ledger_entry(**params)
    return JsonResponse(
        {
            'payee': entry.payee,
            'amount': entry.amount,
            'currency': entry.currency,
            'account_from': entry.account_from,
            'account_to': entry.account_to,
        },
        status=201,
    )
