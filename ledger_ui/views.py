from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models.functions import Lower
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.generic.edit import CreateView, UpdateView, DeleteView

import pandas as pd
import re

from .forms import SubmitForm, RuleModelForm, AccountFormSet
from .models import Undo
from ledger_submit.models import Rule
from utils import ledger_api


def index(request):
    return render(
        request,
        'ledger_ui/index.html',
    )


@login_required
def journal(request):
    if request.method == 'POST':
        if request.POST.get('revert'):
            undo = get_object_or_404(Undo, pk=request.user)

            ledger_path = request.user.ledger_path.path
            journal = ledger_api.Journal(ledger_path, undo)

            try:
                journal.revert()
            except journal.CannotRevert:
                return render(
                    request,
                    'ledger_ui/error/cannot_revert.html',
                    status=409,
                )

    entries = list(ledger_api.Journal(request.user.ledger_path.path))


    entry_filter = request.GET.get('filter', '')
    if entry_filter:
        entries = [
            entry
            for entry in entries
            if entry_filter.lower() in entry['body'].lower()
        ]

    count = request.GET.get('count', settings.LEDGER_ENTRY_COUNT)
    try:
        count = int(count)
    except ValueError:
        if count is not None and count != 'all':
            return HttpResponse(
                '<h1>Unprocessable Entity</h1> Bad count.',
                status=422,
            )
    if count != 'all' and len(entries) <= count:
        count = 'all'
    if count != 'all':
        entries = entries[-count:]

    reversed_sort = request.GET.get('reverse', 'true').lower() not in ['false', '0']
    if reversed_sort:
        entries = reversed(entries)

    ledger_path = request.user.ledger_path.path
    journal = ledger_api.Journal(ledger_path)
    try:
        undo = Undo.objects.get(pk=request.user)
    except Undo.DoesNotExist:
        pass
    else:
        journal.last_data = undo

    return render(
        request,
        'ledger_ui/journal.html',
        {
            'entries': entries,
            'reverse': reversed_sort,
            'count': count,
            'filter': entry_filter,
            'count_step': settings.LEDGER_ENTRY_COUNT,
            'can_revert': not entry_filter and journal.can_revert(),
        },
    )


@login_required
def charts(request):
    ledger_path = request.user.ledger_path.path

    csv = ledger_api.Journal(ledger_path).csv(
        '--monthly',
        '-X', settings.LEDGER_DEFAULT_CURRENCY,
    )
    df = pd.read_csv(
        csv,
        header=None,
        names=[
            'date', 'code', 'payee', 'account', 'currency', 'amount',
            'reconciled', 'note',
        ],
        usecols=['date', 'payee', 'account', 'amount'],
        parse_dates=['date'],
    )
    if len(df) == 0:
        return render(
            request,
            'ledger_ui/charts.html',
        )

    assets = df[df['account'].str.contains("^Assets:|^Liabilities:")]
    income = df[df['account'].str.contains("^Income:")]

    account_filter = request.GET.get('account_filter', '')
    if account_filter:
        expenses = df[df['account'].str.contains(
            account_filter,
            case=False,
        )].copy()
    else:
        expenses = df[df['account'].str.contains("^Expenses:")].copy()

    date_grouped_assets = assets[['date', 'amount']].groupby('date').sum()
    date_grouped_expenses = expenses[['date', 'amount']].groupby('date').sum()
    date_grouped_income = income[['date', 'amount']].groupby('date').sum()

    date_range = pd.date_range(df['date'].min(), df['date'].max(), freq='MS')
    date_grouped_assets = date_grouped_assets.reindex(date_range, fill_value=0)
    date_grouped_expenses = date_grouped_expenses.reindex(date_range, fill_value=0)
    date_grouped_income = date_grouped_income.reindex(date_range, fill_value=0)

    date_grouped_assets['amount'] = date_grouped_assets['amount'].cumsum()
    expenses['date'] = expenses['date'].dt.strftime("%Y-%m")

    return render(
        request,
        'ledger_ui/charts.html',
        {
            'dates': {'data': date_range.strftime('%Y-%m').to_series().to_list()},
            'expenses_totals': date_grouped_expenses['amount'].round(2).to_json(),
            'income_totals': (-date_grouped_income['amount']).round(2).to_json(),
            'expenses': (
                expenses[['date', 'account', 'amount']].to_json(
                    orient='table', index=False)),
            'assets': date_grouped_assets['amount'].round(2).to_json(),
            'account_filter': account_filter,
        },
    )


@login_required
def submit(request):
    ledger_path = request.user.ledger_path.path
    journal = ledger_api.Journal(ledger_path)
    ledger_errors = False

    try:
        accounts = journal.accounts()
        currencies = journal.currencies()
        payees = journal.payees()
    except journal.LedgerCliError as e:
        accounts = currencies = payees = []
        ledger_errors = e.__cause__

    if request.method == 'POST':
        form = SubmitForm(
            request.POST,
            payees=payees,
        )
        formset = AccountFormSet(
            request.POST,
        )
        if form.is_valid() and formset.is_valid():
            validated = form.cleaned_data
            entry = ledger_api.Entry(
                date=validated['date'],
                payee=validated['payee'],
                note=validated['note'],
                accounts=[
                    (account['name'], account['amount'], account['currency'])
                    for account in formset.cleaned_data
                    if account.get('name')
                ],
            )

            if validated['amend']:
                undo = get_object_or_404(Undo, pk=request.user)
                journal.last_data = undo

                try:
                    journal.revert()
                except journal.CannotRevert:
                    return render(
                        request,
                        'ledger_ui/error/cannot_revert.html',
                        status=409,
                    )

            old, new = journal.append(entry)
            Undo.objects.update_or_create(
                pk=request.user.id,
                defaults={
                    'last_entry': entry,
                    'old_position': old,
                    'new_position': new,
                },
            )
            return redirect('ledger_ui:journal')

    else:
        amend = request.GET.get('amend', 'false').lower() not in ['false', '0']
        if amend:
            last_entry = get_object_or_404(Undo, pk=request.user).last_entry
            form = SubmitForm(
                {
                    'date': last_entry.date,
                    'payee': last_entry.payee,
                    'note': last_entry.note,
                    'amend': True,
                },
                payees=payees,
            )
            default_currency = settings.LEDGER_DEFAULT_CURRENCY
            for account in last_entry.accounts:
                if account.amount is not None:
                    default_currency = account.currency
                    break
            formset = AccountFormSet(
                form_kwargs={
                    'default_currency': default_currency,
                },
                initial=[
                    account._asdict()
                    for account in last_entry.accounts
                ],
            )
        else:
            form = SubmitForm(payees=payees)
            formset = AccountFormSet(
                initial=[
                    {'name': settings.LEDGER_DEFAULT_TO},
                    {'name': settings.LEDGER_DEFAULT_FROM},
                ]
            )

    return render(
        request,
        'ledger_ui/submit.html',
        {
            'form': form,
            'formset': formset,
            'accounts': accounts,
            'currencies': currencies,
            'ledger_errors': ledger_errors,
        },
    )


@login_required
def balance(request):
    ledger_path = request.user.ledger_path.path

    csv = ledger_api.Journal(ledger_path).csv()
    df = pd.read_csv(
        csv,
        header=None,
        names=[
            'date', 'code', 'payee', 'account', 'currency', 'amount',
            'reconciled', 'note',
        ],
        usecols=['account', 'currency', 'amount'],
    )

    search = request.GET.get('filter', '')
    if search:
        df = df[df['account'].str.contains(search, case=False)]

    if len(df) == 0:
        return render(
            request,
            'ledger_ui/balance.html',
            {
                'accounts': [],
                'filter': search,
            },
        )

    balance = df.groupby(['account', 'currency']).sum()
    balance['amount'] = balance['amount'].round(2)

    return render(
        request,
        'ledger_ui/balance.html',
        {
            'accounts': balance.to_dict()['amount'],
            'filter': search,
        },
    )


@login_required
def register(request):
    ledger_path = request.user.ledger_path.path

    csv = ledger_api.Journal(ledger_path).csv()
    df = pd.read_csv(
        csv,
        header=None,
        names=[
            'date', 'code', 'payee', 'account', 'currency', 'amount',
            'reconciled', 'note',
        ],
        usecols=['date', 'payee', 'account', 'currency', 'amount'],
    )

    search = request.GET.get('filter', '')
    if search:
        df = df[df['account'].str.contains(search, case=False)]

    if len(df) == 0:
        return render(
            request,
            'ledger_ui/register.html',
            {
                'transactions': [],
                'filter': search,
            },
        )

    transactions = df
    transactions['total'] = transactions['amount'].cumsum().round(2)

    return render(
        request,
        'ledger_ui/register.html',
        {
            'transactions': transactions,
            'filter': search,
            'currency_count': transactions['currency'].unique().size,
        },
    )


@method_decorator(login_required, name='dispatch')
class RuleIndexView(generic.ListView):
    model = Rule
    template_name = 'ledger_ui/rules.html'

    def get_queryset(self):
        return Rule.objects.filter(
            user=self.request.user
        ).order_by(Lower('payee'))


class UserCheckMixin:
    def get_object(self, *args, **kwargs):
        obj = super().get_object(*args, **kwargs)
        if not obj.user == self.request.user:
            raise Http404
        return obj


class RuleViewBase(CreateView):
    model = Rule
    form_class = RuleModelForm
    template_name = 'ledger_ui/rule.html'
    success_url = reverse_lazy('ledger_ui:rules')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        ledger_path = self.request.user.ledger_path.path
        journal = ledger_api.Journal(ledger_path)
        kwargs['accounts'] = journal.accounts()
        kwargs['payees'] = journal.payees()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class RuleEditView(UserCheckMixin, RuleViewBase, UpdateView):
    pass


@method_decorator(login_required, name='dispatch')
class RuleCreateView(RuleViewBase, CreateView):

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            payee = self.request.GET['payee']
            kwargs['initial']['payee'] = re.escape(payee)
        except (KeyError, Undo.DoesNotExist):
            pass
        return kwargs


@method_decorator(login_required, name='dispatch')
class RuleDeleteView(UserCheckMixin, DeleteView):
    model = Rule
    success_url = reverse_lazy('ledger_ui:rules')
