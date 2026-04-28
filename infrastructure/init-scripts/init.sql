-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================================
-- Group: User & Authentication
-- =========================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- Group: Scope & Project Management
-- =========================================================
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

-- =========================================================
-- Group: AI Models & Tool Metadata
-- =========================================================
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

-- =========================================================
-- Group: Scheduling & Tasks
-- =========================================================
CREATE TYPE execution_type_enum AS ENUM ('CRON', 'ONCE', 'CONTINUOUS');
CREATE TYPE restart_policy_enum AS ENUM ('ALWAYS', 'ON_FAILURE', 'NEVER');

CREATE TABLE schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scope_id UUID REFERENCES scopes(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
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
    input_schema JSONB,
    output_schema JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- Group: UDTP (Uniform Data Tracking Protocol) Enums
-- =========================================================
CREATE TYPE data_stage_enum AS ENUM ('1_RAW', '2_ETL', '3_ANALYZE', '4_VISUALIZE');

-- =========================================================
-- Group: Vector Database (knowledge_embeddings) + UDTP Metadata
-- =========================================================
CREATE TABLE knowledge_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_reference TEXT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(1536), 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- UDTP Metadata Columns
    udtp_scope_ids UUID[] NOT NULL DEFAULT '{}',
    udtp_schedule_ids UUID[] NOT NULL DEFAULT '{}',
    udtp_tags TEXT[] DEFAULT '{}',
    udtp_stage data_stage_enum NOT NULL
);

-- =========================================================
-- 🔥 GIN Indexes สำหรับ UDTP เพื่อเร่งความเร็วการค้นหา
-- =========================================================
-- Index สำหรับค้นหาแบบ Intersection (&&) และ Union
CREATE INDEX idx_udtp_scope_ids ON knowledge_embeddings USING GIN (udtp_scope_ids);
CREATE INDEX idx_udtp_schedule_ids ON knowledge_embeddings USING GIN (udtp_schedule_ids);
CREATE INDEX idx_udtp_tags ON knowledge_embeddings USING GIN (udtp_tags);

-- B-Tree Index ธรรมดาสำหรับ Stage (เพราะข้อมูลมีแค่ 4 แบบ)
CREATE INDEX idx_udtp_stage ON knowledge_embeddings (udtp_stage);

-- =========================================================
-- Group: Data Lake File Catalog (MinIO Metadata)
-- =========================================================
CREATE TABLE file_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id VARCHAR(255) UNIQUE NOT NULL,    -- รหัสอ้างอิงไฟล์ (อาจใช้ UUID หรือ Hash ของไฟล์)
    file_name VARCHAR(255) NOT NULL,          -- ชื่อไฟล์ เช่น 'data_2026_q1.parquet'
    file_path TEXT NOT NULL,                  -- Path เต็มใน MinIO เช่น 's3a://processed-data/clean-news/...'
    mime_type VARCHAR(100),                   -- ชนิดไฟล์ เช่น 'application/json', 'application/parquet', 'text/csv'
    size_byte BIGINT NOT NULL DEFAULT 0,      -- ขนาดไฟล์ (ใช้ BIGINT เพราะไฟล์อาจใหญ่กว่า 2GB)
    compression VARCHAR(50) DEFAULT 'NONE',   -- รูปแบบการบีบอัด เช่น 'NONE', 'SNAPPY', 'GZIP', 'ZSTD'
    attributes JSONB DEFAULT '{}'::jsonb,     -- ข้อมูลยืดหยุ่นเพิ่มเติม (เช่น จำนวน Row, Schema Version, Encoding)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- =========================================================
    -- UDTP Metadata Columns (เพื่อให้ค้นหาไฟล์ข้าม Scope ได้)
    -- =========================================================
    udtp_scope_ids UUID[] NOT NULL DEFAULT '{}',
    udtp_schedule_ids UUID[] NOT NULL DEFAULT '{}',
    udtp_task_ids UUID[] NOT NULL DEFAULT '{}',
    udtp_tags TEXT[] DEFAULT '{}',
    udtp_stage data_stage_enum NOT NULL
);

-- =========================================================
-- Indexes สำหรับ File Assets
-- =========================================================
-- 1. Index สำหรับค้นหาไฟล์ด้วย Path หรือ Asset ID เร็วๆ
CREATE INDEX idx_file_assets_asset_id ON file_assets (asset_id);
CREATE INDEX idx_file_assets_path ON file_assets (file_path);

-- 2. GIN Indexes สำหรับค้นหาไฟล์ด้วย UDTP Logic (Intersection / Union)
CREATE INDEX idx_file_assets_udtp_scopes ON file_assets USING GIN (udtp_scope_ids);
CREATE INDEX idx_file_assets_udtp_schedules ON file_assets USING GIN (udtp_schedule_ids);
CREATE INDEX idx_file_assets_udtp_tasks ON file_assets USING GIN (udtp_task_ids);
CREATE INDEX idx_file_assets_udtp_tags ON file_assets USING GIN (udtp_tags);
CREATE INDEX idx_file_assets_udtp_stage ON file_assets (udtp_stage);