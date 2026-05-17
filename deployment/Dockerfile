FROM python:3.11-slim
WORKDIR /app

# Build context is the project root (see .github/workflows/deploy.yml).
COPY deployment/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY deployment/app.py .
COPY data/processed/ ./data/processed/

ENV VDSS_DATA_DIR=/app/data/processed

EXPOSE 8501

# The baseUrlPath flag is CRITICAL for reverse proxying to a subpath!
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.baseUrlPath=/streamlit"]