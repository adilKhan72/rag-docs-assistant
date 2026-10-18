FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Bake the embedding model into the image so containers start offline and fast.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"
COPY . .
EXPOSE 8080
CMD ["uvicorn", "ragdocs.api:app", "--host", "0.0.0.0", "--port", "8080"]
