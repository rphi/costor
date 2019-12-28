'''
config.py
~~
Read in and parse config YML file and expose in the Config class.
'''

import yaml


class Config:
    def __init__(self):
        with open('./config.yml') as file:
            self.opts = yaml.load(file, Loader=yaml.BaseLoader)
