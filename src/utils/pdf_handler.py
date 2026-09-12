"""
Varre uma pasta RECURSIVAMENTE em busca de arquivos PDF, extrai o texto de
cada página, gera embeddings com SentenceTransformer (dividindo páginas
longas em quantas partes forem necessárias para ficar abaixo de
MAX_TOKENS_PER_CHUNK tokens) e salva TUDO em um único índice FAISS,
incluindo o caminho/nome do livro de origem em cada chunk.

Requisitos:
    pip install pdfplumber sentence-transformers faiss-cpu --break-system-packages

Uso:
    python extract_folder_pdfs.py /caminho/para/pasta_com_livros
    (gera livros.index + livros.metadata.json na pasta atual, por padrão)

    python extract_folder_pdfs.py /caminho/para/pasta_com_livros --out biblioteca
    (gera biblioteca.index + biblioteca.metadata.json)
"""
from sentence_transformers import SentenceTransformer

import argparse
import json
import math
import os
import sys
import numpy as np
import faiss
import pdfplumber

MAX_TOKENS_PER_CHUNK = 512

# Quantidade de páginas amostradas para decidir se um PDF é "escaneado".
SCAN_SAMPLE_PAGES = 5
# Média mínima de caracteres/página na amostra para considerar que o PDF
# tem camada de texto de verdade (abaixo disso = provavelmente escaneado).
SCAN_MIN_AVG_CHARS = 30


def is_scanned_pdf(pdf_path: str, sample_pages: int = SCAN_SAMPLE_PAGES,
                    min_avg_chars: int = SCAN_MIN_AVG_CHARS) -> bool:
    """
    Heurística rápida: abre o PDF, extrai texto de até `sample_pages`
    páginas espalhadas pelo documento (início, meio, fim) e mede a média
    de caracteres extraídos por página.

    PDFs escaneados (imagem pura, sem OCR) tendem a retornar texto vazio
    ou quase vazio em `extract_text()`. PDFs com camada de texto real
    normalmente retornam centenas de caracteres por página.

    Retorna True se o PDF parece ser escaneado (sem texto extraível).
    """
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        if total_pages == 0:
            return True

        n = min(sample_pages, total_pages)
        if n == 1:
            indices = [0]
        else:
            # espalha as amostras do início ao fim do livro
            indices = sorted(set(
                round(i * (total_pages - 1) / (n - 1)) for i in range(n)
            ))

        char_counts = []
        for idx in indices:
            text = pdf.pages[idx].extract_text(x_tolerance=2) or ""
            char_counts.append(len(text.strip()))

    avg_chars = sum(char_counts) / len(char_counts)
    return avg_chars < min_avg_chars


def split_text_into_parts(text: str, num_parts: int) -> list[str]:
    """Divide o texto em `num_parts` pedaços aproximadamente iguais (por caracteres)."""
    chunk_size = math.ceil(len(text) / num_parts)
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def find_pdfs(root_dir: str) -> list[str]:
    """Retorna, em ordem, os caminhos de todos os .pdf encontrados recursivamente."""
    pdf_paths = []
    for dirpath, _dirnames, filenames in os.walk(root_dir):
        for filename in sorted(filenames):
            if filename.lower().endswith(".pdf"):
                pdf_paths.append(os.path.join(dirpath, filename))
    return sorted(pdf_paths)


def list_pages(pdf_path: str) -> int:
    """Retorna o número total de páginas do PDF."""
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)


def extract_page_text(pdf_path: str, page_number: int) -> str:
    """
    Extrai o texto bruto de uma página (1-based).
    Lança ValueError se o número da página for inválido.
    """
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        if page_number < 1 or page_number > total_pages:
            raise ValueError(
                f"Page {page_number} is invalid. The PDF has {total_pages} pages."
            )
        page = pdf.pages[page_number - 1]
        text = page.extract_text(x_tolerance=2) or ""
        return text


def save_faiss_index(embeddings: np.ndarray, metadata: list[dict], index_path: str, metadata_path: str) -> None:
    """
    Constrói um índice FAISS (similaridade de cosseno via inner product
    normalizado) a partir de `embeddings` e salva em `index_path`. Como o
    FAISS só guarda vetores, `metadata` (um dict por vetor, mesma ordem)
    é salvo separadamente em JSON para mapear um resultado de busca de
    volta ao livro/página/texto de origem.
    """
    embeddings = np.asarray(embeddings, dtype="float32")
    faiss.normalize_L2(embeddings)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index = faiss.IndexIDMap(index)

    ids = np.arange(len(metadata), dtype="int64")
    index.add_with_ids(embeddings, ids)

    faiss.write_index(index, index_path)
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\nFAISS index saved to: {index_path}")
    print(f"Metadata saved to: {metadata_path}")


def process_pdf(model: SentenceTransformer, pdf_path: str, book_id: int) -> tuple[list[np.ndarray], list[dict]]:
    """Processa um único PDF e retorna (embeddings, metadata) de seus chunks."""
    total_pages = list_pages(pdf_path)
    book_name = os.path.splitext(os.path.basename(pdf_path))[0]

    passage_embeddings = []
    passage_metadata = []

    for page_number in range(1, total_pages + 1):
        page_text = extract_page_text(pdf_path, page_number)

        if not page_text.strip():
            print(f"  [Page {page_number}] Empty, skipping.")
            continue

        print(f"  === Page {page_number}/{total_pages} ===")

        tokenized = model.tokenizer(page_text, truncation=False)
        token_count = len(tokenized["input_ids"])

        page_principal_text = page_text.splitlines()[0]

        if token_count > MAX_TOKENS_PER_CHUNK:
            num_parts = math.ceil(token_count / MAX_TOKENS_PER_CHUNK)
            print(f"  Page {page_number} split into {num_parts} part(s).")
            text_parts = split_text_into_parts(page_text, num_parts)
        else:
            text_parts = [page_text]

        sentences = []
        for part in text_parts:
            sentences.append(f"query: {page_principal_text}")
            sentences.append(f"passage: {part}")

        embeddings = model.encode(sentences)

        for i, part in enumerate(text_parts):
            passage_vector = embeddings[i * 2 + 1]
            passage_embeddings.append(passage_vector)
            passage_metadata.append({
                "book_id": book_id,
                "book_name": book_name,
                "source_path": pdf_path,
                "page_number": page_number,
                "chunk_index": i,
                "text": part,
            })

    return passage_embeddings, passage_metadata


def main():
    parser = argparse.ArgumentParser(
        description="Gera um índice FAISS único a partir de todos os PDFs de uma pasta (recursivo)."
    )
    parser.add_argument("folder", help="Pasta raiz onde procurar os PDFs (recursivamente).")
    parser.add_argument(
        "--out", default="livros",
        help="Prefixo de saída (gera <out>.index e <out>.metadata.json). Padrão: 'livros'."
    )
    parser.add_argument(
        "--model", default="intfloat/multilingual-e5-small",
        help="Nome do modelo SentenceTransformer a usar."
    )
    parser.add_argument(
        "--scan-sample", type=int, default=SCAN_SAMPLE_PAGES,
        help=f"Nº de páginas amostradas para detectar livro escaneado (padrão: {SCAN_SAMPLE_PAGES})."
    )
    parser.add_argument(
        "--scan-min-chars", type=int, default=SCAN_MIN_AVG_CHARS,
        help=f"Média mínima de caracteres/página para considerar 'não escaneado' (padrão: {SCAN_MIN_AVG_CHARS})."
    )
    parser.add_argument(
        "--include-scanned", action="store_true",
        help="Não filtra livros escaneados (tenta processar mesmo assim; provavelmente gera chunks vazios/ruins)."
    )
    args = parser.parse_args()

    if not os.path.isdir(args.folder):
        print(f"Erro: '{args.folder}' não é uma pasta válida.")
        sys.exit(1)

    all_pdf_paths = find_pdfs(args.folder)
    if not all_pdf_paths:
        print(f"Nenhum PDF encontrado em '{args.folder}'.")
        sys.exit(0)

    print(f"Encontrados {len(all_pdf_paths)} PDF(s). Verificando quais têm camada de texto...")

    pdf_paths = []
    scanned_paths = []
    for p in all_pdf_paths:
        try:
            scanned = (
                False if args.include_scanned
                else is_scanned_pdf(p, args.scan_sample, args.scan_min_chars)
            )
        except Exception as exc:
            print(f"  Aviso: não consegui abrir '{p}' para checagem ({exc}). Tratando como escaneado/ilegível.")
            scanned = True

        if scanned:
            scanned_paths.append(p)
            print(f"  [ESCANEADO?] {p}")
        else:
            pdf_paths.append(p)
            print(f"  [OK]         {p}")

    if scanned_paths:
        scanned_list_path = f"{args.out}.scanned_books.txt"
        with open(scanned_list_path, "w", encoding="utf-8") as f:
            f.write("\n".join(scanned_paths) + "\n")
        print(
            f"\n{len(scanned_paths)} livro(s) parecem escaneados (sem texto extraível) "
            f"e foram deixados de fora do índice. Lista salva em: {scanned_list_path}\n"
            f"Para incluí-los mesmo assim, rode com --include-scanned "
            f"(mas provavelmente vão gerar chunks vazios/ruins — considere rodar OCR neles primeiro)."
        )

    if not pdf_paths:
        print("\nTodos os PDFs encontrados parecem escaneados. Nada para indexar.")
        sys.exit(0)

    model = SentenceTransformer(args.model)

    all_embeddings = []
    all_metadata = []

    for book_id, pdf_path in enumerate(pdf_paths):
        print(f"\n>>> Processando livro {book_id + 1}/{len(pdf_paths)}: {pdf_path}")
        try:
            embeddings, metadata = process_pdf(model, pdf_path, book_id)
        except Exception as exc:
            print(f"  Erro ao processar '{pdf_path}': {exc}. Pulando este arquivo.")
            continue

        if not embeddings:
            print(f"  Nenhum texto extraído de '{pdf_path}'.")
            continue

        all_embeddings.extend(embeddings)
        all_metadata.extend(metadata)

    if not all_embeddings:
        print("Nenhum texto extraído de nenhum PDF, nada para salvar.")
        sys.exit(0)

    index_path = f"{args.out}.index"
    metadata_path = f"{args.out}.metadata.json"

    save_faiss_index(
        np.vstack(all_embeddings),
        all_metadata,
        index_path,
        metadata_path,
    )

    num_books = len({m["book_id"] for m in all_metadata})
    print(f"\nProcessados {len(all_metadata)} chunk(s) de {num_books} livro(s) de um total de {len(pdf_paths)} PDF(s) encontrados.")


if __name__ == "__main__":
    main()