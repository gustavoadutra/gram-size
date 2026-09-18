# Brian - Fisio

RAG system designed to retrieve information from physiotherapy books through a Telegram bot to help physioterapeuts. It creates embeddings using a local model running on an MX130 GPU, with the multilingual-e5-small model loaded in VRAM.

The project uses a retrieval-augmented generation pipeline: PDF files are processed, text is split into chunks with controlled size limits, embeddings are generated, stored in a FAISS index, and then used to answer user questions based on the indexed sources.

The source documents are in Portuguese, and the retrieval process is optimized for that language.

The main PDF processing logic is implemented in pdf_handler.py. This module is responsible for discovering the books, extracting text, checking for scanned documents, splitting large pages into smaller chunks, generating embeddings, and saving the FAISS index together with the corresponding metadata.

The retrieved context is then sent to the LLM, which answers the question using only the relevant information extracted from the indexed books and cites the source material when appropriate.

Books used:

- CINESIOLOGIA E BIOMECÂNICA
- Diagnóstico cinetico-funcional e imaginologia
- Kapanji - volume 1
- Kapanji - volume 2
- Kapanji - volume 3
- 360940236-ABC-da-Ventilac-a-o-Meca-nica-Volume-pdf
- Anatomia Orientada para a Clínica - 7a Edição - Moore
- Anatomia na Prática_ Sistema Musculoesquelético. 1º edição. POZZOBON, Adriane. MATEUS PEREIRA, Gabriela Augusta. JUNG, Leonardo.
- Anatomia para Colorir - Netter
- Histologia Básica - 12ª Edição - Junqueira & Carneiro
- Netter - Atlas de Anatomia Humana - 6° edição
- Sobotta - Cabeça, pescoço e extremidades superiores - volume 1
- Política Nacional de Práticas Integrativas e Complementares no SUS
- Questões - Residências em Fisioterapia
- Fisiologia Médica - Guyton
- Exame neurológico - Bases anatomofuncionais - Gusmão
- Agentes físicos terapêuticos - Dr. Jorge Enrique Martin Cordero
- Bandagem terapêutica - Neuson Morini - 2° edição
- Eletroterapia em estética corporal - Marizilda Toledo
- Eletroterapia prática baseada em evidências - Sheila Kitchen
- ABC da Ventilação Mecânica- volume 2
- Bases da fisioterapia respiratória - terapia intensiva e reabilitação - Machado - 1 edição
- Fisiologia Respiratória - West
- Princípios e práticas de ventilação mecânica em pediatria e neonatologia
- Urofisioterapia

# I DO NOT HAVE THE RIGHTS FOR THESE BOOKS