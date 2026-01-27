/**
 * Zakat Page - صفحة الزكاة
 * View Zakat calculations and discrepancies
 */
import React from 'react';
import { Calculator, Info, AlertTriangle } from 'lucide-react';
import { useZakatCalculations } from '../lib/hooks';
import { ComplianceProgressBar } from '../components/dashboard/ComplianceScore';
import { RiskBadge } from '../components/dashboard/RiskBadge';

const ZakatPage = ({ organizationId }) => {
  const { data: zakatData, isLoading } = useZakatCalculations({
    organization_id: organizationId,
  });

  const calculations = zakatData?.results || [];

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ar-SA', {
      style: 'currency',
      currency: 'SAR',
      minimumFractionDigits: 0,
    }).format(amount || 0);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('ar-SA', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="space-y-6" data-testid="zakat-page">
      {/* Header */}
      <div>
        <h1 className="text-ar-title flex items-center gap-3">
          <Calculator className="w-8 h-8 text-primary" />
          الزكاة
        </h1>
        <p className="text-muted-foreground">
          حساب الزكاة السنوي ومقارنتها بضريبة الدخل
        </p>
      </div>

      {/* Info Banner */}
      <div className="finai-card bg-primary/5 border-primary/20">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-primary mt-0.5" />
          <div>
            <div className="font-medium text-primary">نسبة الزكاة</div>
            <div className="text-sm text-muted-foreground">
              تُحسب الزكاة بنسبة 2.5% من الوعاء الزكوي السنوي وفقاً لنظام جباية الزكاة الصادر من هيئة الزكاة والضريبة والجمارك
            </div>
          </div>
        </div>
      </div>

      {/* Calculations List */}
      {isLoading ? (
        <div className="finai-card text-center py-8 text-muted-foreground">
          جاري التحميل...
        </div>
      ) : calculations.length === 0 ? (
        <div className="finai-card text-center py-8">
          <Calculator className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">لا توجد حسابات زكاة مسجلة</p>
        </div>
      ) : (
        <div className="space-y-6">
          {calculations.map((calc) => (
            <div 
              key={calc.id} 
              className="finai-card"
              data-testid={`zakat-calc-${calc.id}`}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h3 className="text-lg font-semibold">
                    السنة المالية {new Date(calc.fiscal_year_end).getFullYear()}
                  </h3>
                  <div className="text-sm text-muted-foreground">
                    {formatDate(calc.fiscal_year_start)} - {formatDate(calc.fiscal_year_end)}
                  </div>
                </div>
                <div className={`px-3 py-1 rounded-full text-sm ${
                  calc.status === 'submitted' || calc.status === 'assessed' 
                    ? 'bg-green-500/20 text-green-400' 
                    : 'bg-yellow-500/20 text-yellow-400'
                }`}>
                  {calc.status_display || calc.status}
                </div>
              </div>

              {/* Zakat Calculation Breakdown */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Positive Base */}
                <div className="space-y-3">
                  <h4 className="text-sm font-medium text-muted-foreground border-b border-border pb-2">
                    الوعاء الزكوي الإيجابي
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>إجمالي حقوق الملكية</span>
                      <span className="number">{formatCurrency(calc.total_equity)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>الالتزامات طويلة الأجل</span>
                      <span className="number">{formatCurrency(calc.long_term_liabilities)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>المخصصات</span>
                      <span className="number">{formatCurrency(calc.provisions)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>صافي الربح المعدل</span>
                      <span className="number">{formatCurrency(calc.adjusted_net_profit)}</span>
                    </div>
                    <div className="flex justify-between font-medium pt-2 border-t border-border">
                      <span>الإجمالي</span>
                      <span className="number text-primary">{formatCurrency(calc.positive_zakat_base)}</span>
                    </div>
                  </div>
                </div>

                {/* Deductions */}
                <div className="space-y-3">
                  <h4 className="text-sm font-medium text-muted-foreground border-b border-border pb-2">
                    الحسومات
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>الأصول الثابتة</span>
                      <span className="number text-red-400">({formatCurrency(calc.fixed_assets)})</span>
                    </div>
                    <div className="flex justify-between">
                      <span>الخسائر المتراكمة</span>
                      <span className="number text-red-400">({formatCurrency(calc.accumulated_losses)})</span>
                    </div>
                    <div className="flex justify-between font-medium pt-2 border-t border-border">
                      <span>إجمالي الحسومات</span>
                      <span className="number text-red-400">({formatCurrency(calc.total_deductions)})</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Final Calculation */}
              <div className="mt-6 p-4 bg-secondary/50 rounded-lg">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="text-sm text-muted-foreground mb-1">الوعاء الزكوي الصافي</div>
                    <div className="text-2xl font-bold number">{formatCurrency(calc.net_zakat_base)}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm text-muted-foreground mb-1">نسبة الزكاة</div>
                    <div className="text-2xl font-bold number">2.5%</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm text-muted-foreground mb-1">الزكاة المستحقة</div>
                    <div className="text-2xl font-bold number text-primary">{formatCurrency(calc.zakat_due)}</div>
                  </div>
                </div>
              </div>

              {/* Zakat vs Tax Comparison */}
              {calc.zakat_tax_difference !== 0 && (
                <div className="mt-4 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                  <h4 className="text-sm font-medium text-blue-400 mb-2">مقارنة الزكاة بضريبة الدخل</h4>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">الزكاة: </span>
                      <span className="number">{formatCurrency(calc.zakat_due)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">ضريبة الدخل: </span>
                      <span className="number">{formatCurrency(calc.income_tax_due)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">الفرق: </span>
                      <span className={`number ${calc.zakat_tax_difference > 0 ? 'text-yellow-400' : 'text-green-400'}`}>
                        {formatCurrency(Math.abs(calc.zakat_tax_difference))}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Compliance Score */}
              <div className="mt-4">
                <ComplianceProgressBar 
                  score={calc.compliance_score || 0} 
                  label_ar="درجة الامتثال" 
                />
              </div>

              {/* Discrepancies */}
              {calc.discrepancies && calc.discrepancies.length > 0 && (
                <div className="mt-4 space-y-2">
                  <h4 className="text-sm font-medium text-yellow-400 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" />
                    التفاوتات المكتشفة
                  </h4>
                  {calc.discrepancies.map((disc, idx) => (
                    <div key={idx} className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="text-sm">{disc.description_ar}</div>
                          <div className="text-xs text-muted-foreground mt-1">
                            التأثير على الزكاة: <span className="number">{formatCurrency(disc.impact_on_zakat)}</span>
                          </div>
                        </div>
                        <RiskBadge level={disc.risk_level} size="small" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ZakatPage;
