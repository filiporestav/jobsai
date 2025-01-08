import sys
import logging
import time_handling
from get_ads import get_all_ads
from pinecone_handler import PineconeHandler, load_all

from settings import LOG_LEVEL, LOG_DATE_FORMAT, LOG_FORMAT, PLACES, OCCUPATIONS

log = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=LOG_LEVEL, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

if __name__ == '__main__':
    """
    This is executed once to initialize the Pinecone database and 
    load all ads into it. To keep the database updated, run main.py   
    """
    # Initialize Pinecone handler
    handler = PineconeHandler()
    handler.recreate_index()
    log.info('Pinecone connection initialized')

    if PLACES or OCCUPATIONS:
        # If filtering by location/occupation, set past timestamp
        timestamp = time_handling.write_timestamp('2022-01-01T00:00:00')
    else:
        timestamp = time_handling.write_timestamp()
        all_ads = get_all_ads()
        load_all(all_ads)
        log.info(f'Loaded {len(all_ads)} into Pinecone. Timestamp: {timestamp}')