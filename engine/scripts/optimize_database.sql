-- Database Optimization Script for COE Kernel
-- Run this after PostgreSQL is initialized with PGVector

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- ============================================
-- EPISODIC MEMORY TABLE & INDEXES
-- ============================================

CREATE TABLE IF NOT EXISTS episodic_memory (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data JSONB NOT NULL,
    agent_id VARCHAR(255),
    session_id VARCHAR(255)
);

-- Indexes for episodic memory
CREATE INDEX IF NOT EXISTS idx_episodic_task_id ON episodic_memory(task_id);
CREATE INDEX IF NOT EXISTS idx_episodic_timestamp ON episodic_memory(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_episodic_event_type ON episodic_memory(event_type);
CREATE INDEX IF NOT EXISTS idx_episodic_agent ON episodic_memory(agent_id);
CREATE INDEX IF NOT EXISTS idx_episodic_session ON episodic_memory(session_id);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_episodic_task_event ON episodic_memory(task_id, event_type, timestamp DESC);

-- ============================================
-- SEMANTIC MEMORY TABLE & INDEXES
-- ============================================

CREATE TABLE IF NOT EXISTS semantic_memory (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(255),
    confidence FLOAT DEFAULT 1.0
);

-- Indexes for semantic memory
CREATE INDEX IF NOT EXISTS idx_semantic_doc_id ON semantic_memory(document_id);
CREATE INDEX IF NOT EXISTS idx_semantic_created ON semantic_memory(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_semantic_source ON semantic_memory(source);

-- Vector similarity index using ivfflat
CREATE INDEX IF NOT EXISTS idx_semantic_embedding ON semantic_memory 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- GIN index for JSONB metadata queries
CREATE INDEX IF NOT EXISTS idx_semantic_metadata ON semantic_memory USING GIN (metadata);

-- ============================================
-- CONTEXT MEMORY TABLE & INDEXES
-- ============================================

CREATE TABLE IF NOT EXISTS context_memory (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    context_data JSONB NOT NULL,
    retrieved_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    priority INTEGER DEFAULT 0
);

-- Indexes for context memory
CREATE INDEX IF NOT EXISTS idx_context_session ON context_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_context_retrieved ON context_memory(retrieved_at DESC);
CREATE INDEX IF NOT EXISTS idx_context_expires ON context_memory(expires_at);
CREATE INDEX IF NOT EXISTS idx_context_priority ON context_memory(priority DESC);

-- Partial index for non-expired context
CREATE INDEX IF NOT EXISTS idx_context_active ON context_memory(session_id, priority DESC) 
WHERE expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP;

-- ============================================
-- EVENT BUS TABLE & INDEXES
-- ============================================

CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    stream_name VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_id UUID DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    payload JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for event bus
CREATE INDEX IF NOT EXISTS idx_events_stream ON events(stream_name, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_unprocessed ON events(processed, timestamp) WHERE processed = FALSE;
CREATE INDEX IF NOT EXISTS idx_events_event_id ON events(event_id);

-- ============================================
-- AUDIT LEDGER TABLE & INDEXES
-- ============================================

CREATE TABLE IF NOT EXISTS audit_ledger (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    operation VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    actor_id VARCHAR(255) NOT NULL,
    previous_hash VARCHAR(64) NOT NULL,
    current_hash VARCHAR(64) NOT NULL,
    data JSONB NOT NULL,
    signature VARCHAR(512)
);

-- Indexes for audit ledger
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_ledger(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_ledger(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_ledger(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_hash ON audit_ledger(previous_hash);

-- ============================================
-- BUSINESS DATA TABLES
-- ============================================

CREATE TABLE IF NOT EXISTS businesses (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    domain VARCHAR(255),
    revenue DECIMAL(15, 2) DEFAULT 0,
    leads INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_businesses_industry ON businesses(industry);
CREATE INDEX IF NOT EXISTS idx_businesses_revenue ON businesses(revenue DESC);

-- ============================================
-- PERFORMANCE OPTIMIZATIONS
-- ============================================

-- Set appropriate autovacuum settings for high-write tables
ALTER TABLE episodic_memory SET (autovacuum_vacuum_scale_factor = 0.1);
ALTER TABLE events SET (autovacuum_vacuum_scale_factor = 0.1);
ALTER TABLE audit_ledger SET (autovacuum_vacuum_scale_factor = 0.05);

-- Partition large tables by time (optional, for high volume)
-- CREATE TABLE events_partitioned (LIKE events INCLUDING ALL) PARTITION BY RANGE (timestamp);

-- ============================================
-- MAINTENANCE PROCEDURES
-- ============================================

-- Function to clean up old context memory
CREATE OR REPLACE FUNCTION cleanup_expired_context()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM context_memory 
    WHERE expires_at IS NOT NULL 
    AND expires_at < CURRENT_TIMESTAMP - INTERVAL '1 day';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to archive old events
CREATE OR REPLACE FUNCTION archive_old_events(cutoff_date TIMESTAMP WITH TIME ZONE)
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    -- In production, this would move to archive table
    DELETE FROM events 
    WHERE timestamp < cutoff_date 
    AND processed = TRUE;
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- ANALYTICS VIEWS
-- ============================================

-- Business statistics view
CREATE OR REPLACE VIEW business_stats AS
SELECT 
    COUNT(*) as total_businesses,
    SUM(revenue) as total_revenue,
    SUM(leads) as total_leads,
    SUM(conversions) as total_conversions,
    CASE 
        WHEN SUM(leads) > 0 THEN ROUND(100.0 * SUM(conversions) / SUM(leads), 2)
        ELSE 0 
    END as conversion_rate
FROM businesses;

-- Event stream statistics
CREATE OR REPLACE VIEW event_stats AS
SELECT 
    stream_name,
    event_type,
    COUNT(*) as event_count,
    MIN(timestamp) as first_event,
    MAX(timestamp) as last_event
FROM events
GROUP BY stream_name, event_type;

-- ============================================
-- GRANT PERMISSIONS
-- ============================================

-- Grant appropriate permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO coe_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO coe_app;

-- ============================================
-- VERIFICATION
-- ============================================

-- Verify indexes were created
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
