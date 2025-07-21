from django.core.management.base import BaseCommand
from core.tasks import ingest_customer_data, ingest_loan_data

class Command(BaseCommand):
    help = 'Ingest initial data from Excel files'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting data ingestion...')
        
        # First ingest customers (since loans depend on customers)
        self.stdout.write('Ingesting customer data...')
        ingest_customer_data.delay()
        
        # Then ingest loans
        self.stdout.write('Ingesting loan data...')
        ingest_loan_data.delay()
        
        self.stdout.write('Data ingestion tasks have been queued.')
