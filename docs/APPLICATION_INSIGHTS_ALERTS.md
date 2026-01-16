# Application Insights Alerts Configuration

**Project:** Century Churn Prediction System
**Last Updated:** 2024-12-19
**Version:** 1.0

## Overview

This document provides instructions for setting up Application Insights alerts for the Century Churn Prediction System. Alerts enable proactive monitoring and early detection of issues.

## Prerequisites

- Application Insights workspace linked to Function App
- Azure Portal access with appropriate permissions
- Understanding of Kusto Query Language (KQL) for custom queries

## Alert Configuration

### Alert 1: Function Execution Failures

**Purpose:** Alert immediately when the pipeline fails

1. Azure Portal → Application Insights → Alerts → Create alert rule
1. **Scope:** Select Application Insights resource and resource type "Any"
1. **Condition:**
   - **Signal type:** Custom log search
   - **Search query:**

     ```kusto
     traces
     | where severityLevel >= 3
     | where message contains "Pipeline failed" or message contains "Step"
     | where timestamp > ago(5m)
     ```

   - **Alert logic:**
     - Number of results: Greater than 0
     - Evaluation frequency: Every 1 minute
     - Lookback period: 5 minutes
1. **Actions:**
   - Action group: Create or select action group with email notifications
   - Email recipients: Operations team
1. **Alert details:**
   - Alert rule name: `Churn Pipeline - Execution Failure`
   - Severity: Critical
   - Description: Alert when churn scoring pipeline fails at any step

- Triggers immediately when pipeline fails
- Sends email notification with error details
- Includes Application Insights link for investigation

### Alert 2: High Error Rate

**Purpose:** Alert when error rate exceeds threshold

1. Azure Portal → Application Insights → Alerts → Create alert rule
1. **Scope:** Select Application Insights resource and resource type "Any"
1. **Condition:**
   - **Signal type:** Custom log search
   - **Search query:**

     ```kusto
     traces
     | where timestamp > ago(1h)
     | summarize 
         total_requests = count(),
         errors = countif(severityLevel >= 3)
     | extend error_rate = (errors * 100.0 / total_requests)
     | project error_rate
     ```

   - **Alert logic:**
     - Number of results: Greater than 0
     - Evaluation frequency: Every 5 minutes
     - Lookback period: 1 hour
     - Threshold value: 5 (error rate > 5%)
1. **Actions:**
   - Action group: Same as Alert 1
1. **Alert details:**
   - Alert rule name: `Churn Pipeline - High Error Rate`
   - Severity: Warning
   - Description: Alert when error rate exceeds 5% over 1 hour

- Triggers when error rate > 5% in past hour
- Helps detect gradual degradation
- Sends notification to operations team

### Alert 3: Pipeline Performance Degradation

**Purpose:** Alert when pipeline execution time exceeds threshold

1. Azure Portal → Application Insights → Alerts → Create alert rule
1. **Scope:** Select Application Insights resource and resource type "Any"
1. **Condition:**
   - **Signal type:** Custom log search
   - **Search query:**

     ```kusto
     traces
     | where message contains "Pipeline completed"
     | where timestamp > ago(1h)
     | parse message with "Pipeline completed successfully: " rows_scored " rows scored, " rows_written " written, duration: " duration_seconds " seconds"
     | extend duration_seconds = toreal(duration_seconds)
     | summarize avg_duration = avg(duration_seconds), max_duration = max(duration_seconds)
     | where max_duration > 600  // 10 minutes
     ```

   - **Alert logic:**
     - Number of results: Greater than 0
     - Evaluation frequency: Every 15 minutes
     - Lookback period: 1 hour
1. **Actions:**
   - Action group: Same as Alert 1
1. **Alert details:**
   - Alert rule name: `Churn Pipeline - Performance Degradation`
   - Severity: Warning
   - Description: Alert when pipeline execution time exceeds 10 minutes

- Triggers when execution time > 10 minutes
- Indicates potential performance issues
- Sends notification to operations team

### Alert 4: Data Quality - Low Row Count

**Purpose:** Alert when pipeline processes fewer rows than expected

1. Azure Portal → Application Insights → Alerts → Create alert rule
1. **Scope:** Select Application Insights resource and resource type "Any"
1. **Condition:**
   - **Signal type:** Custom log search
   - **Search query:**

     ```kusto
     traces
     | where message contains "Pipeline completed successfully"
     | where timestamp > ago(1h)
     | parse message with "Pipeline completed successfully: " rows_scored " rows scored"
     | extend rows_scored = toint(rows_scored)
     | where rows_scored < 5000  // Adjust threshold based on expected minimum
     ```

   - **Alert logic:**
     - Number of results: Greater than 0
     - Evaluation frequency: Every 15 minutes
     - Lookback period: 1 hour
1. **Actions:**
   - Action group: Same as Alert 1
1. **Alert details:**
   - Alert rule name: `Churn Pipeline - Low Row Count`
   - Severity: Warning
   - Description: Alert when pipeline processes fewer than expected rows

- Triggers when row count < expected threshold
- Indicates potential data source issues
- Sends notification to operations team

### Alert 5: Data Quality - Missing DAX Query Results

**Purpose:** Alert when DAX query returns no results

1. Azure Portal → Application Insights → Alerts → Create alert rule
1. **Scope:** Select Application Insights resource and resource type "Any"
1. **Condition:**
   - **Signal type:** Custom log search
   - **Search query:**

     ```kusto
     traces
     | where message contains "DAX query returned no rows"
     | where timestamp > ago(5m)
     ```

   - **Alert logic:**
     - Number of results: Greater than 0
     - Evaluation frequency: Every 1 minute
     - Lookback period: 5 minutes
1. **Actions:**
   - Action group: Same as Alert 1
1. **Alert details:**
   - Alert rule name: `Churn Pipeline - No DAX Results`
   - Severity: Critical
   - Description: Alert when DAX query returns no rows

- Triggers immediately when DAX query fails
- Critical alert for data pipeline
- Sends notification to operations team

### Alert 6: Timer Trigger Not Executing

**Purpose:** Alert when monthly timer trigger doesn't execute

1. Azure Portal → Application Insights → Alerts → Create alert rule
1. **Scope:** Select Application Insights resource and resource type "Any"
1. **Condition:**
   - **Signal type:** Custom log search
   - **Search query:**

     ```kusto
     traces
     | where message contains "Pipeline started" or message contains "Pipeline completed"
     | where timestamp > ago(2d)
     | summarize execution_count = count()
     | where execution_count == 0
     ```

   - **Alert logic:**
     - Number of results: Greater than 0
     - Evaluation frequency: Every 6 hours
     - Lookback period: 2 days
   - **Note:** This alert is designed to catch missing monthly executions. Adjust timing based on schedule.
1. **Actions:**
   - Action group: Same as Alert 1
1. **Alert details:**
   - Alert rule name: `Churn Pipeline - Timer Not Executing`
   - Severity: Critical
   - Description: Alert when monthly timer trigger doesn't execute

- Triggers if no pipeline execution in 2 days (after expected run date)
- Critical for monthly batch jobs
- Sends notification to operations team

## Action Groups

### Create Action Group

1. Azure Portal → Application Insights → Alerts → Action groups → Create
1. **Basics:**
   - Name: `churn-pipeline-alerts`
   - Display name: `Churn Pipeline Alerts`
   - Subscription: Select subscription
   - Resource group: Select resource group
1. **Notifications:**
   - Notification type: Email/SMS/Push/Voice
   - Name: `operations-team`
   - Email: Add operations team email addresses
   - SMS: Add phone numbers (optional)
1. **Actions:**
   - Action type: Email/SMS (already added in notifications)
   - Configure recipients
1. **Tags:** (Optional) Add tags for resource organization
1. **Review + Create:** Review and create action group

### Recommended Recipients

- Operations team email address
- On-call engineer (SMS optional)
- Team distribution list

## Testing Alerts

### Test Alert 1: Function Execution Failures

1. **Trigger test failure:**
   - Manually trigger pipeline with invalid configuration
   - Or temporarily break code to cause failure
1. **Verify alert:**
   - Check Application Insights → Alerts → Alert history
   - Verify alert fired within 1-2 minutes
   - Verify email notification received

### Test Alert 2: High Error Rate

1. **Simulate errors:**
   - Trigger multiple pipeline runs that fail
   - Ensure error rate > 5% over 1 hour
1. **Verify alert:**
   - Check alert history
   - Verify email notification

### Test Alert 3: Performance Degradation

1. **Simulate slow execution:**
   - Add artificial delay to pipeline code (temporary)
   - Trigger pipeline execution
1. **Verify alert:**
   - Check alert history
   - Verify email notification

## Alert Management

### Viewing Active Alerts

1. Azure Portal → Application Insights → Alerts
1. View "Active alerts" tab for currently firing alerts
1. Click alert to view details and investigate

### Alert History

1. Azure Portal → Application Insights → Alerts → Alert history
1. Filter by:
   - Time range
   - Alert rule name
   - Severity
   - Status (fired/resolved)

### Disabling/Enabling Alerts

1. Azure Portal → Application Insights → Alerts
1. Select alert rule
1. Click "Enable" or "Disable" button

### Modifying Alerts

1. Azure Portal → Application Insights → Alerts
1. Select alert rule
1. Click "Edit" to modify:
   - Query
   - Thresholds
   - Evaluation frequency
   - Action groups

## Dashboard Queries

### Useful KQL Queries for Monitoring

#### Recent Errors

```kusto
traces
| where severityLevel >= 3
| where timestamp > ago(24h)
| order by timestamp desc
| project timestamp, message, customDimensions
```

#### Pipeline Execution Times

```kusto
traces
| where message contains "Pipeline completed"
| parse message with "Pipeline completed successfully: " rows_scored " rows scored, " rows_written " written, duration: " duration_seconds " seconds"
| extend duration_seconds = toreal(duration_seconds)
| project timestamp, duration_seconds, rows_scored, rows_written
| order by timestamp desc
```

#### Errors by Step

```kusto
traces
| where severityLevel >= 3
| where message contains "Step"
| extend step = tostring(customDimensions.step)
| summarize count() by step
| order by count_ desc
```

#### Success Rate Over Time

```kusto
traces
| where message contains "Pipeline completed" or message contains "Pipeline failed"
| extend success = iff(message contains "successfully", 1, 0)
| summarize 
    total = count(),
    successful = sum(success),
    failed = count() - sum(success)
    by bin(timestamp, 1h)
| extend success_rate = (successful * 100.0 / total)
| project timestamp, total, successful, failed, success_rate
| order by timestamp desc
```

#### Function Execution Metrics

```kusto
requests
| where timestamp > ago(7d)
| summarize 
    count(),
    avg(duration),
    max(duration),
    min(duration)
    by bin(timestamp, 1h)
| order by timestamp desc
```

## Best Practices

1. **Start with Critical Alerts:**
   - Set up Alert 1 (Execution Failures) first
   - Add other alerts incrementally

1. **Tune Thresholds:**
   - Adjust thresholds based on actual performance
   - Monitor alert frequency and adjust if too noisy

1. **Document Alert Logic:**
   - Document expected behavior in alert descriptions
   - Include runbook links in alert notifications

1. **Review and Refine:**
   - Review alert history monthly
   - Remove false positives
   - Add new alerts as needed

1. **Test Regularly:**
   - Test alerts after deployment changes
   - Verify notification delivery

## Troubleshooting

### Alert Not Firing

- Check alert rule status (enabled/disabled)
- Verify query returns results when manually run
- Check evaluation frequency vs. lookback period

1. Run query manually in Application Insights → Logs
1. Verify query returns expected results
1. Check alert rule configuration
1. Verify action group is configured

### Too Many False Positives

- Thresholds too sensitive
- Query logic needs refinement

1. Adjust thresholds based on historical data
1. Refine query to exclude known benign conditions
1. Add filters to query

### Alert Not Sending Notifications

- Action group not configured
- Email addresses incorrect
- Action group not linked to alert rule

1. Verify action group exists and is enabled
1. Check email addresses in action group
1. Verify action group is linked to alert rule
1. Test action group notifications manually

## References

- [Azure Monitor Alerts Documentation](https://learn.microsoft.com/azure/azure-monitor/alerts/alerts-overview)
- [Application Insights Query Documentation](https://learn.microsoft.com/azure/azure-monitor/logs/get-started-queries)
- [Kusto Query Language (KQL) Reference](https://learn.microsoft.com/azure/data-explorer/kusto/query/)
