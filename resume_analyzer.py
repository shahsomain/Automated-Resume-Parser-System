import os
import re
import string
from tkinter import Tk, filedialog

import docx2txt
import PyPDF2
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lsa import LsaSummarizer


# ===============================
# 📂 File Selection (Fixed Version)
# ===============================
def select_file():
    root = Tk()
    root.withdraw()  # Hide the root window
    file_path = filedialog.askopenfilename(
        title="Select Resume",
        filetypes=[("PDF files", "*.pdf"), ("Word files", "*.docx")],
    )
    return file_path


# ===============================
# 📄 Extract Text from PDF/DOCX
# ===============================
def extract_text(file_path):
    if file_path.endswith(".pdf"):
        text = ""
        with open(file_path, "rb") as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + " "
        return text.strip()
    elif file_path.endswith(".docx"):
        return docx2txt.process(file_path)
    else:
        raise ValueError("Unsupported file format. Use PDF or DOCX.")


# ===============================
# ✨ Clean Text
# ===============================
def clean_text(text):
    text = text.lower()
    text = re.sub(r"\d+", "", text)
    return text.translate(str.maketrans("", "", string.punctuation))


# ===============================
# 🧠 Summarize Resume
# ===============================
def summarize_text(text, num_sentences=3):
    if not text.strip():
        return "No valid text found to summarize."

    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, num_sentences)
    return " ".join(str(sentence) for sentence in summary)


# ===============================
# 🛠️ Skill Classification
# ===============================
def classify_skills(text):
    skill_categories = {
        "Programming": ["python", "java", "c++", "javascript", "typescript"],
        "Data Science": [
            "machine learning",
            "deep learning",
            "tensorflow",
            "pytorch",
            "nlp",
            "pandas",
        ],
        "Cloud Computing": ["aws", "azure", "gcp", "kubernetes", "docker"],
        "Web Development": ["html", "css", "react", "angular", "node.js"],
        "Databases": ["mysql", "postgresql", "mongodb", "sql", "nosql"],
    }

    detected_skills = {
        category: [skill for skill in skills if skill in text]
        for category, skills in skill_categories.items()
    }

    # Remove empty categories
    detected_skills = {key: value for key, value in detected_skills.items() if value}

    return detected_skills


# Main Function


def main():
    print("📂 Please select your resume file (PDF or DOCX)...\n")

    resume_path = select_file()

    if not resume_path:
        print("❌ No file selected!")
        return

    print(f"\n✅ File Selected: {os.path.basename(resume_path)}")
    print(f"📁 Full Path: {resume_path}")

    try:
        resume_text = extract_text(resume_path)
        cleaned_resume = clean_text(resume_text)

        if not cleaned_resume:
            print("\n❌ No readable text found in the resume!")
            return

        # Generate Summary
        resume_summary = summarize_text(cleaned_resume)
        print("\n📄 Resume Summary:\n", resume_summary)

        # Classify Skills
        skills_detected = classify_skills(cleaned_resume)
        if skills_detected:
            print("\n🛠️ Detected Skills:")
            for category, skills in skills_detected.items():
                print(f"  🔹 {category}: {', '.join(skills)}")
        else:
            print("\n⚙️ No specific technical skills detected in this resume.")

    except Exception as e:
        print("\n❌ Error:", str(e))


# Run Script
if __name__ == "__main__":
    main()
