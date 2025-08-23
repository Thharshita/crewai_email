import logging
import os
import datetime

log_file=f"log_{datetime.datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
LOG_DIRECTORY=os.path.join(os.getcwd(),'LOGS')
os.makedirs(LOG_DIRECTORY,exist_ok=True)
log_file_path=os.path.join(LOG_DIRECTORY,log_file)

logging.basicConfig(
    filename=log_file_path,
    format="[%(asctime)s] %(lineno)d  %(levelname)s - %(message)s",
    level=logging.INFO)  

logger=logging.getLogger(__name__)