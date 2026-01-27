/**
 * Organizations Drill-down Page - صفحة المنشآت
 * Organization → Accounts → Transactions drill-down
 */
import React, { useState } from 'react';
import { 
  Building2, 
  ChevronLeft, 
  Wallet, 
  ArrowUpRight, 
  ArrowDownRight,
  AlertTriangle,
  FileText
} from 'lucide-react';
import { 
  useOrganizations, 
  useOrganizationStats, 
  useAccountsByType,
  useTransactions,
  useAuditFlags
} from '../lib/hooks';
import { ComplianceProgressBar } from '../components/dashboard/ComplianceScore';
import { RiskBadge } from '../components/dashboard/RiskBadge';

const OrganizationsPage = ({ onSelectOrg }) => {
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [view, setView] = useState('orgs'); // orgs | accounts | transactions

  const { data: orgsData, isLoading: loadingOrgs } = useOrganizations();
  const { data: orgStats } = useOrganizationStats(selectedOrg?.id);
  const { data: accountsByType } = useAccountsByType(selectedOrg?.id);
  const { data: transactions } = useTransactions({
    organization_id: selectedOrg?.id,
    account_code: selectedAccount?.account_code,
    page_size: 20,
  });
  const { data: auditFlags } = useAuditFlags({
    organization_id: selectedOrg?.id,
  });

  const organizations = orgsData?.results || [];
  const transactionList = transactions?.results || [];
  const flagsList = auditFlags?.results || [];

  const formatCurrency = (amount, currency = 'SAR') => {
    return new Intl.NumberFormat('ar-SA', {
      style: 'currency',
      currency,
      minimumFractionDigits: 0,
    }).format(amount || 0);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('ar-SA');
  };

  const handleSelectOrg = (org) => {
    setSelectedOrg(org);
    setSelectedAccount(null);
    setView('accounts');
    onSelectOrg?.(org);
  };

  const handleSelectAccount = (account) => {
    setSelectedAccount(account);
    setView('transactions');
  };

  const handleBack = () => {
    if (view === 'transactions') {
      setSelectedAccount(null);
      setView('accounts');
    } else if (view === 'accounts') {
      setSelectedOrg(null);
      setView('orgs');
    }
  };

  // Render Organizations List
  if (view === 'orgs') {
    return (
      <div className="space-y-6" data-testid="organizations-page">
        <div>
          <h1 className="text-ar-title flex items-center gap-3">
            <Building2 className="w-8 h-8 text-primary" />
            المنشآت
          </h1>
          <p className="text-muted-foreground">عرض وتصفح بيانات المنشآت المسجلة</p>
        </div>

        {loadingOrgs ? (
          <div className="text-center py-12 text-muted-foreground">جاري التحميل...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {organizations.map((org) => (
              <div
                key={org.id}
                onClick={() => handleSelectOrg(org)}
                className="finai-card cursor-pointer hover:border-primary/50 transition-colors"
                data-testid={`org-card-${org.id}`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">{org.name}</h3>
                    <div className="text-sm text-muted-foreground mt-1">
                      {org.country} • {org.industry}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1 en-text">
                      {org.tax_id}
                    </div>
                  </div>
                  <ChevronLeft className="w-5 h-5 text-muted-foreground" />
                </div>
                
                <div className="mt-4 pt-4 border-t border-border">
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-muted-foreground">
                      العملة: <span className="text-foreground">{org.currency}</span>
                    </span>
                    <span className="text-muted-foreground">
                      نسبة الضريبة: <span className="number text-foreground">{org.vat_rate}%</span>
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Render Accounts View
  if (view === 'accounts') {
    return (
      <div className="space-y-6" data-testid="accounts-view">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm">
          <button onClick={handleBack} className="text-primary hover:underline">
            المنشآت
          </button>
          <ChevronLeft className="w-4 h-4 text-muted-foreground" />
          <span>{selectedOrg?.name}</span>
        </div>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-ar-title">{selectedOrg?.name}</h1>
            <p className="text-muted-foreground">دليل الحسابات والأرصدة</p>
          </div>
        </div>

        {/* Stats */}
        {orgStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="finai-card">
              <div className="text-sm text-muted-foreground">إجمالي المعاملات</div>
              <div className="text-2xl font-bold number">{orgStats.total_transactions}</div>
            </div>
            <div className="finai-card">
              <div className="text-sm text-muted-foreground">المستندات</div>
              <div className="text-2xl font-bold number">{orgStats.total_documents}</div>
            </div>
            <div className="finai-card">
              <div className="text-sm text-muted-foreground">الشهر الحالي</div>
              <div className="text-2xl font-bold number">
                {formatCurrency(orgStats.current_month_transactions, selectedOrg?.currency)}
              </div>
            </div>
            <div className="finai-card">
              <div className="text-sm text-muted-foreground">غير المطابقة</div>
              <div className="text-2xl font-bold number text-yellow-400">{orgStats.unreconciled_count}</div>
            </div>
          </div>
        )}

        {/* Accounts by Type */}
        {accountsByType && (
          <div className="space-y-4">
            {Object.entries(accountsByType).map(([type, accounts]) => (
              <div key={type} className="finai-card">
                <h3 className="text-lg font-semibold mb-4 capitalize">
                  {type === 'asset' ? 'الأصول' :
                   type === 'liability' ? 'الالتزامات' :
                   type === 'equity' ? 'حقوق الملكية' :
                   type === 'revenue' ? 'الإيرادات' :
                   type === 'expense' ? 'المصروفات' : type}
                </h3>
                <div className="space-y-2">
                  {accounts.map((account) => (
                    <div
                      key={account.id}
                      onClick={() => handleSelectAccount(account)}
                      className="flex items-center justify-between p-3 bg-secondary/30 
                               rounded-lg cursor-pointer hover:bg-secondary/50 transition-colors"
                      data-testid={`account-${account.account_code}`}
                    >
                      <div className="flex items-center gap-3">
                        <Wallet className="w-4 h-4 text-muted-foreground" />
                        <div>
                          <div className="font-medium">{account.account_name}</div>
                          <div className="text-xs text-muted-foreground en-text">
                            {account.account_code}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-left">
                          <div className="number font-medium">
                            {formatCurrency(account.current_balance, selectedOrg?.currency)}
                          </div>
                        </div>
                        <ChevronLeft className="w-4 h-4 text-muted-foreground" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Related Audit Flags */}
        {flagsList.length > 0 && (
          <div className="finai-card">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-400" />
              ملاحظات التدقيق المرتبطة
            </h3>
            <div className="space-y-2">
              {flagsList.slice(0, 5).map((flag) => (
                <div key={flag.id} className="p-3 bg-secondary/30 rounded-lg">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-medium">{flag.title}</div>
                      <div className="text-sm text-muted-foreground">{flag.description?.slice(0, 100)}...</div>
                    </div>
                    <RiskBadge level={flag.priority} size="small" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Render Transactions View
  return (
    <div className="space-y-6" data-testid="transactions-view">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm flex-wrap">
        <button onClick={() => { setSelectedOrg(null); setView('orgs'); }} className="text-primary hover:underline">
          المنشآت
        </button>
        <ChevronLeft className="w-4 h-4 text-muted-foreground" />
        <button onClick={handleBack} className="text-primary hover:underline">
          {selectedOrg?.name}
        </button>
        <ChevronLeft className="w-4 h-4 text-muted-foreground" />
        <span>{selectedAccount?.account_name}</span>
      </div>

      <div>
        <h1 className="text-ar-title">{selectedAccount?.account_name}</h1>
        <div className="text-muted-foreground">
          <span className="en-text">{selectedAccount?.account_code}</span>
          <span className="mx-2">•</span>
          <span>الرصيد: </span>
          <span className="number">{formatCurrency(selectedAccount?.current_balance, selectedOrg?.currency)}</span>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="finai-card">
        <h3 className="text-lg font-semibold mb-4">المعاملات</h3>
        
        {transactionList.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            لا توجد معاملات لهذا الحساب
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>المرجع</th>
                  <th>الوصف</th>
                  <th>التاريخ</th>
                  <th>المبلغ</th>
                  <th>الضريبة</th>
                  <th>الحالة</th>
                </tr>
              </thead>
              <tbody>
                {transactionList.map((txn) => (
                  <tr key={txn.id} data-testid={`txn-${txn.id}`}>
                    <td className="font-mono text-xs en-text">{txn.reference_number || '-'}</td>
                    <td>
                      <div>{txn.description || txn.category}</div>
                      <div className="text-xs text-muted-foreground">{txn.vendor_customer}</div>
                    </td>
                    <td className="number">{formatDate(txn.transaction_date)}</td>
                    <td>
                      <div className={`flex items-center gap-1 ${
                        txn.transaction_type === 'income' ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {txn.transaction_type === 'income' ? (
                          <ArrowUpRight className="w-4 h-4" />
                        ) : (
                          <ArrowDownRight className="w-4 h-4" />
                        )}
                        <span className="number">{formatCurrency(txn.amount, txn.currency)}</span>
                      </div>
                    </td>
                    <td className="number">{formatCurrency(txn.vat_amount, txn.currency)}</td>
                    <td>
                      {txn.is_anomaly ? (
                        <span className="px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded-full">
                          مشبوه
                        </span>
                      ) : txn.is_reconciled ? (
                        <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">
                          مطابق
                        </span>
                      ) : (
                        <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 text-xs rounded-full">
                          قيد المراجعة
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default OrganizationsPage;
