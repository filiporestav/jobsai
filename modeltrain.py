#!/usr/bin/env python3

import os
from torch.utils.data import DataLoader
from sentence_transformers import SentenceTransformer, InputExample, losses
# If you want to push to the HF Hub/Spaces programmatically:
#   pip install huggingface_hub
# from huggingface_hub import HfApi, HfFolder

from hopsworks_integration import HopsworksHandler

def main():
    hopsworks_handler = HopsworksHandler()
    training_data = hopsworks_handler.get_training_data()

    train_examples = []
    for row in training_data.itertuples():
        example = InputExample(
            texts=[row.cv_text, row.liked_job_text, row.disliked_job_text]
        )
        train_examples.append(example)

    # Rest of the training pipeline...

    #--------------------------------------------------------------------------
    # 1. (Optional) Setup your Hugging Face auth
    #--------------------------------------------------------------------------
    # If you need to log into your HF account, you can do:
    #   hf_token = os.getenv("HF_TOKEN")  # or read from a config file
    #   HfFolder.save_token(hf_token)
    #   api = HfApi()
    #
    # Then set something like:
    #   repo_id = "KolumbusLindh/my-weekly-model"
    #
    # Alternatively, you can push manually later via huggingface-cli.

    #--------------------------------------------------------------------------
    # 2. Placeholder training data
    #--------------------------------------------------------------------------
    # Suppose each tuple is: (CV_text, liked_job_text, disliked_job_text).
    # In a real scenario, you'd gather user feedback from your database.
    train_data = [
        ("My CV #1", "Job #1 that user liked", "Job #1 that user disliked"),
        ("My CV #2", "Job #2 that user liked", "Job #2 that user disliked"),
        # ...
    ]

    #--------------------------------------------------------------------------
    # 3. Convert data into Sentence Transformers InputExamples
    #--------------------------------------------------------------------------
    train_examples = []
    for (cv_text, liked_job_text, disliked_job_text) in train_data:
        example = InputExample(
            texts=[cv_text, liked_job_text, disliked_job_text]
            # TripletLoss expects exactly 3 texts: anchor, positive, negative
        )
        train_examples.append(example)

    #--------------------------------------------------------------------------
    # 4. Load the base model
    #--------------------------------------------------------------------------
    model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    model = SentenceTransformer(model_name)

    #--------------------------------------------------------------------------
    # 5. Prepare DataLoader & define the Triplet Loss
    #--------------------------------------------------------------------------
    # A typical margin is 0.5–1.0. Feel free to adjust it.
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=8)
    train_loss = losses.TripletLoss(
        model=model,
        distance_metric=losses.TripletDistanceMetric.COSINE,
        margin=0.5
    )

    #--------------------------------------------------------------------------
    # 6. Fine-tune (fit) the model
    #--------------------------------------------------------------------------
    # Just 1 epoch here for demo. In practice, tune #epochs/batch_size, etc.
    num_epochs = 1
    warmup_steps = int(len(train_dataloader) * num_epochs * 0.1)  # ~10% warmup

    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=num_epochs,
        warmup_steps=warmup_steps,
        show_progress_bar=True
    )

    #--------------------------------------------------------------------------
    # 7. Save model locally
    #--------------------------------------------------------------------------
    local_output_path = "my_finetuned_model"
    model.save(local_output_path)
    print(f"Model fine-tuned and saved locally to: {local_output_path}")

    #--------------------------------------------------------------------------
    # 8. (Optional) Push to your Hugging Face Space
    #--------------------------------------------------------------------------
    # If you want to push automatically:
    #
    #   model.push_to_hub(repo_id=repo_id, commit_message="Weekly model update")
    #
    # Or if you have a Space at e.g. https://huggingface.co/spaces/KolumbusLindh/<some-name>,
    # you’d create a repo on HF, then push to that repo. Typically one uses
    # huggingface-cli or the huggingface_hub methods for that:
    #
    #   api.create_repo(repo_id=repo_id, repo_type="model", private=False)
    #   model.push_to_hub(repo_id=repo_id)
    #
    #   # If it's a Space, you might need to store your model in the "models" folder
    #   # or however your Gradio app is set up to load it.

if __name__ == "__main__":
    main()
