import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tradex.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
