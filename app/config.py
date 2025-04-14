import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_PROJECT_ID = os.environ.get("GOOGLE_PROJECT_ID", "")
GOOGLE_LOCATION = os.environ.get("GOOGLE_LOCATION", "us-central1")
VERTEX_MODEL = os.environ.get("VERTEX_MODEL", "gemini-1.0-pro")

PERSPECTIVE_STATEMENTS = [
    "AI should enable healthcare professionals, not replace them.",
    "Technology should reduce administrative burden, allowing clinicians to focus on patient care.",
    "AI tools must be transparent and explainable to maintain trust in medical decision-making.",
    "Patient data privacy and security are paramount in healthcare AI applications.",
    "AI in healthcare should close health equity gaps, not widen them.",
    "The human connection in healthcare remains irreplaceable, even with advanced AI.",
    "AI adoption in healthcare requires proper clinician training and education."
]

MIN_WORD_COUNT = int(os.environ.get("MIN_WORD_COUNT", "200"))
MAX_WORD_COUNT = int(os.environ.get("MAX_WORD_COUNT", "250"))
DEFAULT_TEMPERATURE = float(os.environ.get("DEFAULT_TEMPERATURE", "0.7"))

CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.7"))
