# Import the modular app for backward compatibility
from main import app

if __name__ == '__main__':
    # Only run the development server if this file is run directly
    # In production, gunicorn will import and run the app
    from utils import DEBUG, PORT
    app.run(debug=DEBUG, port=PORT, host='0.0.0.0') 