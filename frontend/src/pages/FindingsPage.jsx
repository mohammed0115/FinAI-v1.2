/**
 * Audit Findings Page - صفحة ملاحظات التدقيق
 * List and filter audit findings with drill-down capability
 */
import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { 
  AlertTriangle, 
  Filter, 
  Search,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { useAuditFindings, useAuditFindingsDashboard } from '../lib/hooks';
import { AuditFindingCard } from '../components/findings/AuditFindingCard';
import { RiskBadge, RiskSummaryCard } from '../components/dashboard/RiskBadge';

const FindingsPage = ({ organizationId }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchTerm, setSearchTerm] = useState('');
  
  // Get filter values from URL
  const riskLevel = searchParams.get('risk_level') || '';
  const isResolved = searchParams.get('is_resolved') || 'false';
  const page = parseInt(searchParams.get('page') || '1');

  // Fetch data
  const { data: dashboardData } = useAuditFindingsDashboard();
  const { data: findingsData, isLoading } = useAuditFindings({
    organization_id: organizationId,
    risk_level: riskLevel || undefined,
    is_resolved: isResolved,
    page,
    page_size: 10,
  });

  const findings = findingsData?.results || [];
  const totalCount = findingsData?.count || 0;
  const totalPages = Math.ceil(totalCount / 10);

  // Filter handlers
  const updateFilter = (key, value) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    newParams.set('page', '1'); // Reset to first page
    setSearchParams(newParams);
  };

  const goToPage = (newPage) => {
    const newParams = new URLSearchParams(searchParams);
    newParams.set('page', String(newPage));
    setSearchParams(newParams);
  };

  return (
    <div className="space-y-6" data-testid="findings-page">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-ar-title flex items-center gap-3">
            <AlertTriangle className="w-8 h-8 text-yellow-400" />
            ملاحظات التدقيق
          </h1>
          <p className="text-muted-foreground">
            عرض وتصفية جميع ملاحظات التدقيق المكتشفة
          </p>
        </div>
        <div className="text-left">
          <div className="text-3xl font-bold number">{totalCount}</div>
          <div className="text-sm text-muted-foreground">إجمالي الملاحظات</div>
        </div>
      </div>

      {/* Risk Summary */}
      <RiskSummaryCard counts={dashboardData?.by_risk_level || {}} />

      {/* Filters */}
      <div className="finai-card">
        <div className="flex flex-wrap items-center gap-4">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type="text"
              placeholder="البحث في الملاحظات..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pr-10 pl-4 py-2 bg-secondary border border-border rounded-lg
                       focus:ring-2 focus:ring-primary text-sm"
              data-testid="search-input"
            />
          </div>

          {/* Risk Level Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-muted-foreground" />
            <select
              value={riskLevel}
              onChange={(e) => updateFilter('risk_level', e.target.value)}
              className="px-3 py-2 bg-secondary border border-border rounded-lg text-sm"
              data-testid="risk-filter"
            >
              <option value="">جميع المستويات</option>
              <option value="critical">حرج</option>
              <option value="high">مرتفع</option>
              <option value="medium">متوسط</option>
              <option value="low">منخفض</option>
            </select>
          </div>

          {/* Resolution Status */}
          <select
            value={isResolved}
            onChange={(e) => updateFilter('is_resolved', e.target.value)}
            className="px-3 py-2 bg-secondary border border-border rounded-lg text-sm"
            data-testid="status-filter"
          >
            <option value="false">غير محلولة</option>
            <option value="true">تم حلها</option>
            <option value="">الكل</option>
          </select>
        </div>
      </div>

      {/* Findings List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-muted-foreground">جاري التحميل...</div>
        </div>
      ) : findings.length === 0 ? (
        <div className="finai-card text-center py-12">
          <AlertTriangle className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">لا توجد ملاحظات تطابق معايير البحث</p>
        </div>
      ) : (
        <div className="space-y-4">
          {findings
            .filter(f => !searchTerm || 
              f.title_ar?.includes(searchTerm) || 
              f.finding_number?.includes(searchTerm)
            )
            .map((finding) => (
              <AuditFindingCard key={finding.id} finding={finding} />
            ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => goToPage(page - 1)}
            disabled={page <= 1}
            className="p-2 hover:bg-secondary rounded-lg disabled:opacity-50"
            data-testid="prev-page-btn"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
          
          <div className="flex items-center gap-1">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const pageNum = i + 1;
              return (
                <button
                  key={pageNum}
                  onClick={() => goToPage(pageNum)}
                  className={`w-10 h-10 rounded-lg text-sm number
                    ${page === pageNum 
                      ? 'bg-primary text-primary-foreground' 
                      : 'hover:bg-secondary'}`}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>
          
          <button
            onClick={() => goToPage(page + 1)}
            disabled={page >= totalPages}
            className="p-2 hover:bg-secondary rounded-lg disabled:opacity-50"
            data-testid="next-page-btn"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        </div>
      )}
    </div>
  );
};

export default FindingsPage;
