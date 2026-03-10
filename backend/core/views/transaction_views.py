from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404

from core.views.base import OrganizationTemplateView
from documents.models import Account, Transaction


class TransactionsPageView(OrganizationTemplateView):
    template_name = 'transactions.html'

    def get_queryset(self):
        organization = self.get_organization()
        queryset = Transaction.objects.filter(organization=organization)

        transaction_type = self.request.GET.get('type')
        is_anomaly = self.request.GET.get('anomaly')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        if is_anomaly not in (None, ''):
            queryset = queryset.filter(is_anomaly=is_anomaly == 'true')
        if date_from:
            queryset = queryset.filter(transaction_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(transaction_date__lte=date_to)

        return queryset.order_by('-transaction_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        queryset = self.get_queryset()
        all_transactions = Transaction.objects.filter(organization=organization)

        paginator = Paginator(queryset, 30)
        page_obj = paginator.get_page(self.request.GET.get('page'))

        context.update(
            {
                'transactions': page_obj,
                'stats': {
                    'total': all_transactions.count(),
                    'income': all_transactions.filter(transaction_type='income').aggregate(total=Sum('amount'))['total'] or 0,
                    'expense': all_transactions.filter(transaction_type='expense').aggregate(total=Sum('amount'))['total'] or 0,
                    'anomalies': all_transactions.filter(is_anomaly=True).count(),
                },
                'current_type': self.request.GET.get('type'),
                'current_anomaly': self.request.GET.get('anomaly'),
                'date_from': self.request.GET.get('date_from'),
                'date_to': self.request.GET.get('date_to'),
            }
        )
        return context


class TransactionDetailPageView(OrganizationTemplateView):
    template_name = 'transactions_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transaction'] = get_object_or_404(
            Transaction,
            id=self.kwargs['transaction_id'],
            organization=self.get_organization(),
        )
        return context


class AccountsListPageView(OrganizationTemplateView):
    template_name = 'accounts/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        accounts = Account.objects.filter(organization=organization)

        account_type = self.request.GET.get('type')
        if account_type:
            accounts = accounts.filter(account_type=account_type)
        accounts = accounts.order_by('account_code')

        type_summary = {}
        for account in Account.objects.filter(organization=organization):
            account_summary = type_summary.setdefault(account.account_type, {'count': 0, 'balance': 0})
            account_summary['count'] += 1
            account_summary['balance'] += account.current_balance or 0

        paginator = Paginator(accounts, 30)
        page_obj = paginator.get_page(self.request.GET.get('page'))

        context.update(
            {
                'accounts': page_obj,
                'type_summary': type_summary,
                'current_type': account_type,
            }
        )
        return context


class AccountDetailPageView(OrganizationTemplateView):
    template_name = 'accounts/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        account = get_object_or_404(Account, id=self.kwargs['account_id'], organization=organization)
        transactions = Transaction.objects.filter(
            Q(debit_account=account) | Q(credit_account=account),
            organization=organization,
        ).order_by('-transaction_date')[:20]

        context.update(
            {
                'account': account,
                'transactions': transactions,
            }
        )
        return context


transactions_view = TransactionsPageView.as_view()
transaction_detail_view = TransactionDetailPageView.as_view()
accounts_list_view = AccountsListPageView.as_view()
account_detail_view = AccountDetailPageView.as_view()


__all__ = [
    'TransactionsPageView',
    'TransactionDetailPageView',
    'AccountsListPageView',
    'AccountDetailPageView',
    'transactions_view',
    'transaction_detail_view',
    'accounts_list_view',
    'account_detail_view',
]
