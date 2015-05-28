# Generic python libraries
import os

# Config library
from config import Config


basedir = os.path.abspath(os.path.dirname(__file__))
cfg = Config(file(os.path.join(basedir, 'settings.cfg')))
