# Generic libraries
import os

from config import Config

__author__ = 'dhkim'

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
cfg = Config(file(os.path.join(basedir, 'settings.cfg')))
