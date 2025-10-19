import os
import json
import sys
import numpy as np
import faiss
from groq import Groq
from sentence_transformers import SentenceTransformer

class AIAnalystRAG:
    def __init__(self, db_path, model='llama-3.3-70b-versatile'):
        self.db_path = db_path
        self.llm_model = model
        
        # 1. Load Groq client
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set!")
        self.groq_client = Groq(api_key=api_key)
        
        # 2. Load the *same* embedding model used for indexing
        print("🤖 Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Embedding model loaded.")
        
        # 3. Load our vector database from the JSON file
        print(f"📂 Loading vector database from {db_path}...")
        with open(db_path, 'r', encoding='utf-8') as f:
            self.database = json.load(f)
        
        # 4. Build the FAISS index in memory
        self.build_faiss_index()

    def build_faiss_index(self):
        """Builds an in-memory FAISS index from the loaded vectors."""
        print("🧠 Building FAISS index...")
        vectors = [item['vector'] for item in self.database]
        self.vectors = np.array(vectors).astype('float32')
        
        # Get the dimension of the vectors
        d = self.vectors.shape[1]
        
        # Using IndexFlatL2 for simple, accurate L2 distance search
        self.index = faiss.IndexFlatL2(d)
        self.index.add(self.vectors)
        print(f"✅ FAISS index built with {self.index.ntotal} vectors.")

    def retrieve(self, query_text, k=5):
        """Retrieves the top-k most relevant text chunks for a query."""
        print(f"🔍 Searching for context: '{query_text}'")
        # 1. Embed the query
        query_vector = self.embedding_model.encode([query_text])
        
        # 2. Search the FAISS index
        # D = distances, I = indices (of the chunks in our list)
        D, I = self.index.search(query_vector.astype('float32'), k)
        
        # 3. Retrieve the actual text content
        retrieved_chunks = [self.database[i]['content'] for i in I[0]]
        return "\n---\n".join(retrieved_chunks)

    def generate(self, prompt, context):
        """Sends the prompt and retrieved context to the LLM."""
        full_prompt = f"Context:\n{context}\n\nTask:\n{prompt}"
        
        try:
            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": full_prompt}],
                model=self.llm_model,
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ LLM generation failed: {e}")
            return f"Error: {e}"

    def run_analysis(self, output_path):
        """Runs the full RAG-based analysis to build the report."""
        print("🚀 Starting RAG analysis...")
        final_report = {}
        
        # Task 1: Identify Key Themes
        context_themes = self.retrieve("What are the main themes, topics, goals, and corporate strategies discussed?")
        final_report['key_insights'] = self.generate(
            "Identify 3-5 key themes from the context. For each theme, provide a concise one-sentence summary.",
            context_themes
        )
        
        # Task 2: Suggest Revenue Strategies
        context_revenue = self.retrieve("What are the financial results, sales performance, revenue challenges, and growth opportunities?")
        final_report['revenue_suggestions'] = self.generate(
            "Based on the context, suggest 2-3 actionable revenue growth strategies.",
            context_revenue
        )
        
        # Task 3: Generate Graph Code
        context_graph = self.retrieve("Find all quantifiable data, financials, numbers, or statistics over time (e.g., by year, quarter).")
        raw_code = self.generate(
            "Generate Python Matplotlib code for a simple bar or line chart based *only* on the data in the context. "
            "Enclose the code in triple backticks (```python...```). If no data is found, say 'No data available'.",
            context_graph
        )
        
        # Clean up the code block
        if "```python" in raw_code:
            raw_code = raw_code.split("```python")[1].split("```")[0].strip()
        
        final_report['visualization'] = {
            "title": "Data Visualization",
            "plot_code": raw_code,
            "insight": "Plot generated from retrieved data."
        }
        
        # Save the final JSON report
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2)
        print(f"✅ AI analysis report saved to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python analyst.py <input_db_path> <output_report_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    report_path = sys.argv[2]
    
    analyst = AIAnalystRAG(db_path)
    analyst.run_analysis(report_path)