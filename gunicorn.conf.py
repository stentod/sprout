# Gunicorn configuration for production deployment

import os

# Server socket - bind to port 5000 internally (nginx proxies external PORT)
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = int(os.environ.get('WEB_CONCURRENCY', '1'))
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "sprout-budget-tracker"

# Server mechanics
preload_app = True
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = ""
# certfile = ""
