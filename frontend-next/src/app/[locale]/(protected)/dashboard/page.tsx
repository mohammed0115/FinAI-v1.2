"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshCw, ShieldCheck, TriangleAlert, Wallet, Zap } from "lucide-react";
import { useLocale } from "next-intl";
import Badge from "@/src/components/ui/Badge";
import Button from "@/src/components/ui/Button";
import Card from "@/src/components/ui/Card";
import Alert from "@/src/components/ui/Alert";
import DataTable from "@/src/components/data/DataTable";
import EmptyState from "@/src/components/data/EmptyState";
import LoadingState from "@/src/components/data/LoadingState";
import PageHeader from "@/src/components/shell/PageHeader";
import Section from "@/src/components/shell/Section";
import LtrIsland from "@/src/components/common/LtrIsland";
import { useAuthContext } from "@/src/components/auth/AuthContext";

type ComplianceModule = {
  score?: number;
};

type OverviewResponse = {
  overall_compliance_score?: number;
  vat_compliance?: ComplianceModule & {
    reconciliations?: number;
    with_variance?: number;
  };
  zatca_compliance?: ComplianceModule & {
    total_invoices?: number;
    validated?: number;
  };
  audit_findings?: {
    total?: number;
    unresolved?: number;
    critical_unresolved?: number;
    high_unresolved?: number;
  };
  risk_level?: {
    level_ar?: string;
    level?: string;
  };
};

type TransactionSummaryResponse = {
  total_income?: number;
  total_expenses?: number;
  net_income?: number;
  anomaly_count?: number;
  unreconciled_count?: number;
};

type FindingsDashboardResponse = {
  total_findings?: number;
  unresolved_findings?: number;
  by_risk_level?: Record<string, number>;
};

type ApiBundle = {
  overview: OverviewResponse | null;
  transactions: TransactionSummaryResponse | null;
  findings: FindingsDashboardResponse | null;
};

async function fetchJson<T>(url: string, token: string): Promise<Response> {
  return fetch(url, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
    },
    cache: "no-store",
  });
}

