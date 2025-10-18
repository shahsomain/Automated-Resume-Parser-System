# Automated_Resume_Parser_System 

# Resume Summarizer & Skill Classifier

Automate the extraction, summarization, and skill classification of resumes in PDF and DOCX formats using Python. Quickly get concise summaries and identify key technical skills for candidate evaluation.

---

## Features

- **Resume Summarization**: Generate a short, meaningful summary from any PDF or DOCX resume.  
- **Skill Classification**: Detect technical skills across categories like Programming, Data Science, Cloud Computing, Web Development, and Databases.  
- **File Support**: Accepts both PDF and Word (`.docx`) files.  
- **Text Cleaning**: Normalizes text for better summarization and analysis.  
- **Interactive File Selection**: GUI-based file selection using Tkinter.  

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd <repo-folder>

---

## Create a virtual environment and activate it:

python -m venv venv
source venv/bin/activate   # Linux / Mac
venv\Scripts\activate      # Windows

---

# Install dependencies:

pip install -r requirements.txt

---

# Usage

Run the main script:
python main.py

A file dialog will appear. Select a PDF or DOCX resume.
The script will:

1) Extract text from the resume
2) Clean the text
3) Generate a 3-sentence summary
4) Detect technical skills and categorize them

---

# Project Structure 
.
├── main.py                  # Script to run resume summarization & skill classification
├── resume_analyzer.py       # Core logic for text extraction, cleaning, summarization, and skill detection
├── requirements.txt         # Python dependencies
├── README.md                # Project documentation
└── output/                  # Optional folder to save outputs if extended


