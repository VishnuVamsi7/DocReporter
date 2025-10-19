import os
import json
import sys
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer

class PDFIndexer:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        
        # Load the free, local embedding model
        print("🤖 Loading embedding model (this may take a moment)...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Embedding model loaded.")

        print(f"📂 Loading PDF: {pdf_path}")
        try:
            self.doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"❌ Failed to load PDF: {e}")
            raise

    def chunk_document(self, chunk_size=1000, overlap=100):
        """Chunks the document text with a character limit."""
        chunks = []
        full_text = ""
        for page in self.doc:
            full_text += page.get_text("text") + "\n"
        
        start = 0
        while start < len(full_text):
            end = start + chunk_size
            chunks.append(full_text[start:end])
            start += chunk_size - overlap # Move window with overlap
        
        print(f"✅ Created {len(chunks)} text chunks.")
        return chunks

    def create_vector_database(self, chunks):
        """Creates a list of vectors for each text chunk."""
        print(f"🧠 Generating {len(chunks)} vectors...")
        
        # This one command creates embeddings for all chunks
        vectors = self.model.encode(chunks, show_progress_bar=True)
        
        # Combine chunks with their vectors
        vector_database = []
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            vector_database.append({
                "chunk_id": i,
                "content": chunk,
                "vector": vector.tolist() # Convert numpy array to simple list
            })
        print("✅ Vector generation complete.")
        return vector_database

    def process(self, output_path):
        print("\n🚀 Starting PDF indexing pipeline...")
        chunks = self.chunk_document()
        vector_database = self.create_vector_database(chunks)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(vector_database, f, indent=2)
        print(f"\n✅ Vector database saved to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python process_pdf.py <input_pdf_path> <output_json_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2]
    processor = PDFIndexer(pdf_path)
    processor.process(output_path)