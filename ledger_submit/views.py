from django.conf import settings
from django.db.models.functions import Length
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from datetime import datetime
import json
import re

from .models import Rule, Token
from ledger_ui.models import Undo
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


# <LEGACY>
def add_ledger_entry_v1(
        user,
        account_from,
        account_to,
        payee,
        amount,
        currency=None,
        date=None,
        skip_rules=False,
):
    ledger_path = user.ledger_path.path
    if not skip_rules:
        replacement_rules = (
            Rule.objects.filter(user=user).order_by(Length('payee').desc())
        )
        for rule in replacement_rules:
            try:
                match = re.fullmatch(rule.payee, payee)
            except re.error:
                pass
            else:
                if match:
                    payee = rule.new_payee or payee
                    account_to = rule.account or account_to
                    break

    amount = amount.replace(",", ".").strip()

    if date is None:
        date = datetime.now().strftime("%F")

    entry = ledger_api.Entry(
        payee=payee,
        accounts=[
            (
                (account_to, amount, currency)
                if currency is not None
                else (account_to, amount)
            ),
            (account_from,)
        ],
        date=date,
    )
    old, new = ledger_api.Journal(ledger_path).append(entry)
    Undo.objects.update_or_create(
        pk=user.id,
        defaults={
            'last_entry': entry,
            'old_position': old,
            'new_position': new,
        },
    )
    return entry


@require_POST
@csrf_exempt
@require_token
def submit_as_json_v1(request):
    params = json.loads(request.body)
    ledger_data = {
        'payee': params['payee'],
        'amount': params['amount'],
        'account_from': params['account_from'],
        'account_to': params['account_to'],
    }
    entry = add_ledger_entry_v1(
        user=request.user,
        skip_rules=params.get('skip_rules', False),
        **ledger_data,
    )
    return JsonResponse(
        {
            'payee': entry.payee,
            'amount': entry.accounts[0].amount,
            'currency': entry.accounts[0].currency,
            'account_from': entry.accounts[1].name,
            'account_to': entry.accounts[0].name,
        },
        status=201,
    )
# </LEGACY>


def apply_rules(ledger_data, user):
    replacement_rules = (
        Rule.objects.filter(user=user).order_by(Length('payee').desc())
    )
    for rule in replacement_rules:
        try:
            match = True
            for field in ['payee', 'comment']:
                condition = getattr(rule, field)
                if match and condition:
                    match = bool(
                        ledger_data[field]
                        and re.fullmatch(condition, ledger_data[field])
                    )
        except re.error:
            pass
        else:
            if match:
                ledger_data['payee'] = rule.new_payee or ledger_data['payee']
                ledger_data['comment'] = \
                    rule.new_comment or ledger_data['comment']
                for account in ledger_data['accounts']:
                    acc_name = account[0]
                    if acc_name == settings.LEDGER_DEFAULT_TO:
                        account[0] = rule.account or acc_name
                break
    return ledger_data


def normalize_data(ledger_data):
    for account in ledger_data['accounts']:
        try:
            account[1] = str(account[1]).replace(",", ".").strip()
        except IndexError:
            pass
    return ledger_data


@require_POST
@csrf_exempt
@require_token
def submit_as_json(request):
    params = json.loads(request.body)
    ledger_data = {
        'payee': params['payee'],
        'date': params.get('date', datetime.now().strftime("%F")),
        'accounts': params['accounts'],
        'comment': params.get('comment'),
    }

    if not params.get('skip_rules', False):
        apply_rules(ledger_data, request.user)
    normalize_data(ledger_data)

    entry = ledger_api.Entry(**ledger_data)

    old, new = ledger_api.Journal(request.user.ledger_path.path).append(entry)
    Undo.objects.update_or_create(
        pk=request.user.id,
        defaults={
            'last_entry': entry,
            'old_position': old,
            'new_position': new,
        },
    )

    response_data = {
        'payee': entry.payee,
        'date': entry.date,
        'accounts': [
            list(account._asdict().values())
            for account in entry.accounts
        ],
    }
    optionals = {}
    if entry.comment:
        optionals['comment'] = entry.comment
    response_data.update(optionals)

    return JsonResponse(response_data, status=201)
