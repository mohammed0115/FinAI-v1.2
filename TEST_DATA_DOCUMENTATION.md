# FinAI Test Data Documentation

## Overview

This document describes the synthetic test data created for manual testing of the FinAI Financial Audit Platform.

## Test Data Generation

Run the seed command to generate test data:
```bash
cd /app/backend
python manage.py seed_test_data

# To clear existing data first:
python manage.py seed_test_data --clear
```

## Data Summary

| Entity | Count | Description |
|--------|-------|-------------|
| Organizations | 4 | 1 demo + 3 GCC test companies |
| Users | 11 | Admin + 9 test users (3 per org) |
| Accounts | 87 | Chart of Accounts (29 per org) |
| Transactions | 300 | 100 per org (80% normal, 15% anomalies, 5% violations) |
| Journal Entries | 60 | 20 per org |
| Compliance Checks | 18 | 6 per org |
| Audit Flags | 60 | ~20 per org |
| Insights | 15 | 5 per org |
| Reports | 12 | 4 per org |
| Audit Logs | 90 | 30 per org |

## Test Organizations

### 1. FinAI Demo Company (SA)
- **Type**: Demo/Admin organization
- **Country**: Saudi Arabia
- **Currency**: SAR
- **VAT Rate**: 15%
- **Credentials**: admin@finai.com / admin123

### 2. Al-Faisal Trading Company (SA)
- **Type**: Private wholesale trader
- **Country**: Saudi Arabia
- **Currency**: SAR
- **VAT Rate**: 15%
- **Test Users**:
  - test.auditor@al-faisaltradingcompany.com / auditor123
  - test.accountant@al-faisaltradingcompany.com / accountant123
  - test.finance_manager@al-faisaltradingcompany.com / finance_manager123

### 3. Emirates Tech Solutions (AE)
- **Type**: SME tech company
- **Country**: UAE
- **Currency**: AED
- **VAT Rate**: 5%
- **Test Users**:
  - test.auditor@emiratestechsolutions.com / auditor123
  - test.accountant@emiratestechsolutions.com / accountant123
  - test.finance_manager@emiratestechsolutions.com / finance_manager123

### 4. Kuwait Industrial Group (KW)
- **Type**: Private manufacturing
- **Country**: Kuwait
- **Currency**: KWD
- **VAT Rate**: 0% (no VAT)
- **Test Users**:
  - test.auditor@kuwaitindustrialgroup.com / auditor123
  - test.accountant@kuwaitindustrialgroup.com / accountant123
  - test.finance_manager@kuwaitindustrialgroup.com / finance_manager123

## Chart of Accounts

Each organization has a standardized chart of accounts:

### Assets (1xxx)
| Code | Name | Type |
|------|------|------|
| 1000 | Cash in Bank | Cash |
| 1001 | Petty Cash | Cash |
| 1100 | Accounts Receivable | AR |
| 1200 | Inventory | Inventory |
| 1300 | Prepaid Expenses | Prepaid |
| 1500 | Equipment | Fixed Assets |
| 1510 | Vehicles | Fixed Assets |
| 1600 | Accumulated Depreciation | Fixed Assets |

### Liabilities (2xxx)
| Code | Name | Type |
|------|------|------|
| 2000 | Accounts Payable | AP |
| 2100 | VAT Payable | VAT |
| 2200 | Salaries Payable | Accrued |
| 2500 | Short-term Loans | Loans |
| 2600 | Long-term Loans | Loans |

### Equity (3xxx)
| Code | Name | Type |
|------|------|------|
| 3000 | Share Capital | Capital |
| 3100 | Retained Earnings | Retained |
| 3200 | Current Year Earnings | Retained |

### Revenue (4xxx)
| Code | Name | Type |
|------|------|------|
| 4000 | Sales Revenue | Sales |
| 4100 | Service Revenue | Service |
| 4200 | Interest Income | Other |
| 4300 | Other Income | Other |

