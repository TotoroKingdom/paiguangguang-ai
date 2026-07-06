npx chromadb-admin --port 3434 --chromadb-url http://your-chromadb:8000

chroma run --host localhost --port 8002 --path ./chroma

python chroma_view.py

uv run python -m uvicorn app.main:app --reload --env-file dev.env         