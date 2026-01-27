/**
 * Arabic Reports Page - صفحة التقارير العربية
 * View and export Arabic audit reports
 */
import React, { useState, useRef } from 'react';
import { FileText, Download, Calendar, Building2, Printer } from 'lucide-react';
import { useArabicAuditReport, useOrganizations } from '../lib/hooks';
import { RiskBadge } from '../components/dashboard/RiskBadge';

const ReportsPage = ({ organizationId }) => {
  const reportRef = useRef(null);
  const { data: orgsData } = useOrganizations();
  
  // Date range state
  const today = new Date();
  const oneYearAgo = new Date(today.getFullYear() - 1, today.getMonth(), today.getDate());
  
  const [selectedOrg, setSelectedOrg] = useState(organizationId);
  const [periodStart, setPeriodStart] = useState(oneYearAgo.toISOString().split('T')[0]);
  const [periodEnd, setPeriodEnd] = useState(today.toISOString().split('T')[0]);

  const { data: report, isLoading, refetch } = useArabicAuditReport(
    selectedOrg,
    periodStart,
    periodEnd
  );

  const organizations = orgsData?.results || [];

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('ar-SA', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ar-SA', {
      style: 'currency',
      currency: 'SAR',
      minimumFractionDigits: 0,
    }).format(amount || 0);
  };

  const handlePrint = () => {
    window.print();
  };

  const getRiskColor = (rating) => {
    const colors = {
      'حرج': 'text-red-400',
      'مرتفع': 'text-orange-400',
      'متوسط': 'text-yellow-400',
      'منخفض': 'text-green-400',
    };
    return colors[rating] || 'text-muted-foreground';
  };

  return (
    <div className="space-y-6" data-testid="reports-page">
      {/* Header */}
      <div className="flex items-start justify-between no-print">
        <div>
          <h1 className="text-ar-title flex items-center gap-3">
            <FileText className="w-8 h-8 text-primary" />
            التقارير العربية
          </h1>
          <p className="text-muted-foreground">
            إنشاء وعرض تقارير التدقيق الرسمية باللغة العربية
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="finai-card no-print">
        <div className="flex flex-wrap items-end gap-4">
          {/* Organization */}
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium mb-2">المنشأة</label>
            <select
              value={selectedOrg || ''}
              onChange={(e) => setSelectedOrg(e.target.value)}
              className="w-full px-3 py-2 bg-secondary border border-border rounded-lg"
              data-testid="org-select"
            >
              <option value="">اختر المنشأة</option>
              {organizations.map((org) => (
                <option key={org.id} value={org.id}>{org.name}</option>
              ))}
            </select>
          </div>

          {/* Period Start */}
          <div>
            <label className="block text-sm font-medium mb-2">من تاريخ</label>
            <input
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              className="px-3 py-2 bg-secondary border border-border rounded-lg"
              data-testid="period-start"
            />
          </div>

          {/* Period End */}
          <div>
            <label className="block text-sm font-medium mb-2">إلى تاريخ</label>
            <input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              className="px-3 py-2 bg-secondary border border-border rounded-lg"
              data-testid="period-end"
            />
          </div>

          {/* Generate Button */}
          <button
            onClick={() => refetch()}
            disabled={!selectedOrg}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-lg 
                     hover:bg-primary/90 disabled:opacity-50"
            data-testid="generate-report-btn"
          >
            إنشاء التقرير
          </button>

          {/* Print Button */}
          {report && (
            <button
              onClick={handlePrint}
              className="px-4 py-2 bg-secondary text-foreground rounded-lg hover:bg-secondary/80
                       flex items-center gap-2"
              data-testid="print-btn"
            >
              <Printer className="w-4 h-4" />
              طباعة
            </button>
          )}
        </div>
      </div>

      {/* Report Content */}
      {isLoading ? (
        <div className="finai-card text-center py-12 text-muted-foreground">
          جاري إنشاء التقرير...
        </div>
      ) : !report ? (
        <div className="finai-card text-center py-12">
          <FileText className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">اختر المنشأة والفترة لإنشاء التقرير</p>
        </div>
      ) : (
        <div 
          ref={reportRef}
          className="finai-card bg-white text-gray-900 print:shadow-none"
          style={{ direction: 'rtl' }}
          data-testid="report-content"
        >
          {/* Report Header */}
          <div className="text-center border-b-2 border-gray-300 pb-6 mb-6">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              {report.report_title_ar}
            </h1>
            <div className="text-sm text-gray-600 space-y-1">
              <div>رقم التقرير: <span className="en-text">{report.report_number}</span></div>
              <div>تاريخ التقرير: {formatDate(report.report_date)}</div>
            </div>
          </div>

          {/* Organization Info */}
          <div className="bg-gray-50 p-4 rounded-lg mb-6">
            <div className="flex items-center gap-2 mb-2">
              <Building2 className="w-5 h-5 text-gray-600" />
              <span className="font-medium">بيانات المنشأة</span>
            </div>
            <div className="text-sm text-gray-700 space-y-1">
              <div>الاسم: {report.organization_name}</div>
              <div>الرقم الضريبي: <span className="en-text">{report.organization_tax_id}</span></div>
              <div>فترة التقرير: {formatDate(report.period_start)} - {formatDate(report.period_end)}</div>
            </div>
          </div>

          {/* Executive Summary */}
          <div className="mb-6">
            <h2 className="text-lg font-bold text-gray-900 border-b border-gray-300 pb-2 mb-4">
              الملخص التنفيذي
            </h2>
            <div className="whitespace-pre-line text-gray-700 leading-loose">
              {report.executive_summary_ar}
            </div>
          </div>

          {/* Key Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-50 p-4 rounded-lg text-center">
              <div className="text-2xl font-bold text-blue-600 number">
                {report.overall_compliance_score}%
              </div>
              <div className="text-xs text-gray-600">درجة الامتثال</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg text-center">
              <div className={`text-2xl font-bold ${getRiskColor(report.risk_rating)}`}>
                {report.risk_rating}
              </div>
              <div className="text-xs text-gray-600">مستوى المخاطر</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg text-center">
              <div className="text-2xl font-bold text-gray-900 number">
                {report.total_findings}
              </div>
              <div className="text-xs text-gray-600">إجمالي الملاحظات</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg text-center">
              <div className="text-2xl font-bold text-red-600 number">
                {formatCurrency(report.total_financial_impact)}
              </div>
              <div className="text-xs text-gray-600">التأثير المالي</div>
            </div>
          </div>

          {/* Findings Summary */}
          <div className="mb-6">
            <h2 className="text-lg font-bold text-gray-900 border-b border-gray-300 pb-2 mb-4">
              ملخص الملاحظات
            </h2>
            <div className="grid grid-cols-4 gap-2 text-center text-sm">
              <div className="bg-red-50 p-3 rounded">
                <div className="text-xl font-bold text-red-600 number">{report.critical_findings}</div>
                <div className="text-red-700">حرج</div>
              </div>
              <div className="bg-orange-50 p-3 rounded">
                <div className="text-xl font-bold text-orange-600 number">{report.high_risk_findings}</div>
                <div className="text-orange-700">مرتفع</div>
              </div>
              <div className="bg-yellow-50 p-3 rounded">
                <div className="text-xl font-bold text-yellow-600 number">{report.medium_risk_findings}</div>
                <div className="text-yellow-700">متوسط</div>
              </div>
              <div className="bg-green-50 p-3 rounded">
                <div className="text-xl font-bold text-green-600 number">{report.low_risk_findings}</div>
                <div className="text-green-700">منخفض</div>
              </div>
            </div>
          </div>

          {/* Detailed Findings */}
          {report.findings && report.findings.length > 0 && (
            <div className="mb-6">
              <h2 className="text-lg font-bold text-gray-900 border-b border-gray-300 pb-2 mb-4">
                تفاصيل الملاحظات
              </h2>
              <div className="space-y-4">
                {report.findings.map((finding, idx) => (
                  <div key={idx} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div className="font-medium text-gray-900">{finding.title_ar}</div>
                      <span className={`px-2 py-1 rounded text-xs ${
                        finding.risk_level === 'critical' ? 'bg-red-100 text-red-700' :
                        finding.risk_level === 'high' ? 'bg-orange-100 text-orange-700' :
                        finding.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-green-100 text-green-700'
                      }`}>
                        {finding.risk_level === 'critical' ? 'حرج' :
                         finding.risk_level === 'high' ? 'مرتفع' :
                         finding.risk_level === 'medium' ? 'متوسط' : 'منخفض'}
                      </span>
                    </div>
                    {finding.description_ar && (
                      <p className="text-sm text-gray-600 mb-2">{finding.description_ar}</p>
                    )}
                    {finding.financial_impact > 0 && (
                      <div className="text-sm text-gray-500">
                        التأثير المالي: <span className="number">{formatCurrency(finding.financial_impact)}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {report.recommendations_ar && report.recommendations_ar.length > 0 && (
            <div className="mb-6">
              <h2 className="text-lg font-bold text-gray-900 border-b border-gray-300 pb-2 mb-4">
                التوصيات
              </h2>
              <ul className="list-disc list-inside space-y-2 text-gray-700">
                {report.recommendations_ar.map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Conclusion */}
          <div className="mb-6">
            <h2 className="text-lg font-bold text-gray-900 border-b border-gray-300 pb-2 mb-4">
              الخلاصة
            </h2>
            <div className="whitespace-pre-line text-gray-700 leading-loose">
              {report.conclusion_ar}
            </div>
          </div>

          {/* Signature Block */}
          <div className="border-t-2 border-gray-300 pt-6 mt-6">
            <div className="grid grid-cols-2 gap-8">
              <div>
                <div className="text-sm text-gray-600 mb-4">المدقق</div>
                <div className="border-b border-gray-400 h-12"></div>
                <div className="text-sm text-gray-500 mt-2">التوقيع والتاريخ</div>
              </div>
              <div>
                <div className="text-sm text-gray-600 mb-4">المراجع</div>
                <div className="border-b border-gray-400 h-12"></div>
                <div className="text-sm text-gray-500 mt-2">التوقيع والتاريخ</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportsPage;
