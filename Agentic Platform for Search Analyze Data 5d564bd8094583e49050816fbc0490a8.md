# Agentic Platform for Search Analyze Data

Progress: 0%
Assignee: Athip Yuthaworawit
Status: Not started

## About the project:

 Create an application for adding company scopes that need to track news, stock prices, financial statements, and financial status. Use AI to predict the financial status of companies or upcoming events.

## Phase 1: Build Data Pipeline & Infrastructure (Flexible & Scalable)

### 1. Data Lake, Data Warehouse & Storage (Write `docker-compose.yml` )
- MinIO (S3-compatible) - *Data Lake & Script Storage*
    
     Collect all raw data (JSON, CSV from API).
    
    **1. Bucket: `ai-tool-scripts`**
    
    - **Responsibilities:** Store code files (Python, Go, Rust) created by AI or humans.
    - **Internal Structure (Prefix/Folder):**
        - `/traditional-logic/` (Module A)
        - `/ai-inference/` (Module B)
        - `/sandbox-temp/` (For code to be tested)
    
    **2. Bucket: `Raw Data` (also known as Bronze Layer)**
    
    - **Responsibility:** Collect raw data that has just been retrieved from the API (JSON, CSV, HTML) without any modifications, so that we can always revert to the original data if ETL encounters any issues.
    - **Internal Structure (Prefix/Folder):**
        - `/financial-statements/year=2024/quarter=1/`
        - `/stock-prices/ticker=AAPL/`
        - `/news/year=2024/month=10/`
    
    **3. Bucket: `Processed Data` (also known as the Silver/Gold Layer)**
    
    - **Responsibilities:** Collect data that has passed through Task ETL/ELT (Spark Processing) and is already cleaned, then convert it into fast-reading formats such as **Apache Parquet** or **Delta Lake**.
    - **Internal Structure (Prefix/Folder):**
        - `/clean-financials/`
        - `/aggregated-prices/`
    
     Store Tool Scripts (Python, Go, Rust code written by AI or humans)
    
