# Deductly Backend

Python version: 3.12.0

## Setup

1. Clone the repository

2. Download and transfer environment variables

3. Run the setup script through `python3 bootstrap.py`

4. Setup temporary database by creating `main/db.sqlite3`

5. Apply migrations by running `python3 manage.py migrate`

6. Create an superuser account by running `python3 manage.py createsuperuser`. Take note of the credentials for Django Admin.

7. Start the server through `python3 manage.py runserver`
