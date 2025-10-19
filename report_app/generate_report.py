import json
import sys
import os
from fpdf import FPDF

# --- Matplotlib Setup ---
# We MUST use a non-interactive backend 'Agg' so it can run
# in a Docker container without a display.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
# ------------------------

class PDFReportGenerator:
    def __init__(self, json_path, output_pdf_path):
        self.output_pdf_path = output_pdf_path
        print(f"📂 Loading analyst report from {json_path}...")
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except Exception as e:
            print(f"❌ Failed to load analyst report: {e}")
            sys.exit(1)

    def execute_plot_code(self, code, image_path):
        """Safely execute string code to generate and save a plot."""
        if not code or code == "No data available":
            print("⚠️ No plot code found to execute.")
            return False
        
        print(f"🎨 Generating plot at {image_path}...")
        try:
            # We execute the code, which uses 'plt' to create a plot
            exec(code) 
            plt.savefig(image_path)
            plt.close() # Close the plot to free up memory
            return True
        except Exception as e:
            print(f"❌ Plot generation failed: {e}")
            return False

    def generate_report(self):
        print("✍️ Starting final PDF report generation...")
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        # Main Title
        pdf.set_font("Arial", 'B', 18)
        pdf.cell(0, 10, self.data.get("report_title", "AI-Generated Analysis"), ln=True, align='C')
        pdf.ln(10)

        # Key Insights Section
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Key Insights", ln=True)
        # The 'key_insights' from our LLM is a single string, so we'll just print it.
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 6, self.data.get("key_insights", "No insights generated."))
        pdf.ln(5)

        # Revenue Suggestions Section
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Revenue Growth Suggestions", ln=True)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 6, self.data.get("revenue_suggestions", "No suggestions generated."))
        pdf.ln(5)

        # Visualizations Section
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Visualizations", ln=True)
        
        viz_data = self.data.get("visualization", {})
        plot_path = "/app/documents/output/temp_plot.png" # Use a path inside the container
        
        if self.execute_plot_code(viz_data.get("plot_code"), plot_path):
            pdf.image(plot_path, w=160) # Embed the image
            os.remove(plot_path) # Clean up the temp image file
            pdf.set_font("Arial", 'I', 10)
            pdf.multi_cell(0, 6, f"Insight: {viz_data.get('insight', 'Plot from data.')}")
        else:
            pdf.set_font("Arial", 'I', 10)
            pdf.multi_cell(0, 6, "No visualization was generated for this report.")
        
        pdf.output(self.output_pdf_path)
        print(f"✅ Final report saved to: {self.output_pdf_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_report.py <input_json_path> <output_pdf_path>")
        sys.exit(1)
    
    # We pass the container-relative paths
    input_json = sys.argv[1]
    output_pdf = sys.argv[2]
    
    PDFReportGenerator(input_json, output_pdf).generate_report()