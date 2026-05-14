.
├── ai-engine
│   ├── core
│   │   └── llm.py
│   ├── Dockerfile
│   ├── pre-validator
│   ├── prompts
│   │   ├── ScheduleArchitect.md
│   │   ├── TaskOrchestrator.md
│   │   ├── ToolResearcher&DeveloperStep1.md
│   │   └── ToolResearcher&DeveloperStep2.md
│   ├── requirements.txt
│   ├── sanbox
│   └── src
│       └── main.py
├── ai_engin.log
├── backend
│   ├── Dockerfile
│   ├── go.mod
│   ├── requirements.txt
│   └── src
│       ├── api
│       │   ├── data_retrieval.py
│       │   ├── schedules.py
│       │   └── scopes_management.py
│       ├── core
│       ├── db
│       ├── main.py
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
│   │   ├── icons.svg
│   │   └── locales
│   │       ├── en
│   │       │   └── translation.json
│   │       └── th
│   │           └── translation.json
│   ├── README.md
│   ├── src
│   │   ├── App.css
│   │   ├── App.jsx
│   │   ├── assets
│   │   │   ├── hero.png
│   │   │   ├── react.svg
│   │   │   └── vite.svg
│   │   ├── components
│   │   │   ├── CodeEditorModal.jsx
│   │   │   ├── DynamicBlocks.jsx
│   │   │   ├── DynamicBlocks.jsx.back
│   │   │   ├── DynamicWidgetRenderer.jsx
│   │   │   └── Skeletons.jsx
│   │   ├── hooks
│   │   │   └── useLiveStream.js
│   │   ├── i18n.jsx
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
│   ├── AddNewTask1.png
│   ├── AddSchedule1.png
│   ├── AI_Agentic_Scheduling-2026-04-19-133737.png
│   ├── CreateScope1.png
│   ├── CreateTool1.png
│   ├── ScheduleManager1.png
│   ├── SchedulePage1.png
│   ├── ScopePage1.png
│   ├── TaskConfiguration1.png
│   ├── TaskManamger1.png
│   └── ToolLibrary1.png
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
├── tools-library
│   ├── ai-inference
│   │   ├── llm_sentiment.go
│   │   └── rule_base_sentiment.py
│   ├── external-apis
│   │   ├── fetch_data.py
│   │   └── WeatherSearchSummary.py
│   └── traditional-logic
│       ├── clean_and_embed.py
│       └── generate_dashboard_blocks.py
├── tree.md
└── utils
    ├── setup.py
    └── utils
        ├── __init__.py
        ├── udtp_data_manager.py
        ├── UDTP_Library_v2_Standard.md
        ├── udtp_mongo.py
        └── udtp_postgres.py

42 directories, 84 files
