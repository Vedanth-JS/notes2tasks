FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt pyproject.toml /app/
RUN pip install -r requirements.txt fastapi uvicorn

# Copy code
COPY . /app/

# Expose Streamlit and FastAPI ports
EXPOSE 8501 8000

# Run Streamlit by default
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