### Expenses (5xxx)
| Code | Name | Type |
|------|------|------|
| 5000 | Cost of Goods Sold | COGS |
| 5100 | Salaries & Wages | Salaries |
| 5200 | Rent Expense | Rent |
| 5300 | Utilities | Utilities |
| 5400 | Marketing & Advertising | Marketing |
| 5500 | Professional Fees | Other |
| 5600 | Depreciation | Other |
| 5700 | Bank Charges | Other |
| 5800 | Office Supplies | Other |

## Transaction Data

### Normal Transactions (80%)
- Realistic amounts (SAR 1,000 - 100,000)
- Proper VAT calculation
- Various vendors/customers
- Date range: Last 6 months

### Anomalous Transactions (15%)
Types detected:
- **unusual_amount**: 5x normal amount
- **round_number**: Suspiciously round figures
- **duplicate**: Potential duplicate entries

### Compliance Violations (5%)
- Missing VAT calculations
- Data quality issues

## Audit Flags

| Type | Priority | Description |
|------|----------|-------------|
| duplicate | High | Potential duplicate payment |
| unusual_amount | High | Transaction 5x average |
| unusual_timing | Medium | Off-hours transaction |
| vat_error | Medium | VAT calculation mismatch |
| compliance_violation | High | Regulatory violation |
| fraud_risk | Critical | Potential fraud indicator |
| manual_review | Medium | Requires human review |

## Compliance Checks

| Type | Description |
|------|-------------|
| vat | VAT registration and return accuracy |
| zatca | E-invoice format compliance (SA) |
| shariah | Islamic finance principles |
| ifrs | Financial reporting standards |
| aml | Anti-money laundering monitoring |

## Testing Scenarios

### Scenario 1: Normal Audit Workflow
1. Login as auditor
2. View transaction list
3. Filter by date range
4. Review flagged transactions
5. Resolve audit flags
6. Generate report

### Scenario 2: Anomaly Detection
1. Login as admin
2. Navigate to analytics
3. Detect anomalies endpoint
4. Review AI-detected issues
5. Mark as resolved or escalate

### Scenario 3: Compliance Review
1. Login as finance_manager
2. View compliance score summary
3. Review failed checks
4. Document resolutions
5. Generate compliance report

### Scenario 4: VAT Calculation
1. Create new transaction
2. Verify auto-VAT calculation
3. Check VAT payable account
4. Generate VAT return report

## API Endpoints for Testing

### Authentication
```bash
# Get token
curl -X POST http://localhost:8001/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@finai.com", "password": "admin123"}'
```

### Transactions
```bash
# List all (with auth)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/documents/transactions/

# Filter anomalies
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8001/api/documents/transactions/?anomalies_only=true"

# Summary
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/documents/transactions/summary/
```

### Compliance
```bash
# Score summary
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/documents/compliance-checks/score_summary/

# Resolve check
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Reviewed and approved"}' \
  http://localhost:8001/api/documents/compliance-checks/{id}/resolve/
```

### Audit Flags
```bash
# Dashboard
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/documents/audit-flags/dashboard/

# High priority only
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8001/api/documents/audit-flags/?priority=high"
```

### Analytics
```bash
# KPIs
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8001/api/analytics/kpis/?organization_id={org_id}&period=month"

# Cash flow forecast
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"organization_id": "{org_id}", "periods": 6}' \
  http://localhost:8001/api/analytics/forecast/
```

## Data Integrity Notes

1. All UUIDs are auto-generated
2. Timestamps use UTC timezone
3. Amounts use Decimal precision (15,2)
4. Currency codes follow ISO 4217
5. Country codes follow ISO 3166-1 alpha-2

## Resetting Test Data

To regenerate all test data:
```bash
python manage.py seed_test_data --clear
```

This will:
1. Delete all test data (keeps admin user)
2. Recreate test organizations
3. Regenerate all transactions, accounts, etc.
