# AI-Powered Swedish Job Matching Platform

This repository is the final project for the course ID2223 Scalable Machine Learning at KTH.

The final product can be seen by pressing the link below, and is hosted on Streamlit Community Cloud.

[**JobsAI**](https://jobsai.streamlit.app/)

## Short pitch

Have you ever wanted to know which jobs that would fit your competences and experiences the best? Look no more, Jobs AI solves this. We use vector embeddings and similarity search to find the job listings with the highest similarity to your resume, so you don't have to browse through the 40,000+ job listings available on Arbetsförmedlingen.

## Problem description

The project aims to develop an AI-powered job matching platform that connects job seekers with suitable openings by analyzing resumes and job descriptions. The prediction problem involves calculating compatibility scores between resumes and job postings to recommend the most relevant positions. Data comes from two sources: (1) publicly available job listings, accessible through the Arbetsförmedlingen API, and (2) resume data, uploaded by the user. The platform solves the inefficiency of manual job searches and mismatched applications by
leveraging machine learning and natural language processing (NLP).

## Dataset

The data is retrieved from [Arbetsförmedlingen's (the Swedish Public Employment Service) API](https://jobstream.api.jobtechdev.se/). It gives access to all job listings which are published on their job listings bank, inlcuding real time information regarding changes to these listings such as new publications, deletions or updates or job descriptions.

## Method

When building the program, the first thing that we did was to do some analysis of relevant tools for the project. We were thinking about having Hopsworks as the serverless platform which we would upload the job listings data and then fetch the data from. However, since we only needed to store vector embeddings we decided to use a service targeted specifically for that purpose. Some analysis led us into Pinecone, a vector database which is easy to configure and work with, used by several large companies.

When the vector database tool was choosed, we needed to begin working and analyzing how we could get data from Arbetsförmedlingen's API. Luckily for us, Arbetsförmedlingen has some easy-accesible APIs to work with, that are free. We choosed their JobStream API since it allows us to have an own copy of all listings which are published through Arbetsförmedlingen.

## How the code works

The code is fairly simple thanks to the tools we have used.

### First-time setup code description

1. The first thing one should do is to run `boostrap.py`. This is done only once (in the beginning) to initialize the Pinecone database and load all ads into it. This program calls the `get_all_ads` method in `get_ads.py`, which in turn calls the snapshot endpoint `https://jobstream.api.jobtechdev.se/snapshot` to get a snapshot of all the job listings up at this current time.
2. When all ads have been retrieved, we insert it into the Pinecone vector database. This is done through the `upsert_ads` method in `pinecone_handler.py`, which calls `_create_embedding` and `_prepare_metadata` to create embeddings and metadata respectively.
3. The `_create_embedding` function takes an ad as an input and parses the JSON values for headline, occupation and description keys, and then combines these three into a single text. It then encodes the text with the help of a SentenceTransformer. We chose the [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2). It maps sentences and paragraphs to a 384 dimensional dense vector space and is fine-tuned on [nreimers/MiniLM-l&-H384-uncased](https://huggingface.co/nreimers/MiniLM-L6-H384-uncased) to given a sentence from the pair, the model should predict which out of a set of randomly other sentences, was actually paired with it in their dataset. It is intended to be used as a sentence and short paragraph encoder.
4. The `_prepare_metadata` function extracts metadata from the ad, which is stored together with the vector embedding in the Pinecone vector database. Since some JSON values such as email and municipality were nested, we had to parse them in a nested manner.
5. When 100 ads (our batch size for insertion) have been vectorized and retrieved metadata from, we upsert all the ads to the Pinecone vector database through the `_batch_upsert` function.

### Daily code description

We have set up a Github Actions Workflow to run `main.py` each day during midnight. This program calls the `keep_updated.py` function which, as the name suggests, keeps the vector database updated. It retrieves the timestamp of the last update, which is stored in `timestamp2.txt` file. It then uses this timestamp as a HTTP parameter in the request to the API, so that only the changes from this timestamp to the current time is sent as an response from the API.

When the changes of job listings from this timestamp has been retrieved, it calls the `PineconeHandler` to upsert the ads into the vector database, deleting removed ads and inserting new ads.

### Querying from the vector database

Querying from the Pinecone vector database is simple and fast thanks to the Pinecone API. When a resume is uploaded on the frontend (Streamlit app), the Streamlit app calls the `search_similar_ads` from the `PineconeHandler`, encoding the resume text with the [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) SentenceTransformer, as the job listings were encoded with. It then queries the most similar vector embeddings from the Pinecone vector database and returns the `top_k` (default is 5) most similar job listings, along with their metadata. It then displays those jobs to the user, along with their similarity scores.

## How to run the code

1. Clone the Github repository to your local machine.
2. Navigate to the cloned repository folder on your machine in the terminal and run `python -r requirements.txt`
3. Sign up for an account at [Pinecone](https://www.pinecone.io/) and create an API key.
4. Save the API key as a Github Actions Secret, with the name `PINECONE_API_KEY`.
5. Run `python bootstrap.py`. This may take a while since all job listings have to be retrieved from the API and then vectorized and stored in the vector database.
6. To update the vector database, run `python main.py`. This should preferebly be scheduled using e.g. Github Actions Workflow.
7. Run `streamlit run app.py` to start the Streamlit app locally, where you can interact with the application using an UI and be able to upload your own resume to find the most relevant jobs for you.

## Potential improvements

1. The [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) truncates input text longer than 256 word pieces. To capture all the semantics from job listings, we probably need a sentence transformer which can embed longer inputs texts.
2. The [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) is not optimized for multilingual text. Many people in Sweden have their resumes in Sweden, so better performance would probably achieved with a multilingual model.
3. We currently truncate the job descriptions after 1000 characters. To capture the full context, we should not truncate the job descriptions from the listings. This requires more data storage but would give better performance.
4. Users should be able to filter on municipality or location, because the current app ignores where the person wants to work (often not explicitly mentioned in their resume), making many job listings not relevant anyway.
