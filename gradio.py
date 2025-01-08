import gradio as gr
import PyPDF2
import docx2txt
import re
from typing import Optional
from datetime import datetime

# --- Import your custom modules
from pinecone_handler import PineconeHandler
from time_handling import read_timestamp
from settings import DATE_FORMAT

# ------------------------------------------------------------------
# Global or session-level store for job data
# ------------------------------------------------------------------
MAX_RESULTS = 10  # Up to 10 job ads displayed
JOBS_CACHE = [None] * MAX_RESULTS  # Each element will hold (ad_id, ad_metadata, full_resume_text)


# ------------------------------------------------------------------
# Helper functions (same as your original ones) 
# ------------------------------------------------------------------
def extract_text_from_pdf(pdf_file) -> str:
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(docx_file) -> str:
    text = docx2txt.process(docx_file)
    return text

def extract_resume_text(uploaded_file) -> Optional[str]:
    if uploaded_file is None:
        return None
    
    file_extension = uploaded_file.name.split('.')[-1].lower()
    try:
        if file_extension == 'pdf':
            return extract_text_from_pdf(uploaded_file)
        elif file_extension in ['docx', 'doc']:
            return extract_text_from_docx(uploaded_file.name)
        elif file_extension == 'txt':
            return uploaded_file.read().decode("utf-8", errors="replace")
        else:
            return f"ERROR: Unsupported file format: {file_extension}"
    except Exception as e:
        return f"ERROR: {str(e)}"

def clean_resume_text(text: str) -> str:
    if not text:
        return ""
    # Remove special characters and extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def is_description_truncated(description: str) -> bool:
    truncation_indicators = [
        lambda x: len(x) >= 995,  # close to 1000 char limit
        lambda x: x.rstrip().endswith(('...', '…')),
        lambda x: re.search(r'\w+$', x) and not re.search(r'[.!?]$', x),
    ]
    return any(indicator(description) for indicator in truncation_indicators)

def format_job_description(description: str, truncated: bool = False) -> str:
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
        formatted_text = pattern.sub(r'\n\n\\1', formatted_text)
    
    formatted_text = re.sub(r'[•-]\s*', '\n• ', formatted_text)
    formatted_text = re.sub(r'(?<=\w)\.(?=\s*[A-Z])', '.\n', formatted_text)
    formatted_text = re.sub(r'\n{3,}', '\n\n', formatted_text)
    
    if truncated:
        formatted_text = formatted_text.rstrip() + "..."
    
    return formatted_text.strip()


# ------------------------------------------------------------------
# Callback for Like/Dislike
# ------------------------------------------------------------------
def user_interaction(index_in_cache, action):
    """
    index_in_cache: which job row's button was clicked (0..MAX_RESULTS-1)
    action: 'like' or 'dislike'
    
    We'll retrieve:
      - ad_id
      - resume_text
      - possibly do something with them (e.g. store in DB)
    """
    if index_in_cache < 0 or index_in_cache >= MAX_RESULTS:
        return "Invalid job index."
    
    cached = JOBS_CACHE[index_in_cache]
    if not cached:
        return "No job data at this slot."
    
    ad_id, metadata, full_resume_text = cached
    
    # Example logging or storing
    # In reality, you might store this info in a database or call an API
    print(f"[USER_INTERACTION] Action={action}, AdID={ad_id}, CV length={len(full_resume_text)} chars.")
    
    return f"You {action}d job {ad_id}."


