import os 
import sys 
_oracle_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Oracle") 
sys.path.insert(0, _oracle_dir) 
from Oracle.app import app 