-- PostgreSQL schema for Sprout Budget Tracker

-- Users table for multi-user support
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Categories table for expense categorization (removed UNIQUE constraint on name)
CREATE TABLE IF NOT EXISTS categories (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL DEFAULT 0,
  name VARCHAR(100) NOT NULL,
  icon VARCHAR(10) DEFAULT '📝',
  color VARCHAR(7) DEFAULT '#6B7280',
  is_default BOOLEAN DEFAULT FALSE,
  daily_budget DECIMAL(10,2) DEFAULT 0.00,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Insert default user if not exists
INSERT INTO users (id, username, password_hash) 
VALUES (0, 'default', 'dummy_hash') 
ON CONFLICT (id) DO NOTHING;

-- Insert default categories for user 0
INSERT INTO categories (name, icon, color, is_default, user_id) VALUES
  ('Food & Dining', '🍽️', '#FF6B6B', TRUE, 0),
  ('Transportation', '🚗', '#4ECDC4', TRUE, 0),
  ('Shopping', '🛒', '#45B7D1', TRUE, 0),
  ('Health & Fitness', '💪', '#96CEB4', TRUE, 0),
  ('Entertainment', '🎬', '#FECA57', TRUE, 0),
  ('Bills & Utilities', '⚡', '#FF9FF3', TRUE, 0),
  ('Other', '📝', '#6B7280', TRUE, 0)
ON CONFLICT DO NOTHING;

-- Expenses table (updated to include category reference and user_id)
CREATE TABLE IF NOT EXISTS expenses (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL DEFAULT 0,
  amount DECIMAL(10,2) NOT NULL,
  description TEXT,
  category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
  timestamp TIMESTAMP NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- User preferences table for daily spending limits
CREATE TABLE IF NOT EXISTS user_preferences (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL DEFAULT 0 UNIQUE,
  daily_spending_limit DECIMAL(10,2) DEFAULT 30.00,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Insert default preference for user 0
INSERT INTO user_preferences (user_id, daily_spending_limit) 
VALUES (0, 30.00) 
ON CONFLICT (user_id) DO NOTHING; 