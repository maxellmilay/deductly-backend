# Use an official Python runtime as a base image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Expose the port
EXPOSE 8080

# Start Gunicorn server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "main.wsgi:application"]
