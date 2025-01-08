from datetime import datetime
import sys
import logging
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY is not set. Please check your environment or secrets configuration.")

from settings import (
    LOG_LEVEL, 
    LOG_DATE_FORMAT, 
    LOG_FORMAT, 
    PINECONE_ENVIRONMENT,
    PINECONE_INDEX_NAME
)

log = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=LOG_LEVEL, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

class PineconeHandler:
    """
    Handles connections and operations with Pinecone vector database
    for storing and retrieving job ads
    """
    def __init__(self):
        self.pc = Pinecone(api_key=PINECONE_API_KEY)
        self.BATCH_SIZE = 100  # Number of vectors to upsert at once
        
        try:
            self.index = self.pc.Index(PINECONE_INDEX_NAME)
            log.info(f"Connected to existing index '{PINECONE_INDEX_NAME}'")
        except Exception as e:
            log.info(f"Creating new index '{PINECONE_INDEX_NAME}'")
            spec = ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
            
            self.pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=384,
                metric="cosine",
                spec=spec
            )
            self.index = self.pc.Index(PINECONE_INDEX_NAME)
        
        #self.model = SentenceTransformer('all-MiniLM-L6-v2')
        #self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        self.model = SentenceTransformer('forestav/job_matching_sentence_transformer')
        log.info(f"Initialized connection to Pinecone index '{PINECONE_INDEX_NAME}'")

    def _create_embedding(self, ad: Dict[str, Any]) -> List[float]:
        """Create embedding from job ad text"""
        try:
            # Safely get text fields with fallbacks to empty string
            headline = ad.get('headline', '') or ''
            occupation = ad.get('occupation', {})
            occupation_label = occupation.get('label', '') if occupation else ''
            description = ad.get('description', {})
            description_text = description.get('text', '') if description else ''
            
            # Combine text fields
            text_to_embed = f"{headline} {occupation_label} {description_text}".strip()
            
            # If we have no text to embed, raise an exception
            if not text_to_embed:
                raise ValueError("No text content available for embedding")
                
            return self.model.encode(text_to_embed).tolist()
        except Exception as e:
            log.error(f"Error creating embedding for ad {ad.get('id', 'unknown')}: {str(e)}")
            raise

    def _prepare_metadata(self, ad: Dict[str, Any]) -> Dict[str, str]:
        """Extract metadata from ad for storage"""
        try:
            # Safely get nested values with fallbacks
            application_details = ad.get('application_details', {}) or {}
            workplace_address = ad.get('workplace_address', {}) or {}
            occupation = ad.get('occupation', {}) or {}
            description = ad.get('description', {}) or {}
            
            # Limit the size of text fields and handle potential None values
            return {
                'email': (application_details.get('email', '') or '')[:100],
                'city': (workplace_address.get('municipality', '') or '')[:100],
                'occupation': (occupation.get('label', '') or '')[:100],
                'headline': (ad.get('headline', '') or '')[:200],
                'description': (description.get('text', '') or '')[:2000],
                'logo_url': (ad.get('logo_url', '') or '')[:200],
                'webpage_url': (ad.get('webpage_url', '') or '')[:200],
                'published': (ad.get('publication_date', '') or '')[:50]
            }
        except Exception as e:
            log.error(f"Error preparing metadata for ad {ad.get('id', 'unknown')}: {str(e)}")
            raise

    def _batch_upsert(self, vectors: List[tuple]) -> None:
        """
        Upsert a batch of vectors to Pinecone
        
        Args:
            vectors: List of tuples, each containing (id, vector, metadata)
        """
        try:
            # Prepare the vectors in the format Pinecone expects
            upsert_data = [(str(id), vec, meta) for id, vec, meta in vectors]
            
            # Perform the upsert operation
            self.index.upsert(vectors=upsert_data)
            
            log.debug(f"Successfully upserted batch of {len(vectors)} vectors")
        except Exception as e:
            log.error(f"Error upserting batch: {str(e)}")
            raise

    def upsert_ads(self, ads: List[Dict[str, Any]]) -> None:
        """Insert or update multiple ads in batches"""
        vectors = []
        deleted = 0
        processed = 0
        skipped = 0
        
        for ad in ads:
            try:
                # Skip None or empty ads
                if not ad:
                    log.warning("Skipping None or empty ad")
                    skipped += 1
                    continue

                ad_id = ad.get('id')
                if not ad_id:
                    log.warning("Skipping ad without ID")
                    skipped += 1
                    continue
                    
                if ad.get('removed', False):
                    self.delete_ad(ad_id)
                    deleted += 1
                    continue
                
                try:
                    vector = self._create_embedding(ad)
                    metadata = self._prepare_metadata(ad)
                    vectors.append((ad_id, vector, metadata))
                    processed += 1
                    
                    # When we reach batch size, upsert the batch
                    if len(vectors) >= self.BATCH_SIZE:
                        self._batch_upsert(vectors)
                        vectors = []  # Clear the batch
                        
                except Exception as e:
                    log.error(f"Error processing ad {ad_id}: {str(e)}")
                    skipped += 1
                    
            except Exception as e:
                log.error(f"Unexpected error processing ad: {str(e)}")
                skipped += 1
        
        # Upsert any remaining vectors
        if vectors:
            self._batch_upsert(vectors)
        
        log.info(f"Processing complete: {processed} ads upserted, {deleted} deleted, {skipped} skipped")

    def delete_ad(self, ad_id: str) -> None:
        """Delete an ad by ID"""
        try:
            self.index.delete(ids=[ad_id])
            log.debug(f"Deleted ad {ad_id} from Pinecone")
        except Exception as e:
            log.error(f"Error deleting ad {ad_id}: {str(e)}")

    def search_similar_ads(self, query: str, top_k: int = 5, city: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for similar job ads based on text query with optional city filtering."""
        query_embedding = self.model.encode(query).tolist()
        
        # Build the filter dictionary if city is provided
        metadata_filter = {}
        if city:
            city = city.lower().strip()  # Normalize
            city = city[0].upper() + city[1:]  # Capitalize first letter
            metadata_filter["city"] = {"$eq": city}

        # Execute the Pinecone query with optional metadata filtering
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=metadata_filter if metadata_filter else None
        )
        return results.matches

def load_all(all_ads):
    handler = PineconeHandler()
    handler.upsert_ads(all_ads)

def update(list_of_updated_ads):
    start = datetime.now()
    handler = PineconeHandler()
    handler.upsert_ads(list_of_updated_ads)
    log.info(f"{len(list_of_updated_ads)} ads processed. Time: {datetime.now() - start}")