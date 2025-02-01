# Deductly Backend

Python version: 3.12.0

## Setup

1. Clone the repository

2. Download and transfer environment variables

3. Run the setup script through `python3 bootstrap.py`

4. Setup temporary database by creating `main/db.sqlite3`

5. Apply migrations by running `python3 manage.py migrate`

6. Create an superuser account by running `python3 manage.py createsuperuser`. Take note of the credentials for Django Admin.

## Starting the server

1. Make sure your mobile device is connected with the same network as your development pc

2. Run `ipconfig getifaddr en0` and take note of the ip address output

3. Start the server through `python3 manage.py runserver <ip_address>:8000` where you replace the ip address with what you got in step 2