- PostgreSQL - Metadata, State Management & Vector Store
   PostgreSQL serves as the "brain" for managing Users, Scopes, Tools, and the status of AI.
    1. **Group: Vector Database
    Enable Extension:** Enable `pgvector` in PostgreSQL to store High-dimensional Vector data without adding new Database Components
        
        • **`knowledge_embeddings`**: When Task 3.2 (ETL) is executed, Text data (such as economic news, meeting reports) will be processed for Chunking and Embedding generation, stored here for AI Inference (Module B) to perform Retrieval-Augmented Generation (RAG) retrieves relevant context for sentiment analysis or event prediction with high accuracy. 
        - `id` (UUID, PK)
        - `scope_id` (FK)
        - `source_reference` (URL or Path of the news file/financial statement in MinIO)
        - `chunk_text` (Text snippet that has been extracted)
        - `embedding` (Vector data type `VECTOR(1536)` or according to the size of the Embedding Model)
        - `created_at` (Timestamp)
        
    2. **Group: User & Authentication** 
        
        • **`users`**: Store user information
        - `id` (UUID, PK)
        - `email`, `password_hash`, `full_name` 
        - `created_at`, `updated_at`
        
    3. **Group: Scope & Project Management** 
        
        • **`scopes`**: Collect details of the scope of work created by the user
        - `id` (UUID, PK)
        - `user_id` (FK -> users.id)
        - `name`, `description`, `goal` 
        - `schedule_mode` (Enum: `'MANUAL'`, `'AI_AGENT'` ) (Choose whether to create schedule manually or let AI create it)
        - `status` (Enum: `'ACTIVE'`, `'PAUSED'` )
        
    4. **Group: AI Models & Tool Metadata** 
        
        • **`ai_models`**: Model Metadata & Assets
        Store only model data and the location of the Weights file.
        - `id` (UUID, PK)
        - `model_name` (e.g., `'Llama-3-8B-Instruct'`, `'LSTM-Stock-Predictor'` )
        - `version` (e.g., `'v1.0'` )
        - `framework` (e.g., `'PyTorch'`, `'ONNX'`, `'GGUF'` )
        - `model_path` (URL pointing to a `.safetensors` or `.bin` file in MinIO)
        - `model_type` (Enum: `'LLM'`, `'TIME_SERIES'`, `'CLASSIFICATION'`,`'EXTERNAL_API'` )
        
        • **`tools`**: Execution Logic & Scripts
        Store scripts used for operations, including scripts that perform Preprocess -> Load Model -> Postprocess
        - `id` (UUID, PK)
           `ai_model_id` (FK -> ai_models.id, Nullable) *— Insert this FK to indicate which model this script is written to load or manage (if it's a general script that doesn't use AI, set the value to NULL)* 
        - `name` (e.g., `'Llama-3 Inference Script'`, `'RSI Calculator'` )
        - `language` (Enum: `'Python'`, `'Go'`, `'C++'` )
        - `script_url` (URL pointing to a `.py` or `.go` script file in MinIO)
        - `input_schema`, `output_schema` (JSON)
        - `author_type` (Enum: `'HUMAN'`, `'AI_GENERATED'` )
        
    5. **Group: Scheduling & Tasks** 
        
        • **`schedules`**: Defines the work schedule for each Scope
        - `id` (UUID, PK)
        - `scope_id` (FK)
        - `task_mode` (Enum: `'MANUAL'`,  `'AI_AGENT'` ) (Choose whether to create the task manually or let AI create it)
        - `execution_type`: (Enum: `'CRON'`, `'ONCE'`, `'CONTINUOUS'` ) `CONTINUOUS` is used for Streaming tasks that need to be left running continuously 
        - `restart_policy`: (Enum: `'ALWAYS'`, `'ON_FAILURE'`, `'NEVER'` ) For Streaming tasks, if the script crashes, should the system automatically restart? [ `CONTINUOUS` ]
        - `is_sequential` (Boolean: Run consecutively or separately by time)
        - `cron_expression` (For setting independent schedules, specifying run schedule times)
        
        • **`tasks`**: Execution Instances & Configs
        Store instances of tasks to be executed by Airflow or RabbitMQ/Apache Kafka, along with special configurations for each run.
        - `id` (UUID, PK)
        - `schedule_id` (FK)
        - `task_type` (Enum: `'SEARCH'`, `'ETL'`, **`'TRADITIONAL_LOGIC'`**, `'AI_INFERENCE'`, `'VISUALIZE'` )
        - `tool_id` (FK -> tools.id)
        - `engine_type`: (Enum: `'AIRFLOW_DAG'`, `'STREAMING_WORKER'` ) To specify where this Task will be executed.
        - `depends_on_task_id` (Self-referencing FK for tasks that need to be performed sequentially, used to tell Airflow who needs to wait for whom (A $\rightarrow$ B $\rightarrow$ C) to create the correct Workflow) [ `AIRFLOW_DAG` ]
        - `priority` (used for queue jumping, competing for resources when work overloads the server of each Apache Spark scope) [ `AIRFLOW_DAG` ]
        - `execution_order` (used for displaying numbers in order for easy viewing on the UI (1, 2, 3...)) [ `AIRFLOW_DAG` ]
        - `broker_topic`: (String, Nullable) For Streaming tasks, specify the Topic name in the Message Broker (e.g., RabbitMQ) that this script needs to read or write data to [ `STREAMING_WORKER` ]
        - `arguments` (JSONB) *Store Configuration (see example below)* 
        
         Example of data collection in the `arguments` column (JSONB)
           Using the `JSONB` data type in PostgreSQL allows you to freely store configurations that have different structures for each task:
        
        **Case 1: Task runs LLM Model (AI Inference)** 
        The script in `tools` will pull the model path from `ai_models` and retrieve the generation configuration from `tasks.arguments`
        
        `{
          "temperature": 0.7,
          "max_tokens": 1024,
          "top_p": 0.9,
          "system_prompt": "You are a financial analyst. Your task is to read news and assess sentiment..."
        }`
        
        **Case 2: Task calls an External API (such as OpenAI or a News API)**
        
        `{
          "api_endpoint": "https://api.openai.com/v1/chat/completions",
          "api_key": "sk-proj-xxxxxxxxxxxxxx",
          "retry_attempts": 3
        }`
        
        **Case 3: Calculation Task using Traditional Logic (e.g., stock price alert / RSI)**
        
        `{
          "ticker": "AAPL",
          "timeframe": "1D",
          "rsi_period": 14,
          "overbought_threshold": 70,
          "oversold_threshold": 30
        }`
        
