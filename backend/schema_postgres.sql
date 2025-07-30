-- PostgreSQL schema for Sprout Budget Tracker

-- Categories table for expense categorization
CREATE TABLE IF NOT EXISTS categories (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  icon VARCHAR(10) DEFAULT '📝',
  color VARCHAR(7) DEFAULT '#6B7280',
  is_default BOOLEAN DEFAULT FALSE,
  daily_budget DECIMAL(10,2) DEFAULT 0.00,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default categories
INSERT INTO categories (name, icon, color, is_default) VALUES
  ('Food & Dining', '🍽️', '#FF6B6B', TRUE),
  ('Transportation', '🚗', '#4ECDC4', TRUE),
  ('Shopping', '🛒', '#45B7D1', TRUE),
  ('Health & Fitness', '💪', '#96CEB4', TRUE),
  ('Entertainment', '🎬', '#FECA57', TRUE),
  ('Bills & Utilities', '⚡', '#FF9FF3', TRUE),
  ('Other', '📝', '#6B7280', TRUE)
ON CONFLICT (name) DO NOTHING;

-- Expenses table (updated to include category reference)
CREATE TABLE IF NOT EXISTS expenses (
  id SERIAL PRIMARY KEY,
  user_id INTEGER DEFAULT 0,
  amount DECIMAL(10,2) NOT NULL,
  description TEXT,
  category_id INTEGER REFERENCES categories(id) DEFAULT NULL,
  timestamp TIMESTAMP NOT NULL
);

-- User preferences table for daily spending limits
CREATE TABLE IF NOT EXISTS user_preferences (
  id SERIAL PRIMARY KEY,
  user_id INTEGER DEFAULT 0 UNIQUE,
  daily_spending_limit DECIMAL(10,2) DEFAULT 30.00,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default preference for user 0
INSERT INTO user_preferences (user_id, daily_spending_limit) 
VALUES (0, 30.00) 
ON CONFLICT DO NOTHING; 