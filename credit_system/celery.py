import os
from celery import Celery
from kombu import Exchange, Queue

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'credit_system.settings')
app = Celery('credit_system')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Configure Celery to handle connection issues better
app.conf.update(
    broker_pool_limit=1,  # Minimize connection pool for stability
    broker_connection_timeout=60,  # Increased connection timeout further
    broker_connection_retry=True,  # Enable connection retry
    broker_connection_max_retries=5,  # Increased max retries
    task_acks_late=False,  # Acknowledge tasks before execution
    task_reject_on_worker_lost=False,  # Don't reject tasks on connection loss
    worker_prefetch_multiplier=1,  # Process one task at a time
    task_serializer='json',
    result_serializer='json',
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    broker_heartbeat=30,  # Increase heartbeat interval
    accept_content=['json'],
    worker_cancel_long_running_tasks_on_connection_loss=False,  # Don't cancel tasks on connection loss
    broker_transport_options={
        'visibility_timeout': 3600,  # 1 hour
        'socket_timeout': 60,
        'socket_connect_timeout': 60,
        'retry_on_timeout': True,
        'max_retries': 5
    }
)

# Define a default queue
default_exchange = Exchange('default', type='direct')
app.conf.task_default_queue = 'default'
app.conf.task_queues = (
    Queue('default', default_exchange, routing_key='default'),
)