- MongoDB - *NoSQL Data Warehouse
   MongoDB*  is responsible for storing data with an unstructured or semi-structured format, or data that is a set of results from AI *.*
    
    **Collection: `processed_data`**
    
     Collect financial data or information that has already been cleaned (ETL) to prepare for sending to the frontend.
    
    `{
      "scope_id": "UUID",
      "task_id": "UUID",
      "ticker": "XAU/USD",
      "timestamp": "ISODate",
      "data_points": {
        "open": 2000.5,
        "close": 2010.2,
        "rsi": 65.5, // Result from Module A [cite: 41]
        "financial_ratios": { "PE": 15.5, "DE": 0.8 } [cite: 43]
      }
    }`
    
    **Collection: `ai_insights`**
    
     Collect prediction results and analyses from AI Inference (Module B)
    
    `{
      "scope_id": "UUID",
      "model_id": "UUID",
      "insight_type": "SENTIMENT", 
      "content": "Bullish", // From Module B [cite: 51]
      "confidence_score": 0.89,
      "summary": "This quarter's financial report shows a high growth trend...",
      "extracted_events": [ { "date": "2026-05-15", "event": "Dividend Payment" } ] [cite: 53]
    }`
    
    **Collection: `audit_logs`**
    
     Keep a history of script runs in the AI Sandbox for security.
    
    `{
      "task_id": "UUID",
      "status": "VALIDATED/FAILED",
      "sandbox_logs": "Standard Output from Container...",
      "execution_time_ms": 1500
    }`
    
### 2. Data Orchestration & Compute Engine (Core of the Pipeline)

- Apache Airflow (The Orchestrator / DAG Scheduler)<br>Responsible for managing the entire workflow, setting schedules, and coordinating tasks with other services in sequence.

- Apache Spark (The Compute Engine / Distributed Processing)<br>Awaiting instructions from Airflow to retrieve raw data for rapid distributed ETL/ELT processing.

- Apache Kafka or RabbitMQ (Message Broker & Event Streaming)

  - *Role:* While Airflow handles batch jobs (such as pulling financial statements every quarter), the Streaming system takes over tasks that require extremely low latency, such as monitoring price actions (Price Action) of XAU/USD, BTC/USD, or Forex at minute or second levels.
  - Tool Script Created by AI for Price Monitoring *: This script* will publish data into the Message Broker when certain conditions are met (e.g., a candlestick reversal or price breaking support level). The system will then trigger the alert model or immediately run Module A without waiting for the Airflow schedule cycle.

- Triggering Mechanism (API Endpoint)<br>The connection between Streaming and Batch Scopes is made through a central API Endpoint of the Backend (e.g., `/api/v1/schedules/trigger/{schedule_id}` ). The Backend will convert this Request into a REST API command to instruct Apache Airflow to initiate a new DAG Run, along with attaching specific Configuration via `argument` variables defined in `the` PostgreSQL `tasks`.
  
---

### 3. (A) Workflow Batch Tasks (Controlled by Airflow)
    
- **Task 3.1: Searching and Collecting Data**<br>
Airflow executes a Tool Script (such as Python or Go code to pull stock/news API data)<br>
Import raw data into MinIO.

- **Task 3.2: ETL/ELT Task (Spark Processing)**<br>
Airflow instructs Spark to start running.
Spark extracts raw data from MinIO, cleans it, and converts the format.
Save the cleaned data back to MinIO in **Apache Parquet** or **Delta Lake** format (to achieve maximum performance and preserve the data schema without using Data Connector API conversions) then load necessary data into PostgreSQL/MongoDB

- **Task 3.3: Hybrid Analytics & Prediction Task**<br>  
In this section, Apache Airflow will check the "Configuration" specified by the user or AI in the Schedule to determine which processing modules are required for this task. These can be divided into two modules.<br>
  - Module A: Traditional Logic & Calculation (Ordinary Code)<br>Ideal for tasks with fixed formulas or conditions that do not require guesswork. Processes quickly and accurately with 100% precision.
    - **What works:** Python, Go, or C++ code (existing tool scripts or those synthesized by AI)
    - **Example of usage:**
        - **Technical Analysis:** Calculate RSI, MACD, Moving Averages, or identify reversal points from Candlestick Patterns using historical price data.
        - **Financial Ratios:** Calculate financial ratios from the balance sheet (e.g., P/E, P/BV, D/E Ratio)
        - **Rule-based Alert:** Scan data for specific conditions, such as "Notify when the price drops by more than 5% within 1 hour."
    
    - Module B: AI & Machine Learning Inference<br>Suitable for analyzing data without clear structure or for identifying patterns that are too complex for ordinary code to detect.
    
      - **What works:** LLM (e.g., GPT-4, Llama 3), Time-Series Forecasting Models, or Classification Models
      - **Example of usage:**
          - **Sentiment Analysis:** Have the LLM read economic news articles or meeting reports and then assess whether the content is "Positive (Bullish)" or "Negative (Bearish)."
          - **Predictive Modeling:** Forecast the likelihood that the company will announce profit growth in the next quarter.
          - **Event Extraction:** Extracting Key Information from Financial Reports (e.g., Dividend Payment Dates, Executive Resignations)

