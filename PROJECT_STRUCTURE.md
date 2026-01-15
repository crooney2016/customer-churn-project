# Project Tree Structure

text
century-churn-prediction-project/
│
├── .gitignore
├── .pylintrc
├── pyrightconfig.json
├── README.md
├── requirements.txt
│
├── dax/
│   ├── churn_features.dax
│   └── churn_features_dax_multimonth.dax
│
├── function_app/
│   ├── __init__.py
│   ├── config.py
│   ├── dax_client.py
│   ├── email_client.py
│   ├── function_app.py
│   ├── function.json
│   ├── host.json
│   ├── pbi_client.py
│   ├── requirements.txt
│   ├── scorer.py
│   └── sql_client.py
│
├── model/
│   ├── conda.yml
│   └── training-notebook.ipynb
│
├── outputs/
│   └── README.md
│
├── scripts/
│   ├── clean-git-history.sh
│   └── local_scoring.ipynb
│
└── sql/
    ├── functions.sql
    ├── procedures.sql
    ├── schema.sql
    └── views.sql

```text

## Directory Descriptions

- **`dax/`** - DAX query files for churn feature definitions
- **`function_app/`** - Azure Function App code for scoring and services
- **`model/`** - Model training notebook and conda environment configuration
- **`outputs/`** - Output files directory
- **`scripts/`** - Utility scripts for local scoring and git history management
- **`sql/`** - SQL schema, views, functions, and stored procedures
