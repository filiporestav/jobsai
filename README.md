---
title: "JobsAI Space"
emoji: "🤖"
colorFrom: "yellow"
colorTo: "blue"
sdk: "gradio"
sdk_version: "5.10.0"
app_file: "app.py"
pinned: false
---

# AI-Powered Swedish Job Matching Platform

This repository contains the final project for the course **ID2223 Scalable Machine Learning and Deep Learning** at KTH.

**Creators**:

- [Filip Orestav](https://www.linkedin.com/in/filip-orestav/)
- [Kolumbus Lindh](https://www.linkedin.com/in/kolumbuslindh/)

The project culminates in an AI-powered job matching platform, **JobsAI**, designed to help users find job listings tailored to their resumes. The application is hosted on Hugging Face Spaces and can be accessed here:  
[**JobsAI**](https://huggingface.co/spaces/forestav/jobsai)

---

## Overview

### Project Pitch

Finding the right job can be overwhelming, especially with over 40,000 listings available on Arbetsförmedlingen as of speaking. **JobsAI** streamlines this process by using **vector embeddings** and **similarity search** to match users’ resumes with the most relevant job postings. Say goodbye to endless scrolling and let AI do the heavy lifting!

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
- **Embedding Model**: The base model is [**sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2**](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2), a lightweight pre-trained transformer model that encodes sentences and paragraphs into a 384-dimensional dense vector space.
- **Finetuned Model**: The base model is finetuned on user-provided data every 7-days, and stored on HuggingFace. It can be found [**here!**](https://huggingface.co/forestav/job_matching_sentence_transformer)
- **Backend Updates**: GitHub Actions was utilized to automate daily updates to the vector database.
- **Feature Store**: To store user provided data, we used **Hopsworks** as it allows for easy feature interaction, as well as allows us to save older models to evaluate performance over time.

### Workflow

1. **Flowchart of JobsAI**
   ![JobsAI flowchart structure](https://i.imghippo.com/files/CZk3216mnA.png)

2. **Data Retrieval**:

   - Job data is fetched via the JobStream API and stored in Pinecone after being vectorized.
   - Metadata such as job title, description, location, and contact details is extracted.

3. **Similarity Search**:

   - User-uploaded resumes are vectorized using the same sentence transformer model.
   - Pinecone is queried for the top-k most similar job embeddings, which are then displayed to the user alongside their similarity scores.

4. **Feature Uploading**:
   - If a user chooses to leave feedback, by either clicking _Relevant_ or _Not Relevant_, the users CV is uploaded to Hopsworks together with the specific ad data, and the selected choice.
5. **Model Training**:
   - Once every seven days, a cron job on _Github Actions_ runs, where the base model is finetuned on the total data stored in the feature store.

---

## Code Architecture

### First-Time Setup

1. If you want to have your own Pinecone vector database, run `bootstrap.py` to:
   - Retrieve all job listings using the JobStream API’s snapshot endpoint.
   - Vectorize the listings and insert them into the Pinecone database.
2. To run the app locally, navigate to the folder and run `python app.py`

### Daily Updates

- **Automated Workflow**: A GitHub Actions workflow runs `main.py` daily at midnight.
- **Incremental Updates**: The `main.py` file is running daily at midnight and fetches job listings updated since the last recorded timestamp, ensuring the vector database remains current.

### Weekly Updates

- **Automated Workflow**: A GitHub Actions workflow runs `training_pipeline.ipynb` every Sunday at midnight.
- **Model Training**: Features are downloaded from Hopsworks, and the base Sentence Transformer is finetuned on the total dataset with both negative and positive examples.

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
4. [Hopsworks](https://www.hopsworks.ai/) Account and API key.
5. Optional: [Huggingface](https://huggingface.co/) Account and API key/Access Token.

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
3. Add your API keys as an environment variables:
   ```bash
   export PINECONE_API_KEY=<your-api-key>
   export HOPSWORKS_API_KEY=<your-api-key>
   export HUGGINGFACE_API_KEY=<your-api-key>
   ```
4. Run the application locally:
   ```bash
   python app.py
   ```
5. Open the Gradio app in your browser to upload resumes and view job recommendations.

## Potential Improvements

### Model Limitation

- The current embedding model truncates text longer than 128 tokens.
- For longer job descriptions, a model capable of processing more tokens (e.g., 512 or 1024) could improve accuracy.

### Scalability

- Embedding and querying currently run on CPU, which may limit performance for larger datasets.
- Switching to GPU-based processing would significantly enhance speed.

---

## Conclusion

**JobsAI** is a proof-of-concept platform that demonstrates how AI can revolutionize the job search experience. By leveraging vector embeddings and similarity search, the platform reduces inefficiencies and matches users with the most relevant job postings.

While it is functional and effective as a prototype, there are ample opportunities for enhancement, particularly in scalability and model capacity.
