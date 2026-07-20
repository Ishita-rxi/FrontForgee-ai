# Base image ships Python and Node.js together, which is the whole point:
# the app needs to run a real `npm install` / `npm run build` no matter
# where it's deployed, and a plain python:slim image has no Node.js at all.
FROM nikolaik/python-nodejs:python3.11-nodejs20-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
