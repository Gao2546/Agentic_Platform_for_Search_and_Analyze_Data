```code
.
├── agentic_core
│   ├── agentic_core
│   │   ├── __init__.py
│   │   ├── udtp_mongo.py
│   │   └── udtp_postgres.py
│   └── setup.py
├── ai-engine
│   ├── pre-validator
│   ├── prompts
│   └── sanbox
├── backend
│   ├── Dockerfile
│   ├── go.mod
│   ├── requirements.txt
│   └── src
│       ├── api
│       │   ├── data_retrieval.py
│       │   ├── __pycache__
│       │   │   ├── data_retrieval.cpython-311.pyc
│       │   │   ├── schedules.cpython-311.pyc
│       │   │   └── scopes_management.cpython-311.pyc
│       │   ├── schedules.py
│       │   └── scopes_management.py
│       ├── core
│       ├── db
│       ├── main.py
│       ├── __pycache__
│       │   └── main.cpython-311.pyc
│       └── services
├── data-pipeline
│   ├── airflow
│   │   ├── config
│   │   │   └── schedules.json
│   │   ├── dags
│   │   │   └── agentic_dag_factory.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── spark-jobs
│       ├── clean_and_embed_data.py
│       └── Dockerfile
├── frontend
│   ├── Dockerfile
│   ├── eslint.config.js
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── public
│   │   ├── favicon.svg
│   │   └── icons.svg
│   ├── README.md
│   ├── src
│   │   ├── App.css
│   │   ├── App.jsx
│   │   ├── assets
│   │   │   ├── hero.png
│   │   │   ├── react.svg
│   │   │   └── vite.svg
│   │   ├── components
│   │   ├── hooks
│   │   │   └── useLiveStream.js
│   │   ├── index.css
│   │   ├── main.jsx
│   │   ├── pages
│   │   │   ├── Dashboard.jsx
│   │   │   ├── ScheduleFlow.jsx
│   │   │   ├── ScopeDetail.jsx
│   │   │   └── ScopeList.jsx
│   │   └── services
│   │       └── api.js
│   └── vite.config.js
├── images
│   └── AI_Agentic_Scheduling-2026-04-19-133737.png
├── infrastructure
│   ├── docker-compose.yml
│   ├── init-scripts
│   │   ├── init-minio.sh
│   │   └── init.sql
│   └── k8s
├── README.md
├── setup-scripts
├── streaming-pipeline
│   ├── consumers
│   ├── Dockerfile
│   ├── ingestion
│   │   └── mock_price_stream.py
│   ├── processors
│   │   └── fast_lane_worker.py
│   └── requirements.txt
├── test
│   └── test_e2e_flow.py
├── tools-library
│   ├── ai-inference
│   │   └── llm_sentiment.go
│   ├── external-apis
│   │   ├── fetch_data.py
│   │   └── fetch_stock_data.py
│   └── traditional-logic
│       └── clean_and_embed.py
└── tree.md

42 directories, 58 files
