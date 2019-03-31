from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import Http404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from .forms import LedgerForm, RuleModelForm
from ledger_submit.models import Rule
from utils import ledger_api


@login_required
def index(request):
    with open(request.user.ledgerpath.path, 'r') as ledger_fd:
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
    ledger_path = request.user.ledgerpath.path

    currencies = ledger_api.currencies(ledger_path)
    accounts = ledger_api.accounts(ledger_path)

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
            entry.store(ledger_path)
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
    ledger_path = request.user.ledgerpath.path
    accounts = ledger_api.accounts(ledger_path)
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
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class RuleEditView(UserCheckMixin, RuleViewBase, UpdateView):
    pass


@method_decorator(login_required, name='dispatch')
class RuleCreateView(RuleViewBase, CreateView):
    pass


@method_decorator(login_required, name='dispatch')
class RuleDeleteView(UserCheckMixin, DeleteView):
    model = Rule
    success_url = reverse_lazy('ledger_ui:rules')

    def get_object(self, *args, **kwargs):
        obj = super().get_object(*args, **kwargs)
        if not obj.user == self.request.user:
            raise Http404
        return obj