export default function DashboardPage() {
  const locale = useLocale();
  const isArabic = locale === "ar";
  const { accessToken, refreshToken, setTokens, clearTokens } = useAuthContext();

  const [data, setData] = useState<ApiBundle | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshAccessToken = useCallback(async () => {
    if (!refreshToken) {
      return null;
    }

    const refreshResponse = await fetch("/api/auth/token/refresh/", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    if (refreshResponse.status === 401) {
      clearTokens();
      return null;
    }

    if (!refreshResponse.ok) {
      return null;
    }

    const refreshBody = (await refreshResponse.json()) as {
      access?: string;
      refresh?: string;
    };

    if (!refreshBody.access) {
      return null;
    }

    setTokens(refreshBody.access, refreshBody.refresh ?? refreshToken);
    return refreshBody.access;
  }, [clearTokens, refreshToken, setTokens]);

  const runProtectedRequest = useCallback(
    async <T,>(url: string): Promise<T | null> => {
      if (!accessToken) {
        return null;
      }

      let response = await fetchJson<T>(url, accessToken);

      if (response.status !== 401) {
        return response.ok ? ((await response.json()) as T) : null;
      }

      const nextAccessToken = await refreshAccessToken();
      if (!nextAccessToken) {
        return null;
      }

      response = await fetchJson<T>(url, nextAccessToken);
      return response.ok ? ((await response.json()) as T) : null;
    },
    [accessToken, refreshAccessToken],
  );

  const loadDashboard = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [overview, transactions, findings] = await Promise.all([
        runProtectedRequest<OverviewResponse>("/api/compliance/dashboard/overview/"),
        runProtectedRequest<TransactionSummaryResponse>("/api/documents/transactions/summary/"),
        runProtectedRequest<FindingsDashboardResponse>("/api/compliance/audit-findings/dashboard/"),
      ]);

      setData({ overview, transactions, findings });
    } catch {
      setError(isArabic ? "تعذر تحميل بيانات لوحة التحكم." : "Unable to load dashboard data.");
    } finally {
      setIsLoading(false);
    }
  }, [isArabic, runProtectedRequest]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const riskRows = useMemo(() => {
    const map = data?.findings?.by_risk_level ?? {};
    return Object.entries(map).map(([risk, count]) => ({ risk, count }));
  }, [data?.findings?.by_risk_level]);

  const complianceRows = useMemo(() => {
    const rows = [];
    if (data?.overview?.zatca_compliance) {
      rows.push({
        module: isArabic ? "ZATCA" : "ZATCA",
        score: data.overview.zatca_compliance.score ?? null,
        extra:
          data.overview.zatca_compliance.total_invoices != null
            ? `${data.overview.zatca_compliance.validated ?? 0}/${data.overview.zatca_compliance.total_invoices}`
            : null,
      });
    }
    if (data?.overview?.vat_compliance) {
      rows.push({
        module: isArabic ? "ضريبة القيمة المضافة" : "VAT",
        score: data.overview.vat_compliance.score ?? null,
        extra:
          data.overview.vat_compliance.reconciliations != null
            ? `${data.overview.vat_compliance.with_variance ?? 0}/${data.overview.vat_compliance.reconciliations}`
            : null,
      });
    }
    return rows;
  }, [data?.overview?.vat_compliance, data?.overview?.zatca_compliance, isArabic]);

  if (isLoading) {
    return <LoadingState className="min-h-[18rem]" />;
  }

  if (!data?.overview && !data?.transactions && !data?.findings) {
    return (
      <EmptyState
        title={isArabic ? "لا توجد بيانات للوحة التحكم" : "No dashboard data"}
        description={
          isArabic
            ? "تأكد من تسجيل الدخول ووجود بيانات في النظام."
            : "Sign in and verify that data exists in the system."
        }
      />
    );
  }

  return (
    <div>
      <PageHeader
        title={isArabic ? "لوحة التحكم" : "Dashboard"}
        description={
          isArabic
            ? "نظرة عامة على الامتثال والمعاملات والمخاطر"
            : "Overview of compliance, transactions, and risk"
        }
        action={
          <Button variant="primary" onClick={loadDashboard} icon={<RefreshCw className="h-4 w-4" />}>
            {isArabic ? "تحديث" : "Refresh"}
          </Button>
        }
      />

      {error ? (
        <Section>
          <Alert tone="warning" title={isArabic ? "تنبيه" : "Notice"}>
            {error}
          </Alert>
        </Section>
      ) : null}

      <Section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm text-app-textSecondary">{isArabic ? "درجة الامتثال" : "Compliance score"}</p>
            <ShieldCheck className="h-5 w-5 text-app-primaryFrom" />
          </div>
          <p className="text-3xl font-bold text-app-text">
            <LtrIsland>{data?.overview?.overall_compliance_score ?? "--"}%</LtrIsland>
          </p>
          <div className="mt-3">
            <Badge tone="info">{data?.overview?.risk_level?.level_ar ?? data?.overview?.risk_level?.level ?? "--"}</Badge>
          </div>
        </Card>

        <Card className="p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm text-app-textSecondary">{isArabic ? "الإيرادات" : "Income"}</p>
            <Wallet className="h-5 w-5 text-emerald-600" />
          </div>
          <p className="text-3xl font-bold text-app-text">
            <LtrIsland>{(data?.transactions?.total_income ?? 0).toLocaleString()}</LtrIsland>
          </p>
        </Card>

        <Card className="p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm text-app-textSecondary">{isArabic ? "صافي الربح" : "Net income"}</p>
            <Zap className="h-5 w-5 text-app-primaryTo" />
          </div>
          <p className="text-3xl font-bold text-app-text">
            <LtrIsland>{(data?.transactions?.net_income ?? 0).toLocaleString()}</LtrIsland>
          </p>
        </Card>

        <Card className="p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm text-app-textSecondary">{isArabic ? "حالات شاذة" : "Anomalies"}</p>
            <TriangleAlert className="h-5 w-5 text-amber-600" />
          </div>
          <p className="text-3xl font-bold text-app-text">
            <LtrIsland>{data?.transactions?.anomaly_count ?? 0}</LtrIsland>
          </p>
        </Card>
      </Section>

      <Section className="grid gap-4 xl:grid-cols-2">
        <Card className="p-4">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-app-text">{isArabic ? "وحدات الامتثال" : "Compliance modules"}</h2>
            <Badge tone="neutral">{isArabic ? "مباشر" : "Live"}</Badge>
          </div>
          <DataTable
            rows={complianceRows}
            rowKey={(row) => row.module}
            emptyState={
              <EmptyState
                title={isArabic ? "لا توجد بيانات امتثال" : "No compliance data"}
                description={isArabic ? "ستظهر النتائج هنا عند توفرها." : "Results will appear here when available."}
              />
            }
            columns={[
              {
                key: "module",
                header: isArabic ? "الوحدة" : "Module",
                render: (row) => <span className="font-medium text-app-text">{row.module}</span>,
              },
              {
                key: "score",
                header: isArabic ? "الدرجة" : "Score",
                render: (row) => <LtrIsland>{row.score ?? "--"}%</LtrIsland>,
              },
              {
                key: "extra",
                header: isArabic ? "الحالة" : "Status",
                render: (row) => <LtrIsland>{row.extra ?? "--"}</LtrIsland>,
              },
            ]}
          />
        </Card>

        <Card className="p-4">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-app-text">{isArabic ? "توزيع المخاطر" : "Risk distribution"}</h2>
            <Badge tone="warning">
              <LtrIsland>{data?.findings?.unresolved_findings ?? 0}</LtrIsland>
            </Badge>
          </div>
          <DataTable
            rows={riskRows}
            rowKey={(row) => row.risk}
            emptyState={
              <EmptyState
                title={isArabic ? "لا توجد مخاطر مسجلة" : "No risk records"}
                description={isArabic ? "سيظهر التوزيع عند توفر نتائج تدقيق." : "Distribution appears when findings are available."}
              />
            }
            columns={[
              {
                key: "risk",
                header: isArabic ? "المستوى" : "Level",
                render: (row) => <span className="font-medium text-app-text">{row.risk}</span>,
              },
              {
                key: "count",
                header: isArabic ? "العدد" : "Count",
                render: (row) => <LtrIsland>{row.count}</LtrIsland>,
              },
            ]}
          />
        </Card>
      </Section>

      <Section className="grid gap-4 xl:grid-cols-2">
        <Card className="p-4">
          <h2 className="mb-3 text-base font-semibold text-app-text">
            {isArabic ? "المعاملات المالية" : "Financial status"}
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-loginMd border border-app-border/70 bg-white/60 p-3">
              <p className="text-xs text-app-textMuted">{isArabic ? "الإيرادات" : "Income"}</p>
              <p className="mt-1 text-lg font-semibold text-emerald-700">
                <LtrIsland>{(data?.transactions?.total_income ?? 0).toLocaleString()}</LtrIsland>
              </p>
            </div>
            <div className="rounded-loginMd border border-app-border/70 bg-white/60 p-3">
              <p className="text-xs text-app-textMuted">{isArabic ? "المصروفات" : "Expenses"}</p>
              <p className="mt-1 text-lg font-semibold text-red-700">
                <LtrIsland>{(data?.transactions?.total_expenses ?? 0).toLocaleString()}</LtrIsland>
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <h2 className="mb-3 text-base font-semibold text-app-text">{isArabic ? "حاويات الرسوم البيانية" : "Chart containers"}</h2>
          <div className="flex min-h-[12rem] items-center justify-center rounded-loginMd border border-dashed border-app-borderStrong/60 bg-white/35">
            <EmptyState
              title={isArabic ? "يتم تجهيز الرسوم البيانية" : "Charts are being prepared"}
              description={
                isArabic
                  ? "ستظهر الرسوم عند توفر حقول البيانات المؤكدة."
                  : "Charts will render once confirmed fields are available."
              }
            />
          </div>
        </Card>
      </Section>
    </div>
  );
}
