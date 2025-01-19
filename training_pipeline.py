#!/usr/bin/env python
# coding: utf-8

# In[1]:


import hopsworks
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
from sklearn.model_selection import train_test_split
from dotenv import load_dotenv
import os


# In[2]:


# Initialize Hopsworks connection
load_dotenv()

api_key = os.getenv("HOPSWORKS_API_KEY")
project = hopsworks.login(project="orestavf", api_key_value=api_key)
fs = project.get_feature_store()


# In[3]:


# Load preprocessed data
feedback_fg = fs.get_feature_group(name="job_feedback", version=1)
feedback_df = feedback_fg.read()


# In[4]:


# Split into train and validation sets
train_df, val_df = train_test_split(feedback_df, test_size=0.2, random_state=42)


# In[5]:


# Prepare data for SentenceTransformer
def prepare_examples(df):
    examples = []
    for _, row in df.iterrows():
        examples.append(
            InputExample(
                texts=[row["resume_text"], row["job_description"]],
                label=float(row["is_relevant"])  # Convert to float for loss calculation
            )
        )
    return examples


# In[6]:


train_examples = prepare_examples(train_df)
val_examples = prepare_examples(val_df)


# In[7]:


# Load pretrained SentenceTransformer
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')


# In[8]:


# Define DataLoader
train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
val_dataloader = DataLoader(val_examples, shuffle=False, batch_size=16)


# In[9]:


# Define loss
train_loss = losses.CosineSimilarityLoss(model)


# In[10]:


# Configure training
num_epochs = 3
warmup_steps = int(len(train_dataloader) * num_epochs * 0.1)  # 10% of training as warmup


# In[ ]:


# Train the model
model.fit(
    train_objectives=[(train_dataloader, train_loss)],
    evaluator=None,  # Add an evaluator if needed
    epochs=num_epochs,
    warmup_steps=warmup_steps,
    output_path="./finetuned_model"
)


# In[ ]:


# Save the trained model locally
#model.save("./finetuned_model")
#print("Model finetuned and saved locally!")


# In[12]:


from hsml.schema import Schema
from hsml.model_schema import ModelSchema


# In[13]:


# Define the Model Schema
X_train_sample = train_df[["resume_text", "job_description"]].sample(1).values  # Input example
y_train_sample = train_df["is_relevant"].sample(1).values  # Output example


# In[14]:


input_schema = Schema(X_train_sample)
output_schema = Schema(y_train_sample)
model_schema = ModelSchema(input_schema=input_schema, output_schema=output_schema)


# In[15]:


# Get Model Registry
mr = project.get_model_registry()


# In[17]:


# Check if the model already exists and get the latest version
try:
    existing_model = mr.get_model(name="job_matching_sentence_transformer")
    latest_version = existing_model.version
    print(f"Model already exists with version {latest_version}")
except:
    # If the model doesn't exist, set version to 1
    latest_version = 0

# Set the new version dynamically
new_version = latest_version + 1


# In[19]:


# Register the model in the Model Registry
job_matching_model = mr.python.create_model(
    name="job_matching_sentence_transformer",
    #metrics=metrics,
    model_schema=model_schema,
    input_example=X_train_sample,
    description="Finetuned SentenceTransformer for job matching",
    version=new_version,
)


# In[20]:


# Save model artifacts to the Model Registry
job_matching_model.save("./finetuned_model")
print("Model registered in Hopsworks Model Registry!")


# In[ ]:


# Push the model to huggingface
model.push_to_hub(repo_id="forestav/job_matching_sentence_transformer", exist_ok=True)

