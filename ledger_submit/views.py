from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

import json

from .models import Rule, Token
from utils import ledger_api


def require_token(view):
    def inner(request, *args, **kwargs):
        try:
            params = json.loads(request.body)
            token = params['token']
            token_obj = Token.objects.get(token=token)
            request.user = token_obj.user
        except (KeyError, json.decoder.JSONDecodeError):
            return JsonResponse(
                {
                    'error': {
                        'not_authorized': None,
                    },
                },
                status=403,
            )
        except Token.DoesNotExist:
            return JsonResponse(
                {
                    'error': {
                        'not_authorized': token,
                    },
                },
                status=403,
            )
        else:
            return view(request, *args, **kwargs)
    return inner


def add_ledger_entry(ledger_path, account_from, account_to, payee, amount):
    try:
        replacement = Rule.objects.get(pk=payee)
    except Rule.DoesNotExist:
        pass
    else:
        payee = replacement.new_payee or payee
        account_from = replacement.acc_from or account_from
        account_to = replacement.acc_to or account_to

    amount = amount.replace(",", ".").strip()
    entry = ledger_api.Entry(
        payee=payee,
        account_from=account_from,
        account_to=account_to,
        amount=amount,
    )
    entry.store(ledger_path)
    return entry


@require_POST
@csrf_exempt
@require_token
def submit_as_url(request, account_from, account_to, payee, amount):
    ledger_path = request.user.ledgerpath.path
    entry = add_ledger_entry(ledger_path, account_from, account_to, payee, amount)

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
@require_token
def submit_as_json(request):
    params = json.loads(request.body)
    ledger_data = {
        'payee': params['payee'],
        'amount': params['amount'],
        'account_from': params['account_from'],
        'account_to': params['account_to'],
    }
    ledger_path = request.user.ledgerpath.path
    entry = add_ledger_entry(ledger_path, **ledger_data)
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
