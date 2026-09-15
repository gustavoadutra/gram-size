import faiss, json
import logging
from pathlib import Path

from sentence_transformers import SentenceTransformer

from .ia_handler import IA

logger = logging.getLogger(__name__)

class RAG:
    def __init__(self):
        base_dir = Path(__file__).resolve().parents[2] 
        faiss_dir = base_dir / "data" / "faiss"

        self.index = faiss.read_index(str(faiss_dir / "livros.index"))
        with open(faiss_dir / "livros.metadata.json", encoding="utf-8") as f:
            self.metadata = json.load(f)

        self.model = SentenceTransformer("intfloat/multilingual-e5-small")
        self.llm = IA()

    def generate_response(self, query):
        query_vec = self.model.encode([f"query: {query}"])
        faiss.normalize_L2(query_vec)

        distances, ids = self.index.search(query_vec.astype("float32"), k=5)
        chunks = []
        for dist, idx in zip(distances[0], ids[0]):
            item = self.metadata[idx]
            logger.debug(
                "Returned chunk: book=%s page=%s",
                item["book_name"],
                item["page_number"],
            )
            chunks.append(
                "Livro: " + str(item["book_name"]) +
                "Página: " + str(item["page_number"]) +
                "\n" + str(item["text"])
            )
        response = self.llm.response(query, str(" ".join(chunks)))
            
        return response