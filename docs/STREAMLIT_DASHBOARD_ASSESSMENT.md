# Streamlit Dashboard Assessment

**Project:** Century Churn Prediction System
**Last Updated:** 2024-12-19
**Version:** 1.0

## Overview

This document assesses the feasibility and value of implementing a Streamlit dashboard for model documentation, visualization, and monitoring for the Century Churn Prediction System.

## Executive Summary

**Recommendation:** **Optional** - Streamlit dashboard is a valuable addition but not required for production deployment. Consider implementing if:

- Model documentation needs exceed what Power BI provides
- Interactive data exploration is needed by non-technical stakeholders
- Separate monitoring dashboard is desired (independent of Power BI)

**Priority:** Medium (nice-to-have enhancement)

## Current State

### Existing Tools

1. **Power BI:**
   - Primary visualization and reporting tool
   - Business user-friendly interface
   - Integrated with Azure SQL Database
   - Provides trend analysis and aggregations

1. **Application Insights:**
   - Technical monitoring and logging
   - Query-based dashboards available
   - Developer-oriented interface

1. **Email Notifications:**
   - Success/failure notifications
   - Risk distribution summaries
   - Pipeline execution metrics

## Potential Use Cases

### 1. Model Documentation Dashboard

**Purpose:** Document model performance, feature importance, and training statistics

- Model performance metrics (accuracy, precision, recall, ROC-AUC)
- Feature importance visualization (bar charts, waterfall charts)
- Training data statistics (data quality, distributions)
- Model version tracking (when model is retrained)
- Model metadata (training date, version, hyperparameters)

- ✅ Useful for ML team and data scientists
- ✅ Helps document model decisions
- ✅ Useful for model governance and compliance
- ⚠️ May duplicate information in training notebook

**Effort:** Medium (2-3 days development)

- Model metadata files (may need to be created)
- Training metrics (may need to be exported from training notebook)

### 2. Data Exploration Dashboard

**Purpose:** Interactive exploration of scoring results and customer data

- Sample scoring results visualization (interactive table)
- Risk distribution charts (pie charts, bar charts)
- Customer segmentation analysis (filterable by segment, risk band)
- Trend analysis over time (line charts)
- Customer drill-down (view individual customer details)

- ✅ Useful for business analysts and non-technical stakeholders
- ✅ Interactive exploration without SQL knowledge
- ⚠️ May duplicate Power BI capabilities
- ⚠️ Requires data access layer (SQL connection or API)

**Effort:** Medium-High (3-5 days development)

- Database connection or API endpoint
- Streamlit deployment (container or Azure App Service)

### 3. Model Monitoring Dashboard

**Purpose:** Real-time monitoring of pipeline execution and model performance

- Pipeline execution history (timeline, status, duration)
- Performance metrics over time (execution time, row counts)
- Error rate tracking (error rate trends, error types)
- Cost monitoring (Azure Consumption plan usage, cost per execution)
- Data quality metrics (row counts, risk distribution changes)

- ✅ Useful for operations team
- ✅ Complements Application Insights (more user-friendly)
- ✅ Helps track costs and performance trends
- ⚠️ May duplicate Application Insights capabilities
- ⚠️ Requires Application Insights API or database queries

**Effort:** High (5-7 days development)

- Application Insights API access
- Azure Cost Management API (for cost data)
- Database access for historical metrics

## Implementation Considerations

### Pros

1. **Easy to Build:**
   - Streamlit is simple and fast to prototype
   - Python-based (matches existing codebase)
   - Good integration with pandas DataFrames

1. **Good for Non-Technical Users:**
   - Intuitive interface
   - No SQL knowledge required
   - Interactive widgets (filters, sliders, dropdowns)

1. **Flexible:**
   - Can combine multiple data sources
   - Easy to add new visualizations
   - Can embed external content (charts, iframes)

1. **Independent:**
   - Separate from Power BI (different use case)
   - Doesn't affect core Azure Function code
   - Can be deployed independently

### Cons

