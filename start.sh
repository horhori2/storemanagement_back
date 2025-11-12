cd /home/ubuntu/storemanagement_back
source venv/bin/activate
gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 1200 --graceful-timeout 1200 storeManagement.wsgi:application
