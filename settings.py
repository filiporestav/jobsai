import logging

PINECONE_ENVIRONMENT = "gcp-starter"
#PINECONE_INDEX_NAME = "jobads-index"
PINECONE_INDEX_NAME = "jobsai-multilingual-small"

DB_TABLE_NAME = 'jobads'
DB_FILE_NAME = 'jobads_database_20220127.db'
TIMESTAMP_FILE = 'timestamp2.txt'

BASE_URL = 'https://jobstream.api.jobtechdev.se'
STREAM_URL = f"{BASE_URL}/stream"
SNAPSHOT_URL = f"{BASE_URL}/snapshot"

SLEEP_TIME_MINUTES = 5
MAX_UPDATES = 50

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

# Logging
LOG_LEVEL = logging.INFO  # Change INFO to DEBUG for verbose logging
LOG_FORMAT = '%(asctime)s  %(levelname)-8s %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

"""
Examples for the municiplaities in Västerbottens Län:
Skellefteå - kicB_LgH_2Dk
Robertsfors - p8Mv_377_bxp
Norsjö - XmpG_vPQ_K7T
Vindeln - izT6_zWu_tta
Umeå - QiGt_BLu_amP
Vännäs - utQc_6xq_Dfm
"""

# if you don't want to do geographical filtering, set PLACES = []
#PLACES = ['kicB_LgH_2Dk', 'p8Mv_377_bxp', 'XmpG_vPQ_K7T', 'izT6_zWu_tta', 'QiGt_BLu_amP', 'utQc_6xq_Dfm']
PLACES = []

# if you don't want to do filtering on occupations, set OCCUPATIONS = []
#OCCUPATIONS = ['Z6TY_xDf_Yup']  # Städare
OCCUPATIONS = []