- **Task 3.4: Data Visualizations/Summarize**<br>Retrieve data from MongoDB/PostgreSQL to create a summary table, prepared for the frontend to retrieve and display.

---

### 3. (B) Workflow Streaming Tasks (Event-Driven Pipeline) (Controlled by RabbitMQ or Apache Kafka)
    
- **Task 3.1: Continuous Data Ingestion (WebSocket & Stream)**

  - **Workflow:** Instead of scheduling tasks to run at specific times, the system creates Streaming Worker Containers that run code (such as Go, Rust, or Python) as long-running processes to maintain persistent connections via WebSocket or gRPC at all times.
  - **Process:** The script receives real-time price data or news (Tick-by-Tick) immediately upon any market movement, then sends the raw data directly to **a Message Broker (such as RabbitMQ or Apache Kafka)**. Additionally, the raw data may be written to MinIO asynchronously (in the background) for backup purposes.

- **Task 3.2: Real-time Stream Processing (In-memory ETL)**

  - **Work:** Another set of Workers (which may use Apache Spark Structured Streaming or be written in Go/Rust for maximum speed) will Subscribe (track) Topics from the Message Broker.
  - **Process:** Perform on-the-fly data cleaning (e.g., filtering out error data) and perform rapid aggregation, such as consolidating tick data from each second into one-minute or five-minute candlestick charts (OHLCV). Then, send the cleaned data back to the Message Broker in a new topic for further analysis.

- **Task 3.3: Event-Driven Analytics & Prediction Task** 
In this section, the Message Broker will distribute data to Workers for further processing according to the user-defined configuration. It will still be divided into 2 Modules but will operate in Real-time:

  - **Module A: Traditional Logic (Fast Lane)**
      - *Suitable for:* Calculations requiring low latency
      - *What it does:* Go, Rust, or C++ code (user-uploaded or selected from a library) that captures incoming stream data.
      - *Example of usage:* As soon as a new candlestick is received, the system immediately calculates the RSI and MACD values. If conditions are met (e.g., RSI breaks above 30 or a reversal pattern occurs), the system will send a rule-based alert to notify the user or trigger an API order execution immediately.
  - **Module B: AI & Machine Learning Inference (Advanced Track)**
      - *Suitable for:* In-depth analysis triggered by abnormal events in Module A.
      - *What works:* LLM or a Time-Series Model that has already been deployed and is available as an internal API.
      - *Example of usage:* If Module A detects that the price of BTC/USD has dropped significantly and unusually (Event Trigger), the system will instruct Module B to immediately retrieve the latest headlines from the News Stream and analyze the sentiment using LLM to determine what negative news has occurred, in order to confirm the trading signal.

- **Task 3.4: Live Broadcasting & State Update**

  - **Process:** Instead of creating a Summary Table and waiting for the Frontend to request it (Pull), the system uses a Message Broker to send the analysis results to the WebSocket Server, which then distributes the data (Push) to the user's Dashboard page. This enables graphs and notifications to update in real-time (Live update).
  - **Storage:** The latest state data will be "Upserted" (updated and appended if already present) into **MongoDB** to ensure the system always has the most current information available in case a user opens the Web Application page again.

---

### 3. (C) Workflow Mix Tasks (Hybrid Event-Triggered Pipeline)
    
**Concept:** 
A hybrid (Mix) approach that breaks the limitations of traditional pipelines by allowing each Scope to operate independently and assemble Tasks as needed (not required to complete all 4 Tasks; if there are no final Tasks like Visualize, the system will automatically hide the corresponding UI section).

 This system employs a **Cross-Pipeline Triggering** mechanism **via API** to enable streaming speed to work seamlessly with the depth of analysis provided by batch LLM processing.

### Example of Scope Collaboration (Cross-Scope Execution):

**Scope 1: The Background Data Collector (Batch Schedule)**
*   **Function:** Fetches news data at scheduled intervals (e.g., every 1 hour).
*   **Workflow:** Airflow triggers Task 3.1 to fetch news from an API → passes it to Task 3.2 for ETL and cleaning the news text → saves to MinIO and generates Vector Embeddings into the PostgreSQL `knowledge_embeddings` table.
*   **Status:** Runs continuously in independent scheduled batches.

**Scope 2: The Watchdog (Streaming Schedule)**
*   **Function:** Monitors stock or asset prices in real-time.
*   **Workflow:** Task 3.1 opens a WebSocket to receive stock prices continuously → Task 3.3 (Module A) uses Traditional Logic to analyze anomalies (e.g., detecting a volume spike or a price breaking a key support level).
*   **The Trigger:** When an anomaly occurs, the system will not wait for the next Batch cycle. Instead, it immediately sends an HTTP POST Request (API) with an attached Payload (e.g., `{"ticker": "AAPL", "timestamp": "...", "event_type": "BREAKOUT"}`) to trigger the execution of Scope 3 right away.

**Scope 3: The Deep Analyzer (Triggered Batch DAG)**
*   **Function:** Runs only once when invoked, acting as the "brain" for final decision-making.
*   **Workflow Context Payload:** Receives the data payload from Scope 2.
*   **Workflow Skip Logic:** Bypasses Tasks 3.1 and 3.2, starting immediately at Task 3.3 (Module B: AI Inference).
*   **Workflow AI Analysis:** The LLM uses Tools to query the analyzed price data from MongoDB and utilizes RAG to retrieve the latest news from Scope 1. It combines these elements to evaluate the situation (e.g., determining what news caused a price drop) and assesses Sentiment to recommend the next course of action.
*   **Workflow Visualization (Task 3.4):** Sends a comprehensive summary analysis, integrating both charts and text, as an alert to a Dashboard or directly into an application.

 **The Triggering Mechanism (API Endpoint)** 
The connection between Streaming and Batch Scopes is made through a central API Endpoint of the Backend (e.g., `/api/v1/schedules/trigger/{schedule_id}` ). The Backend will convert this Request into a REST API command to instruct Apache Airflow to initiate a new DAG Run, along with attaching specific Configuration via `argument` variables defined in `the` PostgreSQL `tasks`.

---

### 4. CI/CD & AI Sandboxing (Security and Automation)
    
**GitHub Actions:** When code is pushed (PySpark, Airflow DAGs), it will automatically build a Docker Image and push it to the Registry.

**1. Pipeline Validate AI Tool Script**
Pre-validation Pipeline for Code Review Before Entering Sandbox
**Static Code Analysis & Security Check (Pre-execution)**
- Before the system builds and runs the AI-generated Tool Script (AI Schedule) in an isolated Docker container, add a static analysis layer to verify the code without running it. This will save resources and prevent crashes.
    1. **Syntax & AST Check:** Uses modules such as `ast` (for Python) to verify that the code structure is correct and can be compiled successfully.
    2. **Linter & Malicious Pattern Scanner:** Scans for unauthorized library imports (such as `os.system`, `subprocess` for hacking) or detects infinite loops without a conditional break.
    3. **Language-Specific Compiler Check:** If the AI synthesizes code in a low-level language (such as Go or Rust), attempt to run the command `go build` or `cargo check` in a limited environment to evaluate the results first. If there are errors from the compiler, send the error log back to the AI for immediate correction (self-correction) without expending resources to run a full container.
   
**2. Pipeline AI Code Sandbox**
When AI generates a new Tool Script (AI Schedule), the code will first be run in an isolated Docker container to test its functionality and ensure it does not damage the system. Once validated, the path will be recorded in PostgreSQL, and Airflow will be instructed to use it for actual operations. 
        
**Resource & Time Limits:** Running AI-generated code in a Docker Container carries risks such as infinite loops or memory leaks. *Recommendations:* Strictly configure `cgroups` in Docker (e.g., limit RAM to 512MB, CPU to 1 core) and set a Timeout (e.g., kill the process immediately if the script runs for more than 60 seconds).
        
**Network Restriction:** Code within the Sandbox should not have direct access to the internal Database (Postgres/Mongo). It should only be permitted to access the Internet for pulling external APIs.
        
If the test fails, you must submit the error log to the LLM model for code improvement.

---

### 5.  Kubernetes & Cloud Deployment
    
Use **Minikube** to run K8s locally
Write  `a .yaml file` to deploy the entire system (Airflow, Spark Workers, DBs, MinIO) to simulate real cloud operation
        

### Phase 2: Build AI Agent Application (Frontend & Backend)

- 1. Front End (User Interface & Dashboard)
    
    **Dashboard:** Displays news monitoring results, price graphs, financial statement trends, and *AI prediction outcomes*.
    
    **Scope & Schedule Manager:** UI for creating scopes, tracking, and setting schedules.
    
- 2. Back End (Core Services & API)
    - User Session and Asset Management System
    - API for Managing Scope (Add Topic, Add Goal)
        
        
        1.  Create New Scope
        2.  Add Topic of Scope
        3.  Add Scope Goal
        4.  Select Manual Scope or AI Scope
        5.  If Select Manual Scope Add new Schedule and define specific Goal for the Schedule (Manual Schedule or AI Schedule)
            
             If **Manual Schedule**
            
            1.  Add Searching and Collect Data
            2.  Add ETL/ELT Task (Spark Processing)
            3.  AI Inference & Prediction
            4.  Data Visualizations/Summarize
        
        **Manual Schedule:** The user selects an existing Tool Script or uploads code (Python/Go) into the system (save to MinIO).
        
        **AI Schedule (Autonomous Agent):** The user sets a goal (e.g., "Retrieve the financial statements of Company X every quarter"). The AI analyzes the goal and **generates a** new **tool script** or selects an existing one. The script is then sent to *the AI Code Sandbox* for testing. If successful, the tool is automatically added to the system and a batch task is set up in Airflow or a streaming task is initiated.
        

### Project Diagrams

![](Agentic%20Platform%20for%20Search%20Analyze%20Data/AI_Agentic_Scheduling-2026-04-19-133737.png)

### Project Folder Structure
```code
`agentic-platform/
├── .github/
│   └── workflows/            # CI/CD Pipelines (e.g., Code Validation, Docker Build, K8s Deployment)
│
├── infrastructure/           # Database, Message Broker, and Deployment Configs
│   ├── docker-compose.yml    # For running Local Infrastructure
│   ├── k8s/                  # Kubernetes Manifests for Deploying to Cloud (Phase 1: Task 5)
│   └── init-scripts/         # Scripts for initializing the database, such as init.sql for Postgres
│
├── backend/                  # Core API Service (Phase 2: Task 2)
│   ├── src/
│   │   ├── api/              # API Endpoints (Scope, Task, Model Management)
│   │   ├── core/             # Main system logic (Trigger Airflow, State Management)
│   │   ├── db/               # Code for connecting to Postgres (Metadata) and Mongo (Results)
│   │   └── services/         # Services for calling AI or External APIs
│   ├── Dockerfile
│   └── requirements.txt / go.mod
│
├── frontend/                 # Web Application & Dashboard (Phase 2: Task 1)
│   ├── src/
│   │   ├── components/       # UI Components (graphs, tables)
│   │   ├── pages/            # Dashboard page, Scope/Schedule management page
│   │   └── hooks/            # Connect WebSocket for receiving Live Data (Streaming)
│   └── package.json
│
├── data-pipeline/            # Batch Processing section (Phase 1: Task 3.A)
│   ├── airflow/
│   │   ├── days/             # Airflow DAG code for controlling the workflow
│   │   └── config/
│   └── spark-jobs/           # PySpark code for ETL/ELT data cleaning into MinIO
│
├── streaming-pipeline/       # Event-Driven & Real-time section (Phase 1: Task 3.B)
│   ├── ingestion/            # Workers open WebSocket to receive Tick-by-Tick data
│   ├── processors/           # In-memory ETL & Fast-lane Logic (Go/Rust/Python)
│   └── consumers/            # Scripts for capturing events from Kafka/RabbitMQ
│
├── ai-engine/                # Artificial Intelligence Engine and Simulation Code Execution (Phase 1: Task 4)
│   ├── sandbox/              # Docker configurations, cgroups setup for secure AI code execution
│   ├── pre-validator/        # AST Check & Linter: Scans code before entering the Sandbox
│   └── prompts/              # Stores System Prompts for the Agent
│
├── tools-library/            # General Tool Scripts repository that will be pulled to MinIO
│   ├── traditional-logic/    # e.g. RSI formula, MACD, price alerts
│   ├── ai-inference/         # scripts for loading models and running LLM
│   └── external-apis/        # scripts for fetching News API, Stock API
│
└── setup-scripts/            # Scripts for configuring the system after opening the container
└── [init-minio-buckets.py](http://init-minio-buckets.py/) # Code to automatically create Buckets 'ai-tool-scripts' and 'raw-data'`
```