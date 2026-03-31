FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer — only rebuilds if requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app
COPY app.py .

# Streamlit runs on port 8501
EXPOSE 8501

# Disable Streamlit's telemetry + browser auto-open (not useful in a container)
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_HEADLESS=true

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
