FROM mcr.microsoft.com/playwright/python:v1.36.0-jammy
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
CMD gunicorn app:app --bind 0.0.0.0:$PORT
