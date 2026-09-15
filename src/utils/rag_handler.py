import faiss, json
import numpy as np
from sentence_transformers import SentenceTransformer

from .ia_handler import IA

class RAG:
    def __init__(self):
        #book = "/home/aki/Proj/gram-size/data/faiss/CINESIOLOGIA E BIOMECÂNICA.index"
        self.index = faiss.read_index("/home/aki/Proj/gram-size/data/faiss/livros.index")
        self.metadata = json.load(open("/home/aki/Proj/gram-size/data/faiss/livros.metadata.json", encoding="utf-8"))
        self.model = SentenceTransformer("intfloat/multilingual-e5-small")
        self.llm = IA()

    def generate_response(self, query):
        query_vec = self.model.encode([f"query: {query}"])
        faiss.normalize_L2(query_vec)

        distances, ids = self.index.search(query_vec.astype("float32"), k=10)
        chunks = []
        for dist, idx in zip(distances[0], ids[0]):
            print([f"{dist}, {self.metadata[idx]["page_number"]}, {self.metadata[idx]["text"]}"])
            chunks.append("Livro: " + str(self.metadata[idx]["book_name"]) +
                           "Página: " + str(self.metadata[idx]["page_number"]) + 
                           "\n" + str(self.metadata[idx]["text"]))

        print(" ".join(chunks))
        response = self.llm.response(query, str(" ".join(chunks)))
            
        return response