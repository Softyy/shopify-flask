from flask import Flask
from dotenv import load_dotenv,find_dotenv

app = Flask(__name__)

load_dotenv(find_dotenv())
