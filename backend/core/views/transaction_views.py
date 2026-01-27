"""
Transaction and Account Views - وجهات المعاملات والحسابات
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum, Q

from documents.models import Transaction, Account


@login_required
def transactions_view(request):
    """قائمة المعاملات"""
    user = request.user
    organization = user.organization
    
    transactions = Transaction.objects.filter(organization=organization)
    
    # Filters
    transaction_type = request.GET.get('type')
    is_anomaly = request.GET.get('anomaly')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    if is_anomaly is not None and is_anomaly != '':
        transactions = transactions.filter(is_anomaly=is_anomaly == 'true')
    if date_from:
        transactions = transactions.filter(transaction_date__gte=date_from)
    if date_to:
        transactions = transactions.filter(transaction_date__lte=date_to)
    
    transactions = transactions.order_by('-transaction_date')
    
    # Pagination
    paginator = Paginator(transactions, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Stats
    all_transactions = Transaction.objects.filter(organization=organization)
    stats = {
        'total': all_transactions.count(),
        'income': all_transactions.filter(transaction_type='income').aggregate(total=Sum('amount'))['total'] or 0,
        'expense': all_transactions.filter(transaction_type='expense').aggregate(total=Sum('amount'))['total'] or 0,
        'anomalies': all_transactions.filter(is_anomaly=True).count(),
    }
    
    context = {
        'transactions': page_obj,
        'stats': stats,
        'current_type': transaction_type,
        'current_anomaly': is_anomaly,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'transactions.html', context)


@login_required
def transaction_detail_view(request, transaction_id):
    """تفاصيل المعاملة"""
    user = request.user
    organization = user.organization
    
    transaction = get_object_or_404(Transaction, id=transaction_id, organization=organization)
    
    context = {
        'transaction': transaction,
    }
    
    return render(request, 'transactions_detail.html', context)


@login_required
def accounts_list_view(request):
    """قائمة الحسابات - دليل الحسابات"""
    user = request.user
    organization = user.organization
    
    accounts = Account.objects.filter(organization=organization)
    
    # Filter by type
    account_type = request.GET.get('type')
    if account_type:
        accounts = accounts.filter(account_type=account_type)
    
    accounts = accounts.order_by('account_number')
    
    # Group by type for summary
    type_summary = {}
    for acct in Account.objects.filter(organization=organization):
        acct_type = acct.account_type
        if acct_type not in type_summary:
            type_summary[acct_type] = {'count': 0, 'balance': 0}
        type_summary[acct_type]['count'] += 1
        type_summary[acct_type]['balance'] += acct.current_balance or 0
    
    # Pagination
    paginator = Paginator(accounts, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'accounts': page_obj,
        'type_summary': type_summary,
        'current_type': account_type,
    }
    
    return render(request, 'accounts/list.html', context)


@login_required
def account_detail_view(request, account_id):
    """تفاصيل الحساب"""
    user = request.user
    organization = user.organization
    
    account = get_object_or_404(Account, id=account_id, organization=organization)
    
    # Get related transactions
    transactions = Transaction.objects.filter(
        Q(debit_account=account) | Q(credit_account=account),
        organization=organization
    ).order_by('-transaction_date')[:20]
    
    context = {
        'account': account,
        'transactions': transactions,
    }
    
    return render(request, 'accounts/detail.html', context)
