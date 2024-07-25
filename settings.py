import os
from os.path import join, dirname, abspath
from dotenv import load_dotenv

dir_path = dirname(abspath("__file__"))
dotenv_path = join(dir_path, '.env')
load_dotenv(dotenv_path, encoding="utf-8", verbose=True)

access_token = os.environ.get('ACCESS_TOKEN')
cid = os.environ.get('CID')