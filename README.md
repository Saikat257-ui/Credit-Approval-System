# Credit Approval System

A Django 4+ backend project for credit and loan approval, using Django Rest Framework, Celery, and PostgreSQL.

## Features
- Customer and loan management
- Credit score and eligibility calculation
- Background ingestion of Excel data
- RESTful API endpoints
- Dockerized for easy deployment

## Setup

1. Clone the repository and place `customer_data.xlsx` and `loan_data.xlsx` in the root directory.
2. Copy `.env` and fill in your Django secret key if needed.
3. Build and run with Docker Compose:

   - At first, run this command to start the server:
   ```bash
   docker-compose up --build
   ```
   - Point to be noted: In this project cloud based postgres(from Render) and redis(from Redis) have been used. So, before running this command, all you have to do is create a postgres database url from Render and redis url from Redis and paste it in the .env file as shown in the .env.example file. Keep the 'DJANGO_SECRET_KEY' and DEBUG as they are in the .env.example file.

   - Then run this command for appliying all migrations and creating necessary tables to the cloud PostgreSQL database:
   ```bash
   docker-compose exec web python manage.py migrate
   ```

4. The app will be available at `http://localhost:8000/`.

## API Endpoints
- `/register` (POST)
- `/check-eligibility` (POST)
- `/create-loan` (POST)
- `/view-loans/<customer_id>` (GET)

## API Endpoints Testing
- I have used "Rest Client" extension in VS Code to test the API endpoints in the IDE itself.
- Check out the app.rest file to see the API endpoints and the requests to be sent.
- But for the testing of the API endpoints with this app.rest file, you have to install the "Rest Client" extension in VS Code first.

## Database
Uses the provided Render PostgreSQL URL securely via environment variables.

## Background Tasks
- Celery is used for ingesting initial Excel data.
- For ingesting any data file, that particular file(s) should be in the root directory of the project.
- For example, if you want to ingest the data from the file "customer_data.xlsx", then the file should be in the root directory of the project.
- Now before data ingestion, make sure your containers are running.
- Then, open a Django shell inside the running web container and run this command:
```bash
docker-compose exec web python manage.py shell
```
- And then type the following in the Django shell for trigerring ingestion:

```bash
from core.tasks import ingest_customer_data, ingest_loan_data
ingest_customer_data.delay()
ingest_loan_data.delay()
```

--- 