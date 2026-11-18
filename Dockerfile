FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["sh", "-c", "python -m src.generate_messy_excels && python -m src.cleaner_pipeline && streamlit run app/dashboard.py --server.address=0.0.0.0 --server.port=8501"]
