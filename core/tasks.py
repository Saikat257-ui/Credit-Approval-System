from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded, TaskRevokedError
from celery.utils.log import get_task_logger
import pandas as pd
from .models import Customer, Loan
from datetime import datetime
import time
from django.db import transaction, DatabaseError
from redis.exceptions import ConnectionError, TimeoutError

logger = get_task_logger(__name__)

def retry_on_exception(retries=3, delay=5):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError, DatabaseError) as e:
                    if attempt == retries - 1:  # Last attempt
                        raise  # Re-raise the last exception
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds...")
                    time.sleep(delay)
            return None  # In case all retries fail
        return wrapper
    return decorator

@shared_task
def ingest_customer_data():
    print("Starting customer data ingestion...")
    df = pd.read_excel('customer_data.xlsx')
    print("Columns in customer_data.xlsx:", df.columns.tolist())  # Debug print
    print(f"Found {len(df)} customer records to process")
    for index, row in df.iterrows():
        try:
            customer, created = Customer.objects.update_or_create(  # type: ignore
                customer_id=row['Customer ID'],  # Updated column name
                defaults={
                    'first_name': row['First Name'],
                    'last_name': row['Last Name'],
                    'age': row['Age'],
                    'phone_number': row['Phone Number'],
                    'monthly_salary': row['Monthly Salary'],
                    'approved_limit': row['Approved Limit'],
                    'current_debt': 0,  # Set default value since it's not in the Excel
                }
            )
            print(f"Processed customer {row['Customer ID']}: {'Created' if created else 'Updated'}")
        except Exception as e:
            print(f"Error processing customer {row['Customer ID']}: {str(e)}")
    print("Customer data ingestion completed.")

@shared_task
def ingest_loan_data():
    print("Starting loan data ingestion...")
    df = pd.read_excel('loan_data.xlsx')
    print("Columns in loan_data.xlsx:", df.columns.tolist())  # Debug print
    print(f"Found {len(df)} loan records to process")
    for index, row in df.iterrows():
        try:
            customer = Customer.objects.get(customer_id=row['Customer ID'])  # type: ignore
            loan, created = Loan.objects.update_or_create(  # type: ignore
                loan_id=row['Loan ID'],
                defaults={
                    'customer': customer,
                    'loan_amount': row['Loan Amount'],
                    'tenure': row['Tenure'],
                    'interest_rate': row['Interest Rate'],
                    'monthly_repayment': row['Monthly payment'],  # Updated column name
                    'emis_paid_on_time': row['EMIs paid on Time'],  # Updated column name
                    'start_date': pd.to_datetime(row['Date of Approval']).date(),  # Updated column name
                    'end_date': pd.to_datetime(row['End Date']).date(),
                }
            )
            print(f"Processed loan {row['Loan ID']}: {'Created' if created else 'Updated'}")
        except Customer.DoesNotExist:
            print(f"Customer with ID {row['Customer ID']} does not exist. Skipping loan.")
        except Exception as e:
            print(f"Error processing loan {row['Loan ID']}: {str(e)}")
    print("Loan data ingestion completed.") 