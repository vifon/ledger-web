from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.generic.edit import CreateView, UpdateView, DeleteView

import pandas as pd
import re

from .forms import SubmitForm, RuleModelForm
from ledger_submit.models import Rule
from utils import ledger_api


def index(request):
    return render(
        request,
        'ledger_ui/index.html',
    )


@login_required
def register(request):
    with open(request.user.ledgerpath.path, 'r') as ledger_fd:
        entries = list(ledger_api.read_entries(ledger_fd))
    reversed_sort = request.GET.get('reverse', 'true').lower() not in ['false', '0']
    if reversed_sort:
        entries = reversed(entries)
    return render(
        request,
        'ledger_ui/register.html',
        {
            'entries': entries,
            'reverse': reversed_sort,
        },
    )


@login_required
def charts(request):
    ledger_path = request.user.ledgerpath.path

    csv = ledger_api.csv(
        ledger_path,
        '--monthly',
        '-X', settings.LEDGER_DEFAULT_CURRENCY,
    )
    df = pd.read_csv(
        csv,
        header=None,
        names=[
            'date', 'code', 'payee', 'account', 'currency', 'amount',
            'reconciled', 'comment',
        ],
        usecols=['date', 'payee', 'account', 'amount'],
        parse_dates=['date'],
    )

    expenses = df[df['account'].str.contains("^Expenses:")].copy()
    income = df[df['account'].str.contains("^Income:")]

    account_filter = request.GET.get('account_filter', '')
    if account_filter:
        expenses = expenses[expenses['account'].str.contains(
            account_filter,
            case=False,
        )]

    date_grouped_expenses = expenses[['date', 'amount']].groupby('date').sum()
    date_grouped_income = income[['date', 'amount']].groupby('date').sum()

    date_range = pd.date_range(df['date'].min(), df['date'].max(), freq='MS')
    date_grouped_expenses = date_grouped_expenses.reindex(date_range, fill_value=0)
    date_grouped_income = date_grouped_income.reindex(date_range, fill_value=0)

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
            'account_filter': account_filter,
        },
    )


@login_required
def submit(request):
    ledger_path = request.user.ledgerpath.path

    accounts = ledger_api.accounts(ledger_path)
    currencies = ledger_api.currencies(ledger_path)
    payees = ledger_api.payees(ledger_path)

    if request.method == 'POST':
        form = SubmitForm(
            request.POST,
            accounts=accounts,
            currencies=currencies,
            payees=payees,
        )
        if form.is_valid():
            validated = form.cleaned_data
            entry = ledger_api.Entry(
                date=validated['date'],
                payee=validated['payee'],
                account_from=validated['acc_from'],
                account_to=validated['acc_to'],
                amount=validated['amount'],
                currency=validated['currency'],
            )
            entry.store(ledger_path)
    else:
        form = SubmitForm(
            accounts=accounts,
            currencies=currencies,
            payees=payees,
        )

    return render(
        request,
        'ledger_ui/submit.html',
        {'form': form},
    )


@login_required
def balance(request):
    ledger_path = request.user.ledgerpath.path

    csv = ledger_api.csv(
        ledger_path,
    )
    df = pd.read_csv(
        csv,
        header=None,
        names=[
            'date', 'code', 'payee', 'account', 'currency', 'amount',
            'reconciled', 'comment',
        ],
        usecols=['account', 'currency', 'amount'],
    )

    search = request.GET.get('search', '').lower()
    if search:
        df = df[df['account'].str.contains(search, case=False)]

    balance = df.groupby(['account', 'currency']).sum()
    balance['amount'] = balance['amount'].round(2)

    return render(
        request,
        'ledger_ui/balance.html',
        {
            'accounts': balance.to_dict()['amount'],
            'search': search,
        },
    )


@method_decorator(login_required, name='dispatch')
class RuleIndexView(generic.ListView):
    model = Rule
    template_name = 'ledger_ui/rules.html'

    def get_queryset(self):
        return Rule.objects.filter(user=self.request.user)


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
        ledger_path = self.request.user.ledgerpath.path
        kwargs['accounts'] = ledger_api.accounts(ledger_path)
        kwargs['payees'] = ledger_api.payees(ledger_path)
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
            kwargs['initial']['payee'] = re.escape(self.request.GET['payee'])
        except KeyError:
            pass
        return kwargs


@method_decorator(login_required, name='dispatch')
class RuleDeleteView(UserCheckMixin, DeleteView):
    model = Rule
    success_url = reverse_lazy('ledger_ui:rules')

    def get_object(self, *args, **kwargs):
        obj = super().get_object(*args, **kwargs)
        if not obj.user == self.request.user:
            raise Http404
        return obj
