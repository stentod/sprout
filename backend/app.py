# Import the modular app for backward compatibility
import os

# Ensure DEBUG_MODE is set for development when using start.sh
if __name__ == '__main__':
    # Set DEBUG_MODE to true if not already set (for development)
    if 'DEBUG_MODE' not in os.environ:
        os.environ['DEBUG_MODE'] = 'true'
        print("🔧 DEBUG_MODE set to true for development")

from main import app

if __name__ == '__main__':
    # Only run the development server if this file is run directly
    # In production, gunicorn will import and run the app
    from utils import DEBUG, PORT
    app.run(debug=DEBUG, port=PORT, host='0.0.0.0') 