from google.adk.tools import FunctionTool
from .database import _find_doctors_in_db, _book_appointment_in_db

find_doctors = FunctionTool(_find_doctors_in_db)

book_appointment = FunctionTool(_book_appointment_in_db)