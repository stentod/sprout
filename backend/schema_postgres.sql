-- PostgreSQL schema for Sprout Budget Tracker (Email-only authentication)

-- Users table for multi-user support with email-only authentication
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Password reset tokens table
CREATE TABLE IF NOT EXISTS password_reset_tokens (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  token VARCHAR(255) UNIQUE NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  used BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create index for faster token lookups
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires ON password_reset_tokens(expires_at);

-- Categories table for expense categorization
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

-- Insert default user if not exists (email-only)
INSERT INTO users (id, email, password_hash) 
VALUES (0, 'default@example.com', 'dummy_hash') 
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

-- Expenses table
CREATE TABLE IF NOT EXISTS expenses (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL DEFAULT 0,
  amount DECIMAL(10,2) NOT NULL,
  description TEXT,
  category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
  timestamp TIMESTAMP NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- User preferences table for daily spending limits and category requirements
CREATE TABLE IF NOT EXISTS user_preferences (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL DEFAULT 0 UNIQUE,
  daily_spending_limit DECIMAL(10,2) DEFAULT 30.00,
  require_categories BOOLEAN DEFAULT TRUE,
  daily_rollover_enabled BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Insert default preference for user 0
INSERT INTO user_preferences (user_id, daily_spending_limit, require_categories, daily_rollover_enabled) 
VALUES (0, 30.00, TRUE, FALSE) 
ON CONFLICT (user_id) DO NOTHING;

-- Daily rollover table to track rollover amounts
CREATE TABLE IF NOT EXISTS daily_rollovers (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL DEFAULT 0,
  date DATE NOT NULL,
  rollover_amount DECIMAL(10,2) DEFAULT 0.00,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE(user_id, date)
);

-- Recurring expenses table
CREATE TABLE IF NOT EXISTS recurring_expenses (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL DEFAULT 0,
  description TEXT NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  category_id TEXT,
  frequency VARCHAR(20) NOT NULL CHECK (frequency IN ('daily', 'weekly', 'monthly')),
  start_date DATE NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