# ------------------------------------------------------------------
# Callback to search jobs
# ------------------------------------------------------------------
def search_jobs(resume_file, num_results, city_filter):
    """
    1) Extract + clean resume
    2) Query Pinecone
    3) Populate the placeholders for up to MAX_RESULTS job ads
    4) Return status message
    """
    # Clear out global cache
    for i in range(MAX_RESULTS):
        JOBS_CACHE[i] = None

    if resume_file is None:
        return "Please upload a resume first."
    
    resume_text = extract_resume_text(resume_file)
    if resume_text is None or resume_text.startswith("ERROR"):
        return f"Error processing file: {resume_text}"

    clean_text = clean_resume_text(resume_text)
    if not clean_text:
        return "No text extracted from resume or file is invalid."

    # Attempt to read the database update time
    try:
        last_update = read_timestamp()
        last_update_dt = datetime.strptime(last_update, DATE_FORMAT)
        db_info = f"**Database last update:** {last_update_dt.strftime('%B %d, %Y at %I:%M %p')} (Stockholm Time)\n\n"
    except Exception as e:
        db_info = f"Error reading timestamp: {str(e)}\n\n"

    # Pinecone init
    try:
        handler = PineconeHandler()
    except Exception as e:
        return f"{db_info}Error connecting to Pinecone: {str(e)}"

    # Search
    try:
        results = handler.search_similar_ads(
            clean_text, top_k=num_results, city=city_filter.strip()
        )
    except Exception as e:
        return f"{db_info}Error searching jobs: {str(e)}"

    if not results:
        return f"{db_info}No matching jobs found."

    # Fill up to MAX_RESULTS
    text_output = [db_info + f"**Found {len(results)} matching jobs:**\n"]

    for i, match in enumerate(results[:MAX_RESULTS]):
        metadata = match.metadata
        score = match.score
        
        # We'll store data in our global JOBS_CACHE so user_interaction can retrieve it
        # You might have an 'id' or something in metadata that you treat as the ad_id
        ad_id = str(metadata.get('job_id', f"Unknown_{i}"))
        JOBS_CACHE[i] = (ad_id, metadata, clean_text)

        headline = metadata.get('headline', 'Untitled')
        city = metadata.get('city', 'Unknown City')
        occupation = metadata.get('occupation', 'Unknown Occupation')
        published = metadata.get('published', 'Unknown Date')
        desc = metadata.get('description', '')
        truncated = is_description_truncated(desc)
        snippet = desc[:2000] if truncated else desc
        formatted_desc = format_job_description(snippet, truncated=truncated)

        text_output.append(f"### {i+1}. {headline}")
        text_output.append(f"**Ad ID**: `{ad_id}`")
        text_output.append(f"**Match Score (Cosine)**: {score:.2f}")
        text_output.append(f"**Location**: {city}")
        text_output.append(f"**Occupation**: {occupation}")
        text_output.append(f"**Published**: {published}")
        text_output.append(formatted_desc or "*No description*")

        if truncated:
            text_output.append(
                "> **Note**: Description truncated. See original link for full details."
            )
            if 'webpage_url' in metadata:
                text_output.append(f"[View Original]({metadata['webpage_url']})")

        text_output.append("---")

    return "\n".join(text_output)


# ------------------------------------------------------------------
# Build Gradio interface 
# ------------------------------------------------------------------
def build_interface():
    with gr.Blocks() as demo:
        gr.Markdown("# AI-Powered Job Search (Gradio with Like/Dislike)")

        with gr.Row():
            resume_input = gr.File(label="Upload your resume (PDF, DOCX, DOC, or TXT)")
            num_results_slider = gr.Slider(
                minimum=1, maximum=MAX_RESULTS, value=5,
                step=1, label="Number of results"
            )
            city_input = gr.Textbox(
                label="Filter by city (optional)",
                placeholder="Enter a city to filter job results by location"
            )

        search_button = gr.Button("Search Jobs")
        results_markdown = gr.Markdown()

        # We create up to MAX_RESULTS rows for like/dislike
        # Each row has two buttons that map to user_interaction
        # We'll label them with the index so we can pass it to user_interaction
        output_messages = []
        for i in range(MAX_RESULTS):
            with gr.Row(visible=True) as row_i:
                # Each row: "Like" & "Dislike"
                btn_like = gr.Button(f"Like #{i+1}", variant="secondary", visible=True)
                btn_dislike = gr.Button(f"Dislike #{i+1}", variant="secondary", visible=True)

            # user_interaction callback => returns a small message
            msg = gr.Markdown(visible=True)
            output_messages.append(msg)

            # Wire the buttons to user_interaction
            # We pass:
            #   - The index in the JOBS_CACHE
            #   - The literal string 'like' or 'dislike'
            # The function returns a small text update
            btn_like.click(
                fn=user_interaction,
                inputs=[gr.State(i), gr.State("like")],
                outputs=[msg]
            )
            btn_dislike.click(
                fn=user_interaction,
                inputs=[gr.State(i), gr.State("dislike")],
                outputs=[msg]
            )

        # On search click => call search_jobs
        #  outputs => results_markdown (which displays the job list)
        search_button.click(
            fn=search_jobs,
            inputs=[resume_input, num_results_slider, city_input],
            outputs=[results_markdown]
        )

    return demo


if __name__ == "__main__":
    demo_app = build_interface()
    demo_app.launch()
