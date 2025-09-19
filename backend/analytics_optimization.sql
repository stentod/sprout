-- Analytics Performance Optimization Indexes
-- Run these to improve analytics query performance for 30-day datasets

-- Index for expenses queries by user and timestamp (most important)
CREATE INDEX IF NOT EXISTS idx_expenses_user_timestamp 
ON expenses (user_id, timestamp);

-- Index for expenses queries by user, timestamp, and category
CREATE INDEX IF NOT EXISTS idx_expenses_user_timestamp_category 
ON expenses (user_id, timestamp, category_id);

-- Index for category lookups
CREATE INDEX IF NOT EXISTS idx_default_categories_id 
ON default_categories (id);

CREATE INDEX IF NOT EXISTS idx_custom_categories_user_id 
ON custom_categories (user_id, id);

-- Index for user preferences (for simulated date lookups)
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id 
ON user_preferences (user_id);

-- Analyze tables to update statistics
ANALYZE expenses;
ANALYZE default_categories;
ANALYZE custom_categories;
ANALYZE user_preferences;
