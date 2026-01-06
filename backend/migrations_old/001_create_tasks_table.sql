-- Migration: 001_create_tasks_table.sql
-- Description: Create tasks table with indexes

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for query performance
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_user_created ON tasks(user_id, created_at DESC);
CREATE INDEX idx_tasks_user_completed ON tasks(user_id, completed);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE tasks IS 'User tasks for todo application';
COMMENT ON COLUMN tasks.id IS 'Unique task identifier (UUID)';
COMMENT ON COLUMN tasks.user_id IS 'Foreign key to Better Auth users';
COMMENT ON COLUMN tasks.title IS 'Task title (required, 1-200 chars)';
COMMENT ON COLUMN tasks.description IS 'Task description (optional, max 1000 chars)';
COMMENT ON COLUMN tasks.completed IS 'Task completion status';
COMMENT ON COLUMN tasks.created_at IS 'Task creation timestamp (UTC)';
COMMENT ON COLUMN tasks.updated_at IS 'Last update timestamp (UTC)';