/**
 * ZATCA E-Invoices Page - صفحة الفواتير الإلكترونية
 * View and validate ZATCA e-invoices
 */
import React, { useState } from 'react';
import { FileText, CheckCircle, XCircle, AlertCircle, Eye } from 'lucide-react';
import { useZATCAInvoices, useZATCAComplianceSummary, useZATCAValidation } from '../lib/hooks';
import { ComplianceScoreCard } from '../components/dashboard/ComplianceScore';

const InvoicesPage = ({ organizationId }) => {
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  
  const { data: invoicesData, isLoading } = useZATCAInvoices({
    organization_id: organizationId,
  });
  const { data: summary } = useZATCAComplianceSummary();
  const { data: validationData } = useZATCAValidation(selectedInvoice);

  const invoices = invoicesData?.results || [];

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ar-SA', {
      style: 'currency',
      currency: 'SAR',
      minimumFractionDigits: 2,
    }).format(amount || 0);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('ar-SA');
  };

  const getStatusBadge = (status) => {
    const config = {
      draft: { label: 'مسودة', class: 'bg-gray-500/20 text-gray-400' },
      validated: { label: 'تم التحقق', class: 'bg-green-500/20 text-green-400' },
      reported: { label: 'تم الإبلاغ', class: 'bg-blue-500/20 text-blue-400' },
      cleared: { label: 'تمت الموافقة', class: 'bg-green-500/20 text-green-400' },
      rejected: { label: 'مرفوضة', class: 'bg-red-500/20 text-red-400' },
    };
    const c = config[status] || config.draft;
    return <span className={`px-2 py-1 rounded-full text-xs ${c.class}`}>{c.label}</span>;
  };

  return (
    <div className="space-y-6" data-testid="invoices-page">
      {/* Header */}
      <div>
        <h1 className="text-ar-title flex items-center gap-3">
          <FileText className="w-8 h-8 text-primary" />
          الفواتير الإلكترونية
        </h1>
        <p className="text-muted-foreground">
          التحقق من امتثال الفواتير لمتطلبات هيئة الزكاة والضريبة والجمارك
        </p>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="finai-card">
            <div className="text-sm text-muted-foreground mb-1">إجمالي الفواتير</div>
            <div className="text-2xl font-bold number">{summary.total_invoices}</div>
          </div>
          <div className="finai-card bg-green-500/10">
            <div className="text-sm text-muted-foreground mb-1">معتمدة</div>
            <div className="text-2xl font-bold number text-green-400">
              {(summary.by_status?.validated || 0) + (summary.by_status?.cleared || 0)}
            </div>
          </div>
          <div className="finai-card bg-yellow-500/10">
            <div className="text-sm text-muted-foreground mb-1">قيد المراجعة</div>
            <div className="text-2xl font-bold number text-yellow-400">
              {summary.by_status?.draft || 0}
            </div>
          </div>
          <div className="finai-card">
            <div className="text-sm text-muted-foreground mb-1">نسبة الامتثال</div>
            <div className="text-2xl font-bold number text-primary">
              {summary.validated_percentage}%
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Invoices List */}
        <div className="lg:col-span-2">
          <div className="finai-card">
            <h2 className="text-lg font-semibold mb-4">قائمة الفواتير</h2>
            
            {isLoading ? (
              <div className="text-center py-8 text-muted-foreground">جاري التحميل...</div>
            ) : invoices.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                لا توجد فواتير مسجلة
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>رقم الفاتورة</th>
                      <th>المشتري</th>
                      <th>المبلغ</th>
                      <th>التاريخ</th>
                      <th>الحالة</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.map((invoice) => (
                      <tr 
                        key={invoice.id}
                        className={selectedInvoice === invoice.id ? 'bg-primary/10' : ''}
                        data-testid={`invoice-row-${invoice.invoice_number}`}
                      >
                        <td className="font-mono text-xs en-text">{invoice.invoice_number}</td>
                        <td>{invoice.buyer_name}</td>
                        <td className="number">{formatCurrency(invoice.total_including_vat)}</td>
                        <td className="number">{formatDate(invoice.issue_date)}</td>
                        <td>{getStatusBadge(invoice.status)}</td>
                        <td>
                          <button
                            onClick={() => setSelectedInvoice(invoice.id)}
                            className="p-1 hover:bg-secondary rounded"
                            data-testid={`validate-btn-${invoice.id}`}
                          >
                            <Eye className="w-4 h-4 text-muted-foreground" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Validation Panel */}
        <div className="lg:col-span-1">
          <div className="finai-card sticky top-6">
            <h2 className="text-lg font-semibold mb-4">نتيجة التحقق</h2>
            
            {!selectedInvoice ? (
              <div className="text-center py-8 text-muted-foreground">
                <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>اختر فاتورة للتحقق من صحتها</p>
              </div>
            ) : !validationData ? (
              <div className="text-center py-8 text-muted-foreground">
                جاري التحقق...
              </div>
            ) : (
              <div className="space-y-4">
                {/* Overall Status */}
                <div className={`p-4 rounded-lg ${
                  validationData.validation_status === 'validated' 
                    ? 'bg-green-500/10 border border-green-500/30' 
                    : validationData.validation_status === 'warning'
                    ? 'bg-yellow-500/10 border border-yellow-500/30'
                    : 'bg-red-500/10 border border-red-500/30'
                }`}>
                  <div className="flex items-center justify-between">
                    <span className="font-medium">حالة التحقق</span>
                    <span className={`font-bold ${
                      validationData.validation_status === 'validated' ? 'text-green-400' :
                      validationData.validation_status === 'warning' ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>
                      {validationData.validation_status === 'validated' ? 'مطابق' :
                       validationData.validation_status === 'warning' ? 'يحتاج مراجعة' : 'غير مطابق'}
                    </span>
                  </div>
                  <div className="mt-2 text-sm">
                    <span className="text-muted-foreground">درجة الامتثال: </span>
                    <span className="number font-bold">{validationData.compliance_score}%</span>
                  </div>
                </div>

                {/* Checks Summary */}
                <div className="text-sm">
                  <div className="flex justify-between mb-2">
                    <span className="text-muted-foreground">إجمالي الفحوصات</span>
                    <span className="number">{validationData.total_checks}</span>
                  </div>
                  <div className="flex justify-between mb-2">
                    <span className="text-green-400">ناجحة</span>
                    <span className="number">{validationData.passed_checks}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-red-400">فاشلة</span>
                    <span className="number">{validationData.failed_checks}</span>
                  </div>
                </div>

                {/* Validation Results */}
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {validationData.validation_results?.map((result, idx) => (
                    <div 
                      key={idx}
                      className={`p-2 rounded text-xs ${
                        result.is_valid 
                          ? 'bg-green-500/10 border border-green-500/20' 
                          : 'bg-red-500/10 border border-red-500/20'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        {result.is_valid ? (
                          <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                        )}
                        <div>
                          <div className={result.is_valid ? 'text-green-400' : 'text-red-400'}>
                            {result.message_ar}
                          </div>
                          {result.error_code && (
                            <div className="text-muted-foreground mt-1 en-text">
                              {result.error_code}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default InvoicesPage;
