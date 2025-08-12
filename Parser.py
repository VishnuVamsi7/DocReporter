import os
import json
import fitz  # PyMuPDF
import tabula
import warnings
from groq import Groq

warnings.filterwarnings("ignore")
os.environ["GROQ_API_KEY"] = "YOUR_API_KEY_HERE"


class PDFSectionProcessor:
    def __init__(self, pdf_path, model='deepseek-r1-distill-llama-70b', token_limit=3000):
        self.pdf_path = pdf_path
        self.model = model
        self.token_limit = token_limit

        print(f"📂 Loading PDF: {pdf_path}")
        try:
            self.doc = fitz.open(pdf_path)
            print(f"✅ PDF loaded successfully. Total pages: {self.doc.page_count}")
        except Exception as e:
            print(f"❌ Failed to load PDF: {e}")
            raise

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("⚠️ Groq API key not found in environment. Check your setup.")
        self.client = Groq(api_key=api_key)

    def estimate_tokens(self, text):
        """Rough token estimate: ~4 chars/token."""
        return len(text) / 4

    def extract_text(self, start=0, end=None):
        end = end if end is not None else self.doc.page_count
        return "\n".join([self.doc[i].get_text() for i in range(start, end)]).strip()

    def chunk_pages_by_tokens(self):
        """Split PDF into chunks based on token count."""
        chunks = []
        current_chunk_text = ""
        current_chunk_pages = []

        for page_num in range(self.doc.page_count):
            page_text = self.doc[page_num].get_text()
            est_tokens = self.estimate_tokens(current_chunk_text + page_text)

            if est_tokens > self.token_limit and current_chunk_pages:
                # Save current chunk
                chunks.append({
                    "pages": current_chunk_pages,
                    "text": current_chunk_text.strip()
                })
                current_chunk_text = page_text
                current_chunk_pages = [page_num + 1]
            else:
                current_chunk_text += "\n" + page_text
                current_chunk_pages.append(page_num + 1)

        # Save last chunk
        if current_chunk_pages:
            chunks.append({
                "pages": current_chunk_pages,
                "text": current_chunk_text.strip()
            })

        print(f"✅ Created {len(chunks)} token-aware chunks.")
        return chunks

    def extract_tables_for_pages(self, start_page, end_page, min_rows=3):
        """Extract tables for specific page range and return as list of dicts."""
        tables_data = []
        try:
            tables = tabula.read_pdf(
                self.pdf_path,
                pages=f"{start_page}-{end_page}",
                multiple_tables=True,
                silent=True
            )
            for idx, table in enumerate(tables, 1):
                if len(table) >= min_rows:
                    tables_data.append({
                        "page": None,  # Tabula doesn't give exact page per table
                        "table": table.astype(str).values.tolist()
                    })
        except Exception as e:
            print(f"⚠️ Table extraction failed for pages {start_page}-{end_page}: {e}")
        return tables_data

    def query_llm(self, content):
        """Ask DeepSeek R1 to produce heading & summary."""
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"You are given a section of a document.\n"
                            f"Return a JSON object with:\n"
                            f"1. custom_heading: A short, descriptive title for the content.\n"
                            f"2. summary: 5-6 lines summarizing the main ideas.\n"
                            f"Do not include the original content or tables in the summary.\n\n"
                            f"Content:\n{content[:3000]}"
                        )
                    }
                ],
                model=self.model,
                stream=False,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ LLM query failed: {e}")
            return ""

    def process(self, output_path='output.json'):
        print("\n🚀 Starting PDF processing pipeline...")
        chunks = self.chunk_pages_by_tokens()
        results = []

        for chunk in chunks:
            pages = chunk["pages"]
            text = chunk["text"]

            # Get heading + summary from LLM
            llm_output = self.query_llm(text)
            try:
                llm_data = json.loads(llm_output)
            except json.JSONDecodeError:
                llm_data = {
                    "custom_heading": "",
                    "summary": llm_output
                }

            # Extract tables for these pages
            tables = self.extract_tables_for_pages(pages[0], pages[-1])

            results.append({
                "custom_heading": llm_data.get("custom_heading", ""),
                "summary": llm_data.get("summary", ""),
                "pages": pages,
                "content": text,
                "tables": tables
            })

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Results saved to: {output_path}")


if __name__ == "__main__":
    pdf_path = 'YOUR_FILE'
    processor = PDFSectionProcessor(pdf_path, model='deepseek-r1-distill-llama-70b', token_limit=3000)
    processor.process('structured_output.json')
