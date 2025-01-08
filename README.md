---
title: "JobsAI Space"
emoji: "🤖"
colorFrom: "yellow"
colorTo: "blue"
sdk: "gradio" # or "streamlit", depending on your app
sdk_version: "3.0.5" # Specify the correct version of the SDK you're using
app_file: "app.py"
pinned: false
---

# AI-Powered Swedish Job Matching Platform

This repository contains the final project for the course **ID2223 Scalable Machine Learning and Deep Learning** at KTH.

The project culminates in an AI-powered job matching platform, **JobsAI**, designed to help users find job listings tailored to their resumes. The application is hosted on Streamlit Community Cloud and can be accessed here:  
[**JobsAI**](https://jobsai.streamlit.app/)

---

## Overview

### Project Pitch

Finding the right job can be overwhelming, especially with over 40,000 listings available on Arbetsförmedlingen. **JobsAI** streamlines this process by using **vector embeddings** and **similarity search** to match users’ resumes with the most relevant job postings. Say goodbye to endless scrolling and let AI do the heavy lifting!

---

## Problem Statement

Traditional job search methods often involve manual browsing of job listings, leading to inefficiency and mismatched applications. To address this, we developed an AI-powered job matching platform that:

1. **Analyzes resumes and job descriptions** to calculate compatibility scores.
2. **Recommends the most relevant job postings** based on semantic similarity.

The platform leverages **Natural Language Processing (NLP)** and machine learning to eliminate the inefficiencies of manual job searches.

### Data Sources

The platform uses two primary data sources:

1. **Job Listings**: Retrieved via Arbetsförmedlingen’s [JobStream API](https://jobstream.api.jobtechdev.se/), which provides real-time updates for job postings.
2. **Resumes**: Uploaded directly by users via the frontend application.

---

## Methodology

### Tool Selection

- **Vector Database**: After evaluating several options, we chose **Pinecone** for its ease of use and targeted support for vector embeddings.
- **Embedding Model**: We used [**sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2**](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2), a pre-trained transformer model that encodes sentences and paragraphs into a 384-dimensional dense vector space.
- **Backend Updates**: GitHub Actions was utilized to automate daily updates to the vector database.

### Workflow

1. **Data Retrieval**:

   - Job data is fetched via the JobStream API and stored in Pinecone after being vectorized.
   - Metadata such as job title, description, location, and contact details is extracted.

2. **Similarity Search**:
   - User-uploaded resumes are vectorized using the same sentence transformer model.
   - Pinecone is queried for the top-k most similar job embeddings, which are then displayed to the user alongside their similarity scores.

---

## Code Architecture

### First-Time Setup

1. Run `bootstrap.py` to:
   - Retrieve all job listings using the JobStream API’s snapshot endpoint.
   - Vectorize the listings and insert them into the Pinecone database.
2. Embeddings and metadata are generated using helper functions:
   - `_create_embedding`: Combines job title, occupation, and description for encoding into a dense vector.
   - `_prepare_metadata`: Extracts additional details like email, location, and timestamps for storage alongside embeddings.

### Daily Updates

- **Automated Workflow**: A GitHub Actions workflow runs `main.py` daily at midnight.
- **Incremental Updates**: The `keep_updated.py` function fetches job listings updated since the last recorded timestamp, ensuring the vector database remains current.

### Querying for Matches

- When a user uploads their resume:
  - The resume is encoded using the same transformer model.
  - Pinecone’s similarity search retrieves the top-k most relevant job listings.

---

## How to Run

### Prerequisites

1. Python 3.x installed locally.
2. A [Pinecone](https://www.pinecone.io/) account and API key.
3. Arbetsförmedlingen JobStream API access (free).

### Steps

1. Clone this repository:
   ```bash
   git clone https://github.com/filiporestav/jobsai.git
   cd jobsai
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Add your Pinecone API key as an environment variable:
   ```bash
   export PINECONE_API_KEY=<your-api-key>
   ```
4. Run the application locally:
   ```bash
   streamlit run app.py
   ```
5. Open the Streamlit app in your browser to upload resumes and view job recommendations.

## Potential Improvements

### Model Limitation

- The current embedding model truncates text longer than 128 tokens.
- For longer job descriptions, a model capable of processing more tokens (e.g., 512 or 1024) could improve accuracy.

### Active Learning

- Adding a feedback loop for users to label jobs as "Relevant" or "Not Relevant" could fine-tune the model.
- Limitations in Streamlit’s reactivity make it unsuitable for collecting real-time feedback.
- A future iteration could use **React** for a more seamless UI experience.

### Scalability

- Embedding and querying currently run on CPU, which may limit performance for larger datasets.
- Switching to GPU-based processing would significantly enhance speed.

---

## Conclusion

**JobsAI** is a proof-of-concept platform that demonstrates how AI can revolutionize the job search experience. By leveraging vector embeddings and similarity search, the platform reduces inefficiencies and matches users with the most relevant job postings.

While it is functional and effective as a prototype, there are ample opportunities for enhancement, particularly in scalability, UI design, and model fine-tuning.

For a live demo, visit [**JobsAI**](https://jobsai.streamlit.app/).
