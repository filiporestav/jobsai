import hopsworks
import pandas as pd

class HopsworksHandler:
    def __init__(self, project_name="jobsai"):
        self.project = hopsworks.login()
        self.fs = self.project.get_feature_store()

    def create_cv_feature_group(self):
        """Create the CV feature group."""
        try:
            cv_fg = self.fs.get_or_create_feature_group(
                name="cv_features",
                version=1,
                primary_key=["cv_id"],
                description="Features extracted from CVs"
            )
            print("CV feature group created/loaded successfully!")
            return cv_fg
        except Exception as e:
            print(f"Error creating CV feature group: {e}")

    def create_job_feedback_feature_group(self):
        """Create the job feedback feature group."""
        try:
            feedback_fg = self.fs.get_or_create_feature_group(
                name="job_feedback",
                version=1,
                primary_key=["event_id", "cv_id"],
                description="Feedback on job recommendations"
            )
            print("Feedback feature group created/loaded successfully!")
            return feedback_fg
        except Exception as e:
            print(f"Error creating feedback feature group: {e}")

    def insert_cv_features(self, cv_id, embeddings, metadata):
        """Insert CV features."""
        cv_fg = self.create_cv_feature_group()
        data = {
            "cv_id": [cv_id],
            "embeddings": [embeddings],
            **metadata
        }
        df = pd.DataFrame(data)
        cv_fg.insert(df)

    def insert_job_feedback(self, event_id, cv_id, job_id, like_dislike):
        """Insert feedback on job recommendations."""
        feedback_fg = self.create_job_feedback_feature_group()
        data = {
            "event_id": [event_id],
            "cv_id": [cv_id],
            "job_id": [job_id],
            "like_dislike": [like_dislike]
        }
        df = pd.DataFrame(data)
        feedback_fg.insert(df)

    def get_training_data(self):
        """Fetch combined CV and feedback data for training."""
        cv_fg = self.fs.get_feature_group("cv_features", version=1)
        feedback_fg = self.fs.get_feature_group("job_feedback", version=1)
        query = cv_fg.select_all().join(feedback_fg.select_all())
        return query.read()
