#!/usr/bin/env python3
"""
Test script to verify the logging system is working correctly
"""

import os
import sys
import logging

# Add the current directory to the path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the app to initialize logging
from app import logger, setup_logging

def test_logging():
    """Test all logging levels and functionality"""
    
    print("🧪 Testing Structured Logging System")
    print("=" * 50)
    
    # Test different log levels
    logger.debug("This is a DEBUG message - detailed debugging info")
    logger.info("This is an INFO message - general information")
    logger.warning("This is a WARNING message - something might be wrong")
    logger.error("This is an ERROR message - something went wrong")
    logger.critical("This is a CRITICAL message - system failure")
    
    # Test structured logging with context
    logger.info("User action performed", extra={
        'user_id': 123,
        'action': 'login',
        'ip_address': '192.168.1.1',
        'user_agent': 'Mozilla/5.0 (Test Browser)'
    })
    
    # Test error logging with exception
    try:
        # Simulate an error
        raise ValueError("This is a test error")
    except Exception as e:
        logger.error("Test error occurred", exc_info=True, extra={
            'user_id': 123,
            'operation': 'test_function'
        })
    
    # Test database operation logging
    logger.info("Database query executed", extra={
        'user_id': 123,
        'operation': 'SELECT',
        'table': 'expenses',
        'duration_ms': 45
    })
    
    print("\n✅ Logging test completed!")
    print("📁 Check the 'logs/' directory for log files:")
    print("   - logs/app.log (all logs)")
    print("   - logs/errors.log (errors only)")
    print("\n🔍 You can also set LOG_LEVEL environment variable:")
    print("   - LOG_LEVEL=DEBUG (most verbose)")
    print("   - LOG_LEVEL=INFO (default)")
    print("   - LOG_LEVEL=WARNING (warnings and errors only)")
    print("   - LOG_LEVEL=ERROR (errors only)")

if __name__ == "__main__":
    test_logging()