1. **Adds Dependency:**
   - New dependency (Streamlit)
   - Requires separate deployment/container
   - Additional maintenance overhead

1. **May Duplicate Functionality:**
   - Power BI already provides visualization
   - Application Insights provides monitoring
   - Email notifications provide alerts

1. **Not Necessary for Core Functionality:**
   - Core pipeline works without it
   - Documentation can be in markdown/docs
   - Monitoring exists in Application Insights

1. **Deployment Complexity:**
   - Requires container or Azure App Service
   - Needs database/API access
   - Additional authentication considerations

## Architecture Options

### Option 1: Separate Streamlit App (Recommended)

#### Structure

```text
century-churn-prediction-project/
├── dashboard/              # New directory
│   ├── app.py             # Main Streamlit app
│   ├── pages/             # Multi-page dashboard
│   │   ├── model_docs.py  # Model documentation
│   │   ├── exploration.py # Data exploration
│   │   └── monitoring.py  # Pipeline monitoring
│   ├── components/        # Reusable components
│   ├── utils/            # Utility functions
│   └── requirements.txt  # Streamlit dependencies
└── ...
```

- Azure Container Instances (ACI) or Azure App Service
- Docker container with Streamlit
- Environment variables for database connection

#### Pros (Option 1: Separate Streamlit App (Recommended))

- Clean separation from core code
- Independent deployment
- Easy to disable if not needed

#### Cons (Option 1: Separate Streamlit App (Recommended))

- Additional infrastructure
- Separate deployment pipeline

### Option 2: Integrated into Function App (Not Recommended)

#### Structure (Option 2: Integrated into Function App (Not Recommended))

- Add Streamlit app as separate endpoint in Function App
- Use HTTP trigger to serve Streamlit app

#### Pros (Option 2: Integrated into Function App (Not Recommended))

- Single deployment
- Shared infrastructure

#### Cons (Option 2: Integrated into Function App (Not Recommended))

- Not suitable for Function App architecture
- Conflicts with Function App runtime
- Not recommended by Azure Functions best practices

## Recommended Implementation Plan

### Phase 1: Model Documentation Dashboard (MVP)

#### Scope

- Model performance metrics (from training notebook exports)
- Feature importance visualization
- Training data statistics
- Model version tracking

**Timeline:** 2-3 days
**Effort:** Medium
**Value:** High (for ML team)

#### Files to Create

- `dashboard/app.py` - Main app entry point
- `dashboard/pages/model_docs.py` - Model documentation page
- `dashboard/components/metrics.py` - Metrics visualization components

#### Data Sources

- Model metadata JSON files (create during training)
- Feature importance CSV (export from training notebook)

### Phase 2: Data Exploration Dashboard (Optional)

#### Scope (Phase 2: Data Exploration Dashboard (Optional))

- Interactive scoring results table
- Risk distribution charts
- Customer segmentation filters
- Trend analysis

**Timeline:** 3-5 days
**Effort:** Medium-High
**Value:** Medium (may duplicate Power BI)

#### Files to Create (Phase 2: Data Exploration Dashboard (Optional))

- `dashboard/pages/exploration.py` - Data exploration page
- `dashboard/components/charts.py` - Chart components
- `dashboard/utils/db.py` - Database connection utilities

#### Data Sources (Phase 2: Data Exploration Dashboard (Optional))

- Azure SQL Database (read-only access)
- SQL views: `dbo.vwCustomerCurrent`

### Phase 3: Monitoring Dashboard (Future)

#### Scope (Phase 3: Monitoring Dashboard (Future))

- Pipeline execution history
- Performance metrics over time
- Cost monitoring
- Data quality metrics

**Timeline:** 5-7 days
**Effort:** High
**Value:** Medium (Application Insights exists)

#### Data Sources (Phase 3: Monitoring Dashboard (Future))

- Application Insights API
- Azure Cost Management API
- SQL Database (historical metrics)

## Decision Matrix

| Use Case | Value | Effort | Priority | Recommendation |
| -------- | ----- | ------ | -------- | -------------- |
| Model Documentation | High | Medium | High | ✅ Implement (Phase 1) |
| Data Exploration | Medium | Medium-High | Medium | ⚠️ Consider (Phase 2) |
| Monitoring | Medium | High | Low | ❌ Defer (Power BI + Application Insights sufficient) |

## Alternative Approaches

### 1. Enhanced README/Documentation

Instead of Streamlit dashboard, enhance documentation:

- Add model performance metrics to README
- Include training statistics in markdown
- Create visualizations as static images (exported from training notebook)

**Pros:** No additional infrastructure, easier to maintain
**Cons:** Less interactive, requires manual updates

### 2. Power BI Enhancements

Enhance existing Power BI dashboard:

- Add model documentation report
- Add monitoring metrics report
- Improve data exploration features

**Pros:** Uses existing infrastructure, familiar to users
**Cons:** May not support all visualization needs, less flexible

### 3. Application Insights Workbooks

Use Application Insights Workbooks for monitoring:

- Create custom workbooks for pipeline monitoring
- Add KQL queries for metrics
- Customize dashboards

**Pros:** Integrated with Application Insights, no additional infrastructure
**Cons:** Requires KQL knowledge, less user-friendly for non-technical users

## Recommendations

### Immediate Actions

1. **Document Current State:**
   - Document what Power BI provides
   - Document what Application Insights provides
   - Identify gaps

1. **Stakeholder Feedback:**
   - Survey business users on Power BI limitations
   - Survey ML team on model documentation needs
   - Survey operations team on monitoring needs

1. **Decision:**
   - If gaps identified: Consider Phase 1 (Model Documentation)
   - If Power BI sufficient: Defer Streamlit implementation
   - If monitoring needs: Consider Application Insights Workbooks first

### If Proceeding with Streamlit

1. **Start with Phase 1 (Model Documentation):**
   - Highest value, lowest risk
   - Useful for ML team
   - Can be deployed independently

1. **Evaluate Before Phase 2:**
   - Get user feedback on Phase 1
   - Assess if Phase 2 adds value beyond Power BI
   - Consider alternatives

1. **Defer Phase 3:**
   - Application Insights provides monitoring
   - Cost monitoring can be done in Azure Portal
   - Only proceed if clear value identified

## Implementation Example (Phase 1)

### Basic Structure

```python
# dashboard/app.py
import streamlit as st

st.set_page_config(
    page_title="Churn Model Documentation",
    page_icon="📊",
    layout="wide"
)

st.title("Century Churn Prediction Model")

st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Select Page", [
    "Model Overview",
    "Feature Importance",
    "Training Statistics"
])

if page == "Model Overview":
    st.header("Model Overview")
    # Display model metrics
elif page == "Feature Importance":
    st.header("Feature Importance")
    # Display feature importance charts
elif page == "Training Statistics":
    st.header("Training Statistics")
    # Display training data stats
```

```text
# dashboard/requirements.txt
streamlit>=1.28.0
pandas>=2.0.0
plotly>=5.17.0
```

```dockerfile
# dashboard/Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## Conclusion

Streamlit dashboard is a **valuable but optional enhancement**. Priority should be:

1. ✅ **Phase 1 (Model Documentation):** High value, recommended if ML team needs better documentation
1. ⚠️ **Phase 2 (Data Exploration):** Medium value, consider if Power BI limitations identified
1. ❌ **Phase 3 (Monitoring):** Low priority, Application Insights provides sufficient monitoring

**Final Recommendation:** Start with Phase 1 if there's a clear need for model documentation beyond what's in the training notebook. Evaluate Phase 2 based on user feedback and Power BI limitations. Defer Phase 3 unless clear value is identified.

## References

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Streamlit Components Gallery](https://streamlit.io/components)
- [Azure Container Instances](https://learn.microsoft.com/azure/container-instances/)
- [Azure App Service](https://learn.microsoft.com/azure/app-service/)
