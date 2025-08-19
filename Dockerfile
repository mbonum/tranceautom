FROM python:3.12-slim

ARG SECRET_KEY
ENV SECRET_KEY=${SECRET_KEY}
# ARG DATABASE_URL
# ENV DATABASE_URL=${DATABASE_URL}
ARG OKTA_CLIENT_ID
ENV OKTA_CLIENT_ID=${OKTA_CLIENT_ID}
ARG OKTA_CLIENT_SECRET
ENV OKTA_CLIENT_SECRET=${OKTA_CLIENT_SECRET}
ARG OKTA_ISSUER
ENV OKTA_ISSUER=${OKTA_ISSUER}

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

COPY entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

RUN python manage.py collectstatic --noinput

EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]
