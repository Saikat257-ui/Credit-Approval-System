from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Reset database sequences'

    def handle(self, *args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT setval(pg_get_serial_sequence('"core_customer"', 'customer_id'), 
                    (SELECT MAX(customer_id) FROM "core_customer"));
                SELECT setval(pg_get_serial_sequence('"core_loan"', 'loan_id'), 
                    (SELECT MAX(loan_id) FROM "core_loan"));
            """)
            self.stdout.write(self.style.SUCCESS('Successfully reset sequences'))
