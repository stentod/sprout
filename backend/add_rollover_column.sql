-- Simple rollover column addition
-- This script adds the daily_rollover_enabled column to existing user_preferences tables

-- Add rollover column to user_preferences table
ALTER TABLE user_preferences 
ADD COLUMN IF NOT EXISTS daily_rollover_enabled BOOLEAN DEFAULT FALSE;

-- Create daily_rollovers table if it doesn't exist
CREATE TABLE IF NOT EXISTS daily_rollovers (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL DEFAULT 0,
  date DATE NOT NULL,
  rollover_amount DECIMAL(10,2) DEFAULT 0.00,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE(user_id, date)
);

-- Update existing user_preferences to have rollover column set to FALSE
UPDATE user_preferences 
SET daily_rollover_enabled = FALSE 
WHERE daily_rollover_enabled IS NULL;

-- Verify the changes
SELECT 'Rollover column added successfully' as status;
