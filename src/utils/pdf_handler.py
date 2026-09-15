import argparse
import json
import math
import os
import sys

from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import pdfplumber

MAX_TOKENS_PER_CHUNK = 512

# Number of pages sampled to decide whether a PDF is "scanned".
SCAN_SAMPLE_PAGES = 5
# Minimum average characters/page in the sample to consider that the PDF
# actually has a text layer (below that = probably scanned).
SCAN_MIN_AVG_CHARS = 30


def is_scanned_pdf(pdf_path: str, sample_pages: int = SCAN_SAMPLE_PAGES,
                    min_avg_chars: int = SCAN_MIN_AVG_CHARS) -> bool:
    """
    Quick heuristic: opens the PDF, extracts text from up to `sample_pages`
    pages spread across the document (beginning, middle, end), and measures
    the average number of characters extracted per page.

    Scanned PDFs (pure image, no OCR) tend to return empty or nearly empty
    text from `extract_text()`. PDFs with a real text layer usually return
    hundreds of characters per page.

    Returns True if the PDF appears to be scanned (no extractable text).
    """
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        if total_pages == 0:
            return True

        n = min(sample_pages, total_pages)
        if n == 1:
            indices = [0]
        else:
            # spread the samples from the beginning to the end of the book
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
    """Splits the text into `num_parts` roughly equal pieces (by characters)."""
    chunk_size = math.ceil(len(text) / num_parts)
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def find_pdfs(root_dir: str) -> list[str]:
    """Returns, in order, the paths of all .pdf files found recursively."""
    pdf_paths = []
    for dirpath, _dirnames, filenames in os.walk(root_dir):
        for filename in sorted(filenames):
            if filename.lower().endswith(".pdf"):
                pdf_paths.append(os.path.join(dirpath, filename))
    return sorted(pdf_paths)


def list_pages(pdf_path: str) -> int:
    """Returns the total number of pages in the PDF."""
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)


def extract_page_text(pdf_path: str, page_number: int) -> str:
    """
    Extracts the raw text from a page (1-based).
    Raises ValueError if the page number is invalid.
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
    Builds a FAISS index (cosine similarity via normalized inner product)
    from `embeddings` and saves it to `index_path`. Since FAISS only stores
    vectors, `metadata` (one dict per vector, same order) is saved separately
    as JSON to map a search result back to the source book/page/text.
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
    """Processes a single PDF and returns (embeddings, metadata) for its chunks."""
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
        description="Builds a single FAISS index from all PDFs in a folder (recursive)."
    )
    parser.add_argument("folder", help="Root folder where to look for PDFs (recursively).")
    parser.add_argument(
        "--out", default="livros",
        help="Output prefix (generates <out>.index and <out>.metadata.json). Default: 'livros'."
    )
    parser.add_argument(
        "--model", default="intfloat/multilingual-e5-small",
        help="Name of the SentenceTransformer model to use."
    )
    parser.add_argument(
        "--scan-sample", type=int, default=SCAN_SAMPLE_PAGES,
        help=f"Number of pages sampled to detect a scanned book (default: {SCAN_SAMPLE_PAGES})."
    )
    parser.add_argument(
        "--scan-min-chars", type=int, default=SCAN_MIN_AVG_CHARS,
        help=f"Minimum average characters/page to consider 'not scanned' (default: {SCAN_MIN_AVG_CHARS})."
    )
    parser.add_argument(
        "--include-scanned", action="store_true",
        help="Do not filter out scanned books (tries to process them anyway; will probably generate empty/poor chunks)."
    )
    args = parser.parse_args()

    if not os.path.isdir(args.folder):
        print(f"Error: '{args.folder}' is not a valid folder.")
        sys.exit(1)

    all_pdf_paths = find_pdfs(args.folder)
    if not all_pdf_paths:
        print(f"No PDFs found in '{args.folder}'.")
        sys.exit(0)

    print(f"Found {len(all_pdf_paths)} PDF(s). Checking which ones have a text layer...")

    pdf_paths = []
    scanned_paths = []
    for p in all_pdf_paths:
        try:
            scanned = (
                False if args.include_scanned
                else is_scanned_pdf(p, args.scan_sample, args.scan_min_chars)
            )
        except Exception as exc:
            print(f"  Warning: could not open '{p}' for checking ({exc}). Treating as scanned/unreadable.")
            scanned = True

        if scanned:
            scanned_paths.append(p)
            print(f"  [SCANNED?] {p}")
        else:
            pdf_paths.append(p)
            print(f"  [OK]       {p}")

    if scanned_paths:
        scanned_list_path = f"{args.out}.scanned_books.txt"
        with open(scanned_list_path, "w", encoding="utf-8") as f:
            f.write("\n".join(scanned_paths) + "\n")
        print(
            f"\n{len(scanned_paths)} book(s) appear to be scanned (no extractable text) "
            f"and were left out of the index. List saved to: {scanned_list_path}\n"
            f"To include them anyway, run with --include-scanned "
            f"(but they will probably generate empty/poor chunks — consider running OCR on them first)."
        )

    if not pdf_paths:
        print("\nAll PDFs found appear to be scanned. Nothing to index.")
        sys.exit(0)

    model = SentenceTransformer(args.model)

    all_embeddings = []
    all_metadata = []

    for book_id, pdf_path in enumerate(pdf_paths):
        print(f"\n>>> Processing book {book_id + 1}/{len(pdf_paths)}: {pdf_path}")
        try:
            embeddings, metadata = process_pdf(model, pdf_path, book_id)
        except Exception as exc:
            print(f"  Error processing '{pdf_path}': {exc}. Skipping this file.")
            continue

        if not embeddings:
            print(f"  No text extracted from '{pdf_path}'.")
            continue

        all_embeddings.extend(embeddings)
        all_metadata.extend(metadata)

    if not all_embeddings:
        print("No text extracted from any PDF, nothing to save.")
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
    print(f"\nProcessed {len(all_metadata)} chunk(s) from {num_books} book(s) out of {len(pdf_paths)} PDF(s) found.")


if __name__ == "__main__":
    main()