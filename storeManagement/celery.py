import os
from celery import Celery

# Django settings 모듈 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'storeManagement.settings')

app = Celery('storeManagement')

# Django settings에서 설정 로드 (CELERY_ 접두사)
app.config_from_object('django.conf:settings', namespace='CELERY')

# 자동으로 tasks.py 파일 찾기
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')