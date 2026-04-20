-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Group: User & Authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Group: Scope & Project Management
CREATE TYPE schedule_mode_enum AS ENUM ('MANUAL', 'AI_AGENT');
CREATE TYPE scope_status_enum AS ENUM ('ACTIVE', 'PAUSED');

CREATE TABLE scopes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    goal TEXT,
    schedule_mode schedule_mode_enum NOT NULL,
    status scope_status_enum DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Group: AI Models & Tool Metadata
CREATE TYPE model_type_enum AS ENUM ('LLM', 'TIME_SERIES', 'CLASSIFICATION', 'EXTERNAL_API');
CREATE TABLE ai_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255) NOT NULL,
    version VARCHAR(50),
    framework VARCHAR(100),
    model_path TEXT,
    model_type model_type_enum NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TYPE tool_language_enum AS ENUM ('Python', 'Go', 'C++');
CREATE TYPE author_type_enum AS ENUM ('HUMAN', 'AI_GENERATED');
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ai_model_id UUID REFERENCES ai_models(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    language tool_language_enum NOT NULL,
    script_url TEXT NOT NULL,
    input_schema JSONB,
    output_schema JSONB,
    author_type author_type_enum NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Group: Scheduling & Tasks
CREATE TYPE execution_type_enum AS ENUM ('CRON', 'ONCE', 'CONTINUOUS');
CREATE TYPE restart_policy_enum AS ENUM ('ALWAYS', 'ON_FAILURE', 'NEVER');

CREATE TABLE schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scope_id UUID REFERENCES scopes(id) ON DELETE CASCADE,
    task_mode schedule_mode_enum NOT NULL,
    execution_type execution_type_enum NOT NULL,
    restart_policy restart_policy_enum,
    is_sequential BOOLEAN DEFAULT TRUE,
    cron_expression VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TYPE task_type_enum AS ENUM ('SEARCH', 'ETL', 'TRADITIONAL_LOGIC', 'AI_INFERENCE', 'VISUALIZE');
CREATE TYPE engine_type_enum AS ENUM ('AIRFLOW_DAG', 'STREAMING_WORKER');

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schedule_id UUID REFERENCES schedules(id) ON DELETE CASCADE,
    task_type task_type_enum NOT NULL,
    tool_id UUID REFERENCES tools(id) ON DELETE CASCADE,
    engine_type engine_type_enum NOT NULL,
    depends_on_task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    priority INT DEFAULT 1,
    execution_order INT,
    broker_topic VARCHAR(255),
    arguments JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Group: Vector Database (knowledge_embeddings)
CREATE TABLE knowledge_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scope_id UUID REFERENCES scopes(id) ON DELETE CASCADE,
    source_reference TEXT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(1536), -- ขนาด Vector ตามโมเดล (เช่น OpenAI text-embedding-ada-002 ใช้ 1536)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);