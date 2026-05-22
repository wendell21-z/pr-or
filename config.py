import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://root:root@localhost:3306/vw_aps_pr'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
