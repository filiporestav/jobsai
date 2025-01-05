import streamlit as st
import PyPDF2
import io
import docx2txt
from typing import Optional
import re
from pinecone_handler import PineconeHandler
from time_handling import read_timestamp
from datetime import datetime
import os
from settings import DATE_FORMAT

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
        
    # Get the file extension
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    try:
        # Process based on file type
        if file_extension == 'pdf':
            return extract_text_from_pdf(uploaded_file)
        elif file_extension in ['docx', 'doc']:
            return extract_text_from_docx(uploaded_file)
        elif file_extension == 'txt':
            return str(uploaded_file.read(), "utf-8")
        else:
            st.error(f"Unsupported file format: {file_extension}")
            return None
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

def clean_resume_text(text: str) -> str:
    """Clean and process resume text"""
    if not text:
        return ""
        
    # Remove special characters and extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

def is_description_truncated(description: str) -> bool:
    """Check if the description appears to be truncated"""
    # Check for obvious truncation indicators
    truncation_indicators = [
        lambda x: len(x) >= 995,  # Close to the 1000 char limit
        lambda x: x.rstrip().endswith(('...', '…')),
        lambda x: re.search(r'\w+$', x) and not re.search(r'[.!?]$', x),  # Ends mid-word or without punctuation
    ]
    
    return any(indicator(description) for indicator in truncation_indicators)

def format_job_description(description: str, truncated: bool = False) -> str:
    """Format job description text with proper sections and line breaks"""
    if not description:
        return ""
    
    # Common section headers in job descriptions
    sections = [
        "About us", "About you", "About the role", "About the position",
        "Requirements", "Qualifications", "Skills", "Responsibilities",
        "What you'll do", "What we offer", "Benefits", "Your profile",
        "Required skills", "What you need", "Who you are"
    ]
    
    # Add line breaks before section headers
    formatted_text = description
    for section in sections:
        # Look for section headers with case-insensitive matching
        pattern = re.compile(f'({section}:?)', re.IGNORECASE)
        formatted_text = pattern.sub(r'\n\n\1', formatted_text)
    
    # Handle bullet points (both • and - symbols)
    formatted_text = re.sub(r'[•-]\s*', '\n• ', formatted_text)
    
    # Add line breaks for sentences that look like list items
    formatted_text = re.sub(r'(?<=\w)\.(?=\s*[A-Z])', '.\n', formatted_text)
    
    # Clean up any excessive line breaks
    formatted_text = re.sub(r'\n{3,}', '\n\n', formatted_text)
    
    if truncated:
        formatted_text = formatted_text.rstrip() + "..."
    
    return formatted_text.strip()



def main():
    # Add custom CSS
    st.markdown("""
        <style>
        .big-font {
            font-size: 24px !important;
            font-weight: bold;
            color: #1E3A8A;
        }
        .update-info {
            padding: 10px;
            background-color: #F3F4F6;
            border-radius: 5px;
            margin: 10px 0;
            font-size: 14px;
            color: #4B5563;
        }
        .step {
            margin: 10px 0;
            padding: 10px;
            background-color: white;
            border-radius: 5px;
            border: 1px solid #E5E7EB;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Main content
    st.markdown('<p class="big-font">AI-Powered Job Search</p>', unsafe_allow_html=True)
    st.markdown("""
        💼 **Transform Your Job Search with AI**
        
        Tired of searching for jobs? Let AI do the work for you! Upload your resume and discover 
        perfectly matched opportunities in minutes - not hours!
    """)
    
    # Sidebar content
    with st.sidebar:
        st.markdown("### How It Works")
        st.markdown("1. **Upload Resume**\n   PDF, DOCX, DOC, or TXT formats")
        st.markdown("2. **Extract Content**\n   AI processes your resume")
        st.markdown("3. **Smart Search**\n   Match against our database")
        st.markdown("4. **Get Matches**\n   View personalized recommendations")
        
        st.markdown("---")  # Divider
        
        # Database update info
        try:
            last_update = read_timestamp()
            last_update_dt = datetime.strptime(last_update, DATE_FORMAT)
            st.markdown("### Database Status")
            st.markdown("🔄 Updates once a day at midnight.")
            st.markdown(f"**Last update:** {last_update_dt.strftime('%B %d, %Y at %I:%M %p')} (Stockholm Time)")
        except Exception as e:
            st.error(f"Error reading timestamp: {str(e)}")
    
    # Initialize PineconeHandler
    try:
        handler = PineconeHandler()
    except Exception as e:
        st.error(f"Error connecting to Pinecone: {str(e)}")
        return
    
    # File uploader
    uploaded_file = st.file_uploader("Upload your resume", type=['pdf', 'docx', 'doc', 'txt'])
    
    # Search parameters
    num_results = st.slider("Number of results", min_value=1, max_value=20, value=5)
    
    if uploaded_file:
        with st.spinner("Processing resume..."):
            # Extract and clean resume text
            resume_text = extract_resume_text(uploaded_file)
            if resume_text:
                clean_text = clean_resume_text(resume_text)
                
                # Preview extracted text
                with st.expander("Preview extracted text"):
                    st.text(clean_text[:500] + "..." if len(clean_text) > 500 else clean_text)
                
                # Add a city filter textbox above the search button
                city_filter = st.text_input("Filter by city (optional)", value="", help="Enter a city to filter job results by location")

                # Search button
                if st.button("Search Jobs"):
                    with st.spinner("Searching for matching jobs..."):
                        try:
                            # Search for similar job ads
                            results = handler.search_similar_ads(clean_text, top_k=num_results, city=city_filter.strip())
                            
                            if results:
                                st.subheader("Matching Jobs")
                                for i, match in enumerate(results, 1):
                                    metadata = match.metadata
                                    score = match.score
                                    
                                    # Create job card
                                    with st.container():
                                        # Header section with key information
                                        col1, col2 = st.columns([2, 1])
                                        with col1:
                                            st.markdown(f"### {metadata['headline']}")
                                        with col2:
                                            st.markdown(f"**Match Score (Cosine):** {score:.2f}")
                                        
                                        # Job details section
                                        if metadata.get('logo_url'):
                                            st.image(metadata['logo_url'], width=100)
                                        st.markdown(f"**Location:** {metadata['city']}")
                                        st.markdown(f"**Occupation:** {metadata['occupation']}")
                                        st.markdown(f"**Published:** {metadata['published']}")
                                        
                                        # Check if description is truncated
                                        description = metadata['description']
                                        is_truncated = is_description_truncated(description)
                                        
                                        # Display initial description preview
                                        formatted_description = format_job_description(
                                            description[:500] if is_truncated else description,
                                            truncated=is_truncated
                                        )
                                        st.markdown(formatted_description)
                                        
                                        # If truncated, show expandable full description
                                        if is_truncated:
                                            with st.expander("Read Full Description"):
                                                # Try to fetch full description from webpage_url
                                                st.markdown("""
                                                    **Note:** The full description has been truncated in our database. 
                                                    Please visit the original job posting for complete details and for searching the job.
                                                """)
                                                if metadata.get('webpage_url'):
                                                    st.markdown(f"[View Original Job Posting]({metadata['webpage_url']})")
                                        
                                            st.markdown(f"📧 Contact: {metadata['email']}")
                                        
                                        st.markdown("---")
                            else:
                                st.info("No matching jobs found. Try adjusting your search criteria.")
                                
                        except Exception as e:
                            st.error(f"Error searching jobs: {str(e)}")

if __name__ == "__main__":
    main()