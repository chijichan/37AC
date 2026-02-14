"""
The flask application package.
"""

from flask import Flask
from flask_cors import CORS
app = Flask(__name__)
# CORS(app, origins=['https://www.322337.xyz'])
CORS(app) # 允许所有来源访问

import AC_web.views