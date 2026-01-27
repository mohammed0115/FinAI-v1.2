/**
 * FinAI API Client - عميل واجهة برمجة التطبيقات
 * Read-only API integration for the auditor dashboard
 */
import axios from 'axios';

const API_BASE = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// Create axios instance
const api = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('finai_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('finai_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ============ AUTH ============
export const authApi = {
  login: async (email, password) => {
    const response = await api.post('/auth/token/', { email, password });
    return response.data;
  },
};

// ============ CORE ============
export const coreApi = {
  getOrganizations: async () => {
    const response = await api.get('/core/organizations/');
    return response.data;
  },
  getOrganizationStats: async (orgId) => {
    const response = await api.get(`/core/organizations/${orgId}/stats/`);
    return response.data;
  },
};

// ============ DOCUMENTS ============
export const documentsApi = {
  getAccounts: async (params = {}) => {
    const response = await api.get('/documents/accounts/', { params });
    return response.data;
  },
  getAccountsByType: async (orgId) => {
    const response = await api.get('/documents/accounts/by_type/', { 
      params: { organization_id: orgId } 
    });
    return response.data;
  },
  getTrialBalance: async (orgId) => {
    const response = await api.get('/documents/accounts/trial_balance/', {
      params: { organization_id: orgId }
    });
    return response.data;
  },
  getTransactions: async (params = {}) => {
    const response = await api.get('/documents/transactions/', { params });
    return response.data;
  },
  getTransactionsSummary: async (orgId) => {
    const response = await api.get('/documents/transactions/summary/', {
      params: { organization_id: orgId }
    });
    return response.data;
  },
  getAuditFlags: async (params = {}) => {
    const response = await api.get('/documents/audit-flags/', { params });
    return response.data;
  },
  getAuditFlagsDashboard: async () => {
    const response = await api.get('/documents/audit-flags/dashboard/');
    return response.data;
  },
};

// ============ COMPLIANCE ============
export const complianceApi = {
  // Dashboard
  getDashboardOverview: async (orgId) => {
    const response = await api.get('/compliance/dashboard/overview/', {
      params: orgId ? { organization_id: orgId } : {}
    });
    return response.data;
  },
  
  // Regulatory References
  getRegulatoryReferences: async (params = {}) => {
    const response = await api.get('/compliance/regulatory-references/', { params });
    return response.data;
  },
  
  // ZATCA Invoices
  getZATCAInvoices: async (params = {}) => {
    const response = await api.get('/compliance/zatca-invoices/', { params });
    return response.data;
  },
  getZATCAInvoice: async (id) => {
    const response = await api.get(`/compliance/zatca-invoices/${id}/`);
    return response.data;
  },
  validateZATCAInvoice: async (id) => {
    const response = await api.get(`/compliance/zatca-invoices/${id}/validate/`);
    return response.data;
  },
  getZATCAComplianceSummary: async () => {
    const response = await api.get('/compliance/zatca-invoices/compliance_summary/');
    return response.data;
  },
  
  // VAT Reconciliation
  getVATReconciliations: async (params = {}) => {
    const response = await api.get('/compliance/vat-reconciliations/', { params });
    return response.data;
  },
  getVATReconciliation: async (id) => {
    const response = await api.get(`/compliance/vat-reconciliations/${id}/`);
    return response.data;
  },
  getVATVarianceReport: async (orgId) => {
    const response = await api.get('/compliance/vat-reconciliations/variance_report/', {
      params: orgId ? { organization_id: orgId } : {}
    });
    return response.data;
  },
  
  // Zakat
  getZakatCalculations: async (params = {}) => {
    const response = await api.get('/compliance/zakat-calculations/', { params });
    return response.data;
  },
  getZakatCalculation: async (id) => {
    const response = await api.get(`/compliance/zakat-calculations/${id}/`);
    return response.data;
  },
  
  // Audit Findings
  getAuditFindings: async (params = {}) => {
    const response = await api.get('/compliance/audit-findings/', { params });
    return response.data;
  },
  getAuditFinding: async (id) => {
    const response = await api.get(`/compliance/audit-findings/${id}/`);
    return response.data;
  },
  getAuditFindingsDashboard: async () => {
    const response = await api.get('/compliance/audit-findings/dashboard/');
    return response.data;
  },
  generateArabicReport: async (orgId, periodStart, periodEnd) => {
    const response = await api.get('/compliance/audit-findings/generate_report_ar/', {
      params: { 
        organization_id: orgId,
        period_start: periodStart,
        period_end: periodEnd
      }
    });
    return response.data;
  },
};

// ============ ANALYTICS ============
export const analyticsApi = {
  getKPIs: async (orgId, period = 'month') => {
    const response = await api.get('/analytics/kpis/', {
      params: { organization_id: orgId, period }
    });
    return response.data;
  },
};

// ============ REPORTS ============
export const reportsApi = {
  getReports: async (params = {}) => {
    const response = await api.get('/reports/reports/', { params });
    return response.data;
  },
  getInsights: async (params = {}) => {
    const response = await api.get('/reports/insights/', { params });
    return response.data;
  },
};

export default api;
