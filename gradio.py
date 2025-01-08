import gradio as gr
import PyPDF2
import docx2txt
import re
import os
from typing import Optional
from datetime import datetime

# If these come from separate modules, import them:
from pinecone_handler import PineconeHandler
from time_handling import read_timestamp
from settings import DATE_FORMAT

# ------------------------------------------------------------------
# Original helper functions
# ------------------------------------------------------------------

def extract_text_from_pdf(pdf_file) -> str:
    """Extract text content from PDF file"""
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(docx_file) -> str:
    """Extract text content from DOCX file"""
    text = docx2txt.process(docx_file)
    return text

def extract_resume_text(uploaded_file) -> Optional[str]:
    """Extract text from uploaded resume file"""
    if uploaded_file is None:
        return None
    
    # Extract filename from the Gradio file object
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    try:
        if file_extension == 'pdf':
            # Gradio’s uploaded_file is a tempfile-like object
            return extract_text_from_pdf(uploaded_file)
        elif file_extension in ['docx', 'doc']:
            return extract_text_from_docx(uploaded_file.name)
        elif file_extension == 'txt':
            # Read entire text
            return uploaded_file.read().decode("utf-8", errors="replace")
        else:
            return f"ERROR: Unsupported file format: {file_extension}"
    except Exception as e:
        return f"ERROR: {str(e)}"

def clean_resume_text(text: str) -> str:
    """Clean and process resume text"""
    if not text:
        return ""
    # Remove special characters and extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def is_description_truncated(description: str) -> bool:
    """Check if the description appears to be truncated"""
    truncation_indicators = [
        lambda x: len(x) >= 995,  # Close to the 1000 char limit
        lambda x: x.rstrip().endswith(('...', '…')),
        lambda x: re.search(r'\w+$', x) and not re.search(r'[.!?]$', x),
    ]
    return any(indicator(description) for indicator in truncation_indicators)

def format_job_description(description: str, truncated: bool = False) -> str:
    """Format job description text with sections, line breaks, etc."""
    if not description:
        return ""
    
    sections = [
        "About us", "About you", "About the role", "About the position",
        "Requirements", "Qualifications", "Skills", "Responsibilities",
        "What you'll do", "What we offer", "Benefits", "Your profile",
        "Required skills", "What you need", "Who you are"
    ]
    
    formatted_text = description
    for section in sections:
        pattern = re.compile(f'({section}:?)', re.IGNORECASE)
        formatted_text = pattern.sub(r'\n\n\1', formatted_text)
    
    # Handle bullet points
    formatted_text = re.sub(r'[•-]\s*', '\n• ', formatted_text)
    
    # Add line breaks for sentences that look like list items
    formatted_text = re.sub(r'(?<=\w)\.(?=\s*[A-Z])', '.\n', formatted_text)
    
    # Reduce triple+ newlines to double
    formatted_text = re.sub(r'\n{3,}', '\n\n', formatted_text)
    
    if truncated:
        formatted_text = formatted_text.rstrip() + "..."
    
    return formatted_text.strip()

# ------------------------------------------------------------------
# Main Gradio function to handle user input and produce output
# ------------------------------------------------------------------

def search_jobs(resume_file, num_results, city_filter):
    """
    1) Extract + clean resume
    2) Query Pinecone
    3) Format the matching job ads
    4) Return results as text (or HTML)
    """
    # If no file was uploaded
    if resume_file is None:
        return "Please upload a resume first."

    resume_text = extract_resume_text(resume_file)
    if resume_text is None or resume_text.startswith("ERROR"):
        return f"Error processing file: {resume_text}"
    
    clean_text = clean_resume_text(resume_text)
    if not clean_text:
        return "No text extracted from resume or file is invalid."
    
    # Pinecone init
    try:
        handler = PineconeHandler()
    except Exception as e:
        return f"Error connecting to Pinecone: {str(e)}"
    
    # Attempt to read timestamp for “Database Status”
    database_info = ""
    try:
        last_update = read_timestamp()
        last_update_dt = datetime.strptime(last_update, DATE_FORMAT)
        database_info = f"**Database last update:** {last_update_dt.strftime('%B %d, %Y at %I:%M %p')} (Stockholm Time)\n\n"
    except Exception as e:
        database_info = f"Error reading timestamp: {str(e)}\n\n"
    
    # Query Pinecone
    try:
        results = handler.search_similar_ads(
            clean_text, top_k=num_results, city=city_filter.strip()
        )
    except Exception as e:
        return f"{database_info}Error searching jobs: {str(e)}"
    
    if not results:
        return f"{database_info}No matching jobs found. Try a different city or fewer results."
    
    # Build a nice text/HTML output
    output_lines = []
    output_lines.append(database_info)
    output_lines.append(f"**Found {len(results)} matching jobs:**\n")
    
    for i, match in enumerate(results, 1):
        metadata = match.metadata
        score = match.score
        
        # Basic info
        output_lines.append(f"### {i}. {metadata['headline']}")
        output_lines.append(f"Match Score (Cosine): {score:.2f}")
        
        if metadata.get('logo_url'):
            # Gradio can't directly “embed” an image in text, but we can supply a link:
            output_lines.append(f"Logo: {metadata['logo_url']}")
        
        output_lines.append(f"**Location:** {metadata['city']}")
        output_lines.append(f"**Occupation:** {metadata['occupation']}")
        output_lines.append(f"**Published:** {metadata['published']}")

        # Handle description
        description = metadata['description']
        is_trunc = is_description_truncated(description)
        snippet = description[:2000] if is_trunc else description
        
        formatted_desc = format_job_description(snippet, truncated=is_trunc)
        output_lines.append(formatted_desc)
        
        if is_trunc:
            output_lines.append(
                "> **Note**: The full description seems truncated. Please visit the original posting."
            )
            if metadata.get('webpage_url'):
                output_lines.append(f"[View Original Job Posting]({metadata['webpage_url']})")
        
        output_lines.append(f"**Contact:** {metadata['email']}")
        output_lines.append("---")

    return "\n".join(output_lines)


# ------------------------------------------------------------------
# Build the Gradio interface
# ------------------------------------------------------------------

# We’ll combine the user inputs into a single function call
with gr.Blocks() as demo:
    gr.Markdown("# AI-Powered Job Search (Gradio Version)")
    gr.Markdown(
        "Tired of searching for jobs? Upload your resume and discover perfectly matched opportunities!"
    )
    
    with gr.Row():
        resume_input = gr.File(label="Upload your resume (PDF, DOCX, DOC, or TXT)")
        num_results_slider = gr.Slider(
            minimum=1, maximum=20, value=5, step=1, label="Number of results"
        )
        city_input = gr.Textbox(
            label="Filter by city (optional)",
            placeholder="Enter a city to filter job results by location"
        )
    
    search_button = gr.Button("Search Jobs")
    output_box = gr.Markdown()

    # When the user clicks the button, call search_jobs()
    search_button.click(
        fn=search_jobs,
        inputs=[resume_input, num_results_slider, city_input],
        outputs=[output_box]
    )


if __name__ == "__main__":
    demo.launch()
