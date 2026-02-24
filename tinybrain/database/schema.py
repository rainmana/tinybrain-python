"""SQLite database schema."""

SCHEMA = """
-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    metadata TEXT
);

-- Memory entries table
CREATE TABLE IF NOT EXISTS memory_entries (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_type TEXT NOT NULL DEFAULT 'text',
    category TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 5,
    confidence REAL NOT NULL DEFAULT 0.5,
    tags TEXT,
    source TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    accessed_at DATETIME NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS memory_entries_fts USING fts5(
    title,
    content,
    tags,
    content='memory_entries',
    content_rowid='rowid'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS memory_entries_ai AFTER INSERT ON memory_entries BEGIN
    INSERT INTO memory_entries_fts(rowid, title, content, tags)
    VALUES (new.rowid, new.title, new.content, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS memory_entries_ad AFTER DELETE ON memory_entries BEGIN
    DELETE FROM memory_entries_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS memory_entries_au AFTER UPDATE ON memory_entries BEGIN
    UPDATE memory_entries_fts SET title = new.title, content = new.content, tags = new.tags
    WHERE rowid = new.rowid;
END;

-- Relationships table
CREATE TABLE IF NOT EXISTS relationships (
    id TEXT PRIMARY KEY,
    source_entry_id TEXT NOT NULL,
    target_entry_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    strength REAL NOT NULL DEFAULT 0.5,
    description TEXT,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (source_entry_id) REFERENCES memory_entries(id) ON DELETE CASCADE,
    FOREIGN KEY (target_entry_id) REFERENCES memory_entries(id) ON DELETE CASCADE
);

-- Task progress table
CREATE TABLE IF NOT EXISTS task_progress (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    task_name TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    progress_percentage INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    started_at DATETIME,
    completed_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Context snapshots table
CREATE TABLE IF NOT EXISTS context_snapshots (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    context_data TEXT NOT NULL,
    memory_summary TEXT,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    notification_type TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 5,
    message TEXT NOT NULL,
    metadata TEXT,
    read INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_memory_session ON memory_entries(session_id);
CREATE INDEX IF NOT EXISTS idx_memory_category ON memory_entries(category);
CREATE INDEX IF NOT EXISTS idx_memory_priority ON memory_entries(priority);
CREATE INDEX IF NOT EXISTS idx_memory_created ON memory_entries(created_at);
CREATE INDEX IF NOT EXISTS idx_memory_accessed ON memory_entries(accessed_at);
CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_entry_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_entry_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_task_session ON task_progress(session_id);
CREATE INDEX IF NOT EXISTS idx_task_status ON task_progress(status);
CREATE INDEX IF NOT EXISTS idx_notifications_session ON notifications(session_id);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(read);
"""
