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


def apply_rule(ledger_data, rule):
    matches = {}
    for field in ['payee', 'note']:
        condition = getattr(rule, field)
        if all(matches.values()):
            if condition:
                try:
                    matches[field] = re.match(
                        '^(?:{})$'.format(condition),
                        ledger_data[field],
                    )
                except re.error:
                    return False
        else:
            return False

    if all(matches.values()):
        for field in ['payee', 'note']:
            replacement = getattr(rule, 'new_{}'.format(field))
            if replacement or field in matches:
                try:
                    regex = matches[field].re
                except KeyError:
                    regex = re.compile(r'.*')
                ledger_data[field] = regex.sub(
                    getattr(rule, 'new_{}'.format(field)),
                    ledger_data[field],
                )
        for account in ledger_data['accounts']:
            acc_name = account[0]
            if acc_name == settings.LEDGER_DEFAULT_TO:
                account[0] = rule.account or acc_name
        return True
    else:
        return False


def apply_rules(ledger_data, user):
    replacement_rules = (
        Rule.objects.filter(user=user).order_by(
            *(Length(field).desc() for field in ['payee', 'note'])
        )
    )
    for rule in replacement_rules:
        if apply_rule(ledger_data, rule):
            return True
    return False


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
        'note': params.get('note', ''),
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
    if entry.note:
        optionals['note'] = entry.note
    response_data.update(optionals)

    return JsonResponse(response_data, status=201)
