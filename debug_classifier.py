import logging
logging.basicConfig(level=logging.WARNING)

from chatbot.core.intent_classifier import get_intent_classifier, INTENT_EXAMPLES
from common.models.schemas import Intent

c = get_intent_classifier()

# Debug: check 'analyze Reliance' neighbors
from sentence_transformers import SentenceTransformer
import faiss, numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

texts, labels = [], []
for intent, examples in INTENT_EXAMPLES.items():
    for ex in examples:
        texts.append(ex)
        labels.append(intent)

embeddings = model.encode(texts, normalize_embeddings=True).astype("float32")
index = faiss.IndexFlatIP(embeddings.shape[1])
index.add(embeddings)

query = "analyze Reliance"
qvec = model.encode([query], normalize_embeddings=True).astype("float32")
sims, idxs = index.search(qvec, 10)
print(f"Top-10 neighbors for '{query}':")
for sim, idx in zip(sims[0], idxs[0]):
    print(f"  [{sim:.3f}] {labels[idx].value:15s}  '{texts[idx]}'")
