# Cost Monitoring Guide

**Project:** Century Churn Prediction System
**Last Updated:** 2024-12-19
**Version:** 1.0

## Overview

This document provides instructions for monitoring and optimizing Azure Consumption plan costs for the Century Churn Prediction System. The Function App runs monthly, making cost monitoring important for budget management.

## Azure Consumption Plan Pricing

### Cost Components

1. **Execution Time:**
   - Billed per GB-second
   - Based on memory allocation and execution duration
   - Formula: `(Memory in GB) × (Execution Time in Seconds) × (Price per GB-second)`

1. **Function Executions:**
   - First 1 million executions free per month
   - Additional executions: $0.20 per million
   - Typically not a concern for monthly jobs

1. **Application Insights:**
   - First 5 GB free per month
   - Additional data: ~$2.30 per GB
   - Can be significant with verbose logging

## Monitoring Costs

### Method 1: Azure Portal Cost Analysis

1. **Azure Portal → Cost Management + Billing → Cost analysis**

1. **Filter by Resource:**
   - Resource type: Function App
   - Resource: `<your-function-app-name>`
   - Time range: Last 30 days / Last 7 days

1. **View Metrics:**
   - Total cost
   - Cost by date
   - Cost breakdown by resource

### Method 2: Application Insights Metrics

#### Query Execution Metrics

```kusto
requests
| where timestamp > ago(30d)
| summarize 
    execution_count = count(),
    avg_duration_ms = avg(duration),
    total_duration_seconds = sum(duration) / 1000,
    avg_memory_mb = avg(customDimensions.MemoryUsageMB)
| extend 
    total_gb_seconds = (avg_memory_mb / 1024) * (total_duration_seconds / 1000)
| project 
    execution_count, 
    avg_duration_ms, 
    total_gb_seconds,
    estimated_cost_usd = total_gb_seconds * 0.000016  // Approximate price
```

#### Query Function App Usage

```kusto
// Function App execution time
requests
| where timestamp > ago(30d)
| summarize 
    total_executions = count(),
    avg_duration_ms = avg(duration),
    max_duration_ms = max(duration),
    min_duration_ms = min(duration)
| project 
    total_executions,
    avg_duration_seconds = avg_duration_ms / 1000,
    max_duration_seconds = max_duration_ms / 1000
```

### Method 3: Cost Management API (Automated)

#### Create Cost Monitoring Script

```python
# scripts/monitor_costs.py
from azure.identity import DefaultAzureCredential
from azure.mgmt.costmanagement import CostManagementClient
from datetime import datetime, timedelta

credential = DefaultAzureCredential()
client = CostManagementClient(credential, subscription_id="<subscription-id>")

# Query cost for last 30 days
query_definition = {
    "type": "ActualCost",
    "timeframe": "TheLastMonth",
    "dataset": {
        "granularity": "Daily",
        "aggregation": {
            "totalCost": {"name": "PreTaxCost", "function": "Sum"}
        },
        "filter": {
            "dimensions": {
                "name": "ResourceId",
                "operator": "In",
                "values": ["/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Web/sites/<function-app>"]
            }
        }
    }
}

result = client.query.usage(scope=f"/subscriptions/<subscription-id>", parameters=query_definition)

# Print results
for row in result.rows:
    print(f"Date: {row[0]}, Cost: ${row[1]}")
```

## Cost Optimization

### 1. Optimize Execution Time

#### Current Performance

- 12k rows (monthly): ~10 seconds
- 400k rows (full): ~2-3 minutes

#### Optimizations Applied

- ✅ `itertuples()` instead of `iterrows()` (50-70% faster)
- ✅ Vectorized `RiskBand` calculation (20-30% faster)
- ✅ Model caching with `@lru_cache` (avoids 1-2 seconds per invocation)
- ✅ Single `pd.concat()` operation (~5% faster)

#### Monitoring

- Track execution duration in Application Insights
- Alert if duration increases significantly

### 2. Optimize Memory Usage

#### Monitor Memory

```kusto
// Memory usage per execution
requests
| where timestamp > ago(30d)
| extend memory_mb = toreal(customDimensions.MemoryUsageMB)
| summarize 
    avg_memory_mb = avg(memory_mb),
    max_memory_mb = max(memory_mb)
```

#### Optimization

- Process data in batches (already implemented)
- Minimize DataFrame copies
- Release large objects when done

### 3. Optimize Logging (Application Insights Cost)

#### Current Logging

- INFO level: Pipeline steps, metrics
- ERROR level: Exceptions with stack traces
- DEBUG level: Disabled in production

#### Optimization (3. Optimize Logging (Application Insights Cost))

