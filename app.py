import gradio as gr
import PyPDF2
import docx2txt
from typing import Optional, List, Dict
import re
from pinecone_handler import PineconeHandler
import hopsworks
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        # Initialize Hopsworks
        project = "orestavf"
        api_key = os.getenv("HOPSWORKS_API_KEY")
        self.project = hopsworks.login(project=project, api_key_value=api_key)
        self.fs = self.project.get_feature_store()
        self.feedback_fg = self.fs.get_or_create_feature_group(
            name="job_feedback",
            version=1,
            primary_key=["job_id"],
            description="Feature group for storing user feedback on job matches.",
            online_enabled=True
        )

    def save_feedback(self, job_id: str, resume_text: str, headline: str,
                    occupation: str, description: str, is_relevant: bool):
        # Prepare feedback data as a pandas DataFrame
        feedback_data = pd.DataFrame([{
            "job_id": job_id,
            "resume_text": resume_text,
            "job_headline": headline,
            "job_occupation": occupation,
            "job_description": description,
            "is_relevant": is_relevant,
            #"timestamp": datetime.now()
        }])

        self.feedback_fg.insert(feedback_data)
        print(f"Feedback saved to Hopsworks for job ID: {job_id}")

def extract_text(file) -> Optional[str]:
    """Extract text from uploaded resume file"""
    if not file:
        return None
        
    try:
        file_type = file.name.split('.')[-1].lower()
        
        if file_type == 'pdf':
            pdf_reader = PyPDF2.PdfReader(file)
            return "\n".join(page.extract_text() for page in pdf_reader.pages)
            
        elif file_type in ['docx', 'doc']:
            return docx2txt.process(file)
            
        elif file_type == 'txt':
            return str(file.read(), "utf-8")
            
        else:
            return f"Unsupported file format: {file_type}"
    except Exception as e:
        return f"Error processing file: {str(e)}"

class JobMatcher:
    def __init__(self):
        self.handler = PineconeHandler()
        self.db = Database()
        self.current_results = []
        self.current_resume_text = None

    def search_jobs(self, file, num_results: int, city: str = "") -> List[Dict]:
        """Search for matching jobs and return results"""
        if not file:
            return [{"error": "Please upload a resume file."}]
            
        try:
            resume_text = extract_text(file)
            if not resume_text:
                return [{"error": "Could not extract text from resume."}]
                
            self.current_resume_text = resume_text
            resume_text = re.sub(r'\s+', ' ', resume_text).strip()
            
            # Get results from Pinecone
            results = self.handler.search_similar_ads(resume_text, top_k=num_results, city=city.strip())
            
            if not results:
                return [{"error": "No matching jobs found. Try adjusting your search criteria."}]
                
            # Store results with their Pinecone IDs
            self.current_results = [
                {
                    'id': result.id,  # Use Pinecone's ID
                    'score': result.score,
                    'metadata': result.metadata
                }
                for result in results
            ]
            
            return self.current_results
            
        except Exception as e:
            return [{"error": f"Error: {str(e)}"}]

    def submit_feedback(self, pinecone_id: str, is_relevant: bool) -> str:
        """Submit feedback for a specific job using Pinecone ID"""
        try:
            # Find the job in current results by Pinecone ID
            job = next((job for job in self.current_results if job['id'] == pinecone_id), None)

            if not job:
                return "Error: Job not found"

            metadata = job['metadata']

            self.db.save_feedback(
                job_id=pinecone_id,  # Use Pinecone's ID
                resume_text=self.current_resume_text,
                headline=metadata['headline'],
                occupation=metadata['occupation'],
                description=metadata['description'],
                is_relevant=is_relevant
            )
            return f"\u2713 Feedback saved for '{metadata['headline']}'"
        except Exception as e:
            return f"Error saving feedback: {str(e)}"


def create_interface():
    matcher = JobMatcher()
    
    with gr.Blocks() as interface:
        gr.Markdown("# AI-Powered Job Search")
        
        with gr.Row():
            file_input = gr.File(label="Upload Resume (PDF, DOCX, or TXT)")
            num_results = gr.Slider(minimum=1, maximum=20, value=5, step=1, label="Number of Results")
            city_input = gr.Textbox(label="Filter by City (Optional)")
        
        search_btn = gr.Button("Search Jobs")
        status = gr.Textbox(label="Status", interactive=False)
        
        # Container for job results and feedback buttons
        job_containers = []
        for i in range(20):  # Support up to 20 results
            with gr.Column(visible=False) as container:
                job_content = gr.Markdown("", elem_id=f"job_content_{i}")
                with gr.Row():
                    relevant_btn = gr.Button("👍 Relevant", elem_id=f"relevant_{i}")
                    not_relevant_btn = gr.Button("👎 Not Relevant", elem_id=f"not_relevant_{i}")
                feedback_status = gr.Markdown("")
            job_containers.append({
                'container': container,
                'content': job_content,
                'feedback_status': feedback_status,
                'pinecone_id': None  # Will store Pinecone ID for each job
            })
        
        def update_job_displays(file, num_results, city):
            results = matcher.search_jobs(file, num_results, city)
            
            # Initialize updates list with default values for all containers
            updates = []
            
            if "error" in results[0]:
                # If there's an error, hide all containers and show error message
                for _ in range(20):
                    updates.extend([
                        gr.update(visible=False),  # Container visibility
                        "",                        # Job content
                        ""                         # Feedback status
                    ])
                updates.append(results[0]["error"])  # Status message
                return updates
            
            # Process results and generate updates
            for i in range(20):
                if i < len(results):
                    job = results[i]
                    metadata = job['metadata']
                    
                    # Store Pinecone ID for this container
                    job_containers[i]['pinecone_id'] = job['id']
                    
                    content = f"""
### {metadata['headline']}
**Match Score:** {job['score']:.2f}  
**Location:** {metadata['city']}  
**Occupation:** {metadata['occupation']}  
**Published:** {metadata['published']}

{metadata['description'][:500]}...

**Contact:** {metadata.get('email', 'Not provided')}  
**More Info:** {metadata.get('webpage_url', 'Not available')}

*Job ID: {job['id']}*
"""
                    updates.extend([
                        gr.update(visible=True),  # Container visibility
                        content,                  # Job content
                        ""                        # Reset feedback status
                    ])
                else:
                    # For unused containers, hide them and clear content
                    updates.extend([
                        gr.update(visible=False),  # Container visibility
                        "",                        # Job content
                        ""                         # Reset feedback status
                    ])
            
            # Add final status message
            updates.append("Jobs found! If you decide to help us by rating them as relevant or not relevant, your CV will be uploaded to our servers and used for improving the service. ")
            
            return updates
        
        def handle_feedback(container_index: int, is_relevant: bool):
            pinecone_id = job_containers[container_index]['pinecone_id']
            if pinecone_id:
                response = matcher.submit_feedback(pinecone_id, is_relevant)
                return response
            return "Error: Job ID not found"
        
        # Connect search button
        all_outputs = []
        for container in job_containers:
            all_outputs.extend([
                container['container'],
                container['content'],
                container['feedback_status']
            ])
        all_outputs.append(status)
        
        search_btn.click(
            fn=update_job_displays,
            inputs=[file_input, num_results, city_input],
            outputs=all_outputs
        )
        
        # Connect feedback buttons for each container
        for i, container in enumerate(job_containers):
            container_obj = container['container']
            feedback_status = container['feedback_status']
            
            # Get the buttons from the container
            relevant_btn = container_obj.children[1].children[0]
            not_relevant_btn = container_obj.children[1].children[1]
            
            relevant_btn.click(
                fn=lambda idx=i: handle_feedback(idx, True),
                inputs=[],
                outputs=[feedback_status]
            )
            not_relevant_btn.click(
                fn=lambda idx=i: handle_feedback(idx, False),
                inputs=[],
                outputs=[feedback_status]
            )

    return interface

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(debug=True)
