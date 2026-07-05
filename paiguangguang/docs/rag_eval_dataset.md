# RAG Eval Dataset

This repository includes a small local evaluation dataset under `backend/evals/`.

Files:

- `backend/evals/rag_eval_dataset.json`
- `backend/evals/rag_eval_dataset.py`

## Dataset Shape

The JSON file contains:

- `version`: dataset schema version
- `corpus`: fixture documents and chunks
- `cases`: eval questions and expectations

Each corpus item includes:

- `doc_id`
- `title`
- `permission_scope`
- `page_number`
- `chunks[]`

Each chunk includes:

- `chunk_id`
- `chunk_index`
- `page_number`
- `text`
- `metadata`

Each eval case includes:

- `id`
- `question`
- `expected_documents`
- `expected_chunks`
- `expected_pages`
- `answer_notes`
- `citation_expectations`

## How To Extend

1. Add or update a corpus document in `backend/evals/rag_eval_dataset.json`.
2. Add a matching eval case that references the document and chunk IDs.
3. Keep the corpus small and deterministic so local tests remain fast.
4. Use `citation_expectations` to describe which document IDs, chunk IDs, and pages should appear in retrieval traces or citations.

## Script Loading

The dataset can be loaded from Python with:

```python
from evals import load_rag_eval_dataset

dataset = load_rag_eval_dataset()
```

This keeps the dataset usable from tests or future local eval scripts.
