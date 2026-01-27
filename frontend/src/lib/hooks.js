/**
 * React Query Hooks for FinAI API
 * خطافات React Query لواجهة برمجة التطبيقات
 */
import { useQuery } from '@tanstack/react-query';
import { 
  coreApi, 
  documentsApi, 
  complianceApi, 
  analyticsApi, 
  reportsApi 
} from './api';

// ============ CORE HOOKS ============
export const useOrganizations = () => {
  return useQuery({
    queryKey: ['organizations'],
    queryFn: coreApi.getOrganizations,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useOrganizationStats = (orgId) => {
  return useQuery({
    queryKey: ['organization-stats', orgId],
    queryFn: () => coreApi.getOrganizationStats(orgId),
    enabled: !!orgId,
  });
};

// ============ DOCUMENTS HOOKS ============
export const useAccounts = (params) => {
  return useQuery({
    queryKey: ['accounts', params],
    queryFn: () => documentsApi.getAccounts(params),
  });
};

export const useAccountsByType = (orgId) => {
  return useQuery({
    queryKey: ['accounts-by-type', orgId],
    queryFn: () => documentsApi.getAccountsByType(orgId),
    enabled: !!orgId,
  });
};

export const useTrialBalance = (orgId) => {
  return useQuery({
    queryKey: ['trial-balance', orgId],
    queryFn: () => documentsApi.getTrialBalance(orgId),
    enabled: !!orgId,
  });
};

export const useTransactions = (params) => {
  return useQuery({
    queryKey: ['transactions', params],
    queryFn: () => documentsApi.getTransactions(params),
  });
};

export const useTransactionsSummary = (orgId) => {
  return useQuery({
    queryKey: ['transactions-summary', orgId],
    queryFn: () => documentsApi.getTransactionsSummary(orgId),
    enabled: !!orgId,
  });
};

export const useAuditFlags = (params) => {
  return useQuery({
    queryKey: ['audit-flags', params],
    queryFn: () => documentsApi.getAuditFlags(params),
  });
};

export const useAuditFlagsDashboard = () => {
  return useQuery({
    queryKey: ['audit-flags-dashboard'],
    queryFn: documentsApi.getAuditFlagsDashboard,
  });
};

// ============ COMPLIANCE HOOKS ============
export const useComplianceDashboard = (orgId) => {
  return useQuery({
    queryKey: ['compliance-dashboard', orgId],
    queryFn: () => complianceApi.getDashboardOverview(orgId),
    refetchInterval: 60 * 1000, // Refresh every minute
  });
};

export const useRegulatoryReferences = (params) => {
  return useQuery({
    queryKey: ['regulatory-references', params],
    queryFn: () => complianceApi.getRegulatoryReferences(params),
    staleTime: 30 * 60 * 1000, // 30 minutes (rarely changes)
  });
};

export const useZATCAInvoices = (params) => {
  return useQuery({
    queryKey: ['zatca-invoices', params],
    queryFn: () => complianceApi.getZATCAInvoices(params),
  });
};

export const useZATCAInvoice = (id) => {
  return useQuery({
    queryKey: ['zatca-invoice', id],
    queryFn: () => complianceApi.getZATCAInvoice(id),
    enabled: !!id,
  });
};

export const useZATCAValidation = (id) => {
  return useQuery({
    queryKey: ['zatca-validation', id],
    queryFn: () => complianceApi.validateZATCAInvoice(id),
    enabled: !!id,
  });
};

export const useZATCAComplianceSummary = () => {
  return useQuery({
    queryKey: ['zatca-compliance-summary'],
    queryFn: complianceApi.getZATCAComplianceSummary,
  });
};

export const useVATReconciliations = (params) => {
  return useQuery({
    queryKey: ['vat-reconciliations', params],
    queryFn: () => complianceApi.getVATReconciliations(params),
  });
};

export const useVATReconciliation = (id) => {
  return useQuery({
    queryKey: ['vat-reconciliation', id],
    queryFn: () => complianceApi.getVATReconciliation(id),
    enabled: !!id,
  });
};

export const useVATVarianceReport = (orgId) => {
  return useQuery({
    queryKey: ['vat-variance-report', orgId],
    queryFn: () => complianceApi.getVATVarianceReport(orgId),
  });
};

export const useZakatCalculations = (params) => {
  return useQuery({
    queryKey: ['zakat-calculations', params],
    queryFn: () => complianceApi.getZakatCalculations(params),
  });
};

export const useZakatCalculation = (id) => {
  return useQuery({
    queryKey: ['zakat-calculation', id],
    queryFn: () => complianceApi.getZakatCalculation(id),
    enabled: !!id,
  });
};

export const useAuditFindings = (params) => {
  return useQuery({
    queryKey: ['audit-findings', params],
    queryFn: () => complianceApi.getAuditFindings(params),
  });
};

export const useAuditFinding = (id) => {
  return useQuery({
    queryKey: ['audit-finding', id],
    queryFn: () => complianceApi.getAuditFinding(id),
    enabled: !!id,
  });
};

export const useAuditFindingsDashboard = () => {
  return useQuery({
    queryKey: ['audit-findings-dashboard'],
    queryFn: complianceApi.getAuditFindingsDashboard,
  });
};

export const useArabicAuditReport = (orgId, periodStart, periodEnd) => {
  return useQuery({
    queryKey: ['arabic-audit-report', orgId, periodStart, periodEnd],
    queryFn: () => complianceApi.generateArabicReport(orgId, periodStart, periodEnd),
    enabled: !!orgId,
  });
};

// ============ ANALYTICS HOOKS ============
export const useKPIs = (orgId, period = 'month') => {
  return useQuery({
    queryKey: ['kpis', orgId, period],
    queryFn: () => analyticsApi.getKPIs(orgId, period),
    enabled: !!orgId,
  });
};

// ============ REPORTS HOOKS ============
export const useReports = (params) => {
  return useQuery({
    queryKey: ['reports', params],
    queryFn: () => reportsApi.getReports(params),
  });
};

export const useInsights = (params) => {
  return useQuery({
    queryKey: ['insights', params],
    queryFn: () => reportsApi.getInsights(params),
  });
};