- Reduce verbose logging
- Use sampling (configured in `host.json`)
- Archive old logs (set retention policy)

#### Application Insights Sampling

```json
// host.json
{
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "maxTelemetryItemsPerSecond": 20
      }
    }
  }
}
```

### 4. Schedule Optimization

#### Current Schedule

- Monthly timer trigger (1st of month at 6 AM UTC)
- ~12 executions per year

#### Considerations

- Schedule is already optimal (monthly batch job)
- No need to run more frequently

## Cost Alerts

### Set Up Cost Alerts

1. **Azure Portal → Cost Management + Billing → Budgets → Create budget**

1. **Budget Configuration:**
   - Scope: Subscription or Resource Group
   - Budget amount: Set monthly budget (e.g., $50)
   - Period: Monthly
   - Reset type: Monthly

1. **Alert Conditions:**
   - Alert threshold: 50%, 75%, 90%, 100%
   - Alert recipients: Operations team email

1. **Action Groups:**
   - Create action group with email notifications
   - Add recipients

### Cost Monitoring Query (Application Insights)

#### Create Custom Query

```kusto
// Estimated cost per execution
requests
| where timestamp > ago(30d)
| extend 
    duration_seconds = duration / 1000,
    memory_gb = 1.0,  // Approximate memory allocation
    gb_seconds = memory_gb * duration_seconds,
    estimated_cost = gb_seconds * 0.000016  // Approximate USD per GB-second
| summarize 
    total_executions = count(),
    total_gb_seconds = sum(gb_seconds),
    total_estimated_cost = sum(estimated_cost),
    avg_cost_per_execution = avg(estimated_cost)
| project 
    total_executions,
    total_gb_seconds,
    total_estimated_cost_usd = round(total_estimated_cost, 4),
    avg_cost_per_execution_usd = round(avg_cost_per_execution, 4)
```

## Cost Reporting

### Monthly Cost Summary

#### Create Dashboard Query

```kusto
// Monthly cost summary
requests
| where timestamp > ago(30d)
| extend 
    month = format_datetime(timestamp, "yyyy-MM"),
    duration_seconds = duration / 1000,
    gb_seconds = 1.0 * duration_seconds,  // Assuming 1 GB memory
    estimated_cost = gb_seconds * 0.000016
| summarize 
    execution_count = count(),
    total_gb_seconds = sum(gb_seconds),
    total_cost_usd = sum(estimated_cost)
    by month
| project 
    month,
    execution_count,
    total_gb_seconds = round(total_gb_seconds, 2),
    estimated_cost_usd = round(total_cost_usd, 4)
| order by month desc
```

### Cost by Function

#### If multiple functions exist

```kusto
requests
| where timestamp > ago(30d)
| extend 
    function_name = customDimensions.FunctionName,
    duration_seconds = duration / 1000,
    gb_seconds = 1.0 * duration_seconds,
    estimated_cost = gb_seconds * 0.000016
| summarize 
    execution_count = count(),
    total_cost_usd = sum(estimated_cost)
    by function_name
| project 
    function_name,
    execution_count,
    estimated_cost_usd = round(total_cost_usd, 4)
| order by estimated_cost_usd desc
```

## Expected Costs

### Monthly Estimate

#### For 12k rows (monthly batch)

- Execution time: ~10 seconds
- Memory: ~1 GB (approximate)
- GB-seconds: 10 GB-seconds
- Execution cost: ~$0.00016 (negligible)
- Function executions: 1 execution (free tier covers)
- **Estimated monthly cost: < $0.10**

#### Additional Costs

- Application Insights: ~$1-2/month (depends on logging volume)
- Storage (if any): Minimal

#### Total Estimated Monthly Cost: < $3

### Annual Estimate

- 12 monthly executions per year
- Application Insights data retention
- **Estimated annual cost: < $40**

## Cost Optimization Checklist

- [x] Optimize execution time (vectorization, caching)
- [x] Use efficient DataFrame operations (`itertuples()`)
- [x] Minimize memory usage (batch processing)
- [x] Configure Application Insights sampling
- [ ] Set up cost alerts (recommended)
- [ ] Monitor execution duration trends
- [ ] Review Application Insights data retention
- [ ] Archive old logs to reduce costs

## References

- [Azure Functions Pricing](https://azure.microsoft.com/pricing/details/functions/)
- [Azure Cost Management](https://learn.microsoft.com/azure/cost-management-billing/)
- [Application Insights Pricing](https://azure.microsoft.com/pricing/details/monitor/)
- [Cost Management API](https://learn.microsoft.com/rest/api/cost-management/)
