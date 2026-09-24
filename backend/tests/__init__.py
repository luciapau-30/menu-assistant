"""Isolated tests: never use local credentials or the development database."""
import os

os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['JWT_SECRET_KEY'] = 'test-only-secret-not-for-production-12345'
os.environ['EDAMAM_APP_ID'] = 'test'
os.environ['EDAMAM_APP_KEY'] = 'test'
os.environ['GROQ_API_KEY'] = 'test'
