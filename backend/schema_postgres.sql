-- PostgreSQL schema for Sprout Budget Tracker
CREATE TABLE IF NOT EXISTS expenses (
  id SERIAL PRIMARY KEY,
  user_id INTEGER DEFAULT 0,
  amount DECIMAL(10,2) NOT NULL,
  description TEXT,
  timestamp TIMESTAMP NOT NULL
); 