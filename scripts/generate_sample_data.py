"""Generate 10 dummy resume files (mix of .txt, .docx, .pdf) into resumes/.

This is a one-time setup script for sample/demo data. It is not imported by
fs_tools.py or llm_file_assistant.py, and only needs 'fpdf2' + 'python-docx'
(already listed in requirements.txt) to run.

Usage:
    python scripts/generate_sample_data.py
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from fpdf import FPDF

RESUMES_DIR = Path(__file__).resolve().parent.parent / "resumes"

# (filename without extension, format, resume body text)
RESUMES = [
    (
        "aditi_sharma",
        "txt",
        """Aditi Sharma
Email: aditi.sharma@example.com | Phone: +91-9800011122

Summary
Backend engineer with 4 years of experience building APIs with Python.

Skills
Python, Django, REST APIs, PostgreSQL, Docker, Git

Experience
Backend Developer, Nimbus Tech (2021 - Present)
- Built and maintained Python microservices handling 2M+ requests/day
- Migrated legacy Django monolith to a modular service architecture

Education
B.Tech in Computer Science, NIT Trichy (2017 - 2021)
""",
    ),
    (
        "rohan_verma",
        "txt",
        """Rohan Verma
Email: rohan.verma@example.com | Phone: +91-9800022233

Summary
Java backend developer specializing in enterprise applications.

Skills
Java, Spring Boot, Hibernate, Kafka, MySQL, Jenkins

Experience
Software Engineer, Bluewave Systems (2020 - Present)
- Developed Spring Boot services for payment processing
- Set up Kafka-based event pipelines for order management

Education
B.E. in Information Technology, VJTI Mumbai (2016 - 2020)
""",
    ),
    (
        "priya_nair",
        "txt",
        """Priya Nair
Email: priya.nair@example.com | Phone: +91-9800033344

Summary
Data scientist with strong Python and machine learning background.

Skills
Python, Pandas, NumPy, Scikit-learn, SQL, Tableau

Experience
Data Scientist, Insight Analytics (2019 - Present)
- Built Python pipelines for churn prediction using scikit-learn
- Automated reporting with Pandas, reducing manual effort by 70%

Education
M.Sc. in Statistics, University of Hyderabad (2017 - 2019)
""",
    ),
    (
        "karan_mehta",
        "txt",
        """Karan Mehta
Email: karan.mehta@example.com | Phone: +91-9800044455

Summary
Frontend engineer focused on building fast, accessible web apps.

Skills
JavaScript, TypeScript, React, Redux, HTML, CSS

Experience
Frontend Developer, PixelCraft Studio (2021 - Present)
- Built a component library used across 5 React products
- Improved Lighthouse performance scores from 62 to 94

Education
B.Tech in Computer Science, DTU Delhi (2017 - 2021)
""",
    ),
    (
        "sneha_iyer",
        "docx",
        """Sneha Iyer
Email: sneha.iyer@example.com | Phone: +91-9800055566

Summary
Cloud-focused backend engineer building scalable Python services on AWS.

Skills
Python, FastAPI, AWS Lambda, DynamoDB, Terraform

Experience
Cloud Engineer, Skyline Cloud Solutions (2020 - Present)
- Designed serverless Python APIs using FastAPI and AWS Lambda
- Reduced infrastructure cost by 35% via Terraform-managed autoscaling

Education
B.Tech in Electronics and Communication, IIT Guwahati (2016 - 2020)
""",
    ),
    (
        "vikram_singh",
        "docx",
        """Vikram Singh
Email: vikram.singh@example.com | Phone: +91-9800066677

Summary
Embedded systems engineer with experience in real-time firmware.

Skills
C, C++, RTOS, ARM Cortex-M, I2C/SPI, Embedded Linux

Experience
Embedded Software Engineer, Corewave Robotics (2018 - Present)
- Wrote real-time firmware in C++ for motor control systems
- Debugged low-level I2C/SPI communication issues on custom PCBs

Education
B.Tech in Electrical Engineering, IIT Roorkee (2014 - 2018)
""",
    ),
    (
        "ananya_gupta",
        "docx",
        """Ananya Gupta
Email: ananya.gupta@example.com | Phone: +91-9800077788

Summary
AI engineer building LLM-powered applications and agent workflows.

Skills
Python, LangChain, OpenAI API, LLM function calling, RAG, FastAPI

Experience
AI Engineer, NeuralArc AI (2022 - Present)
- Built a Python-based RAG pipeline for internal document search
- Implemented LLM tool-calling agents using LangChain and OpenAI API

Education
M.Tech in Artificial Intelligence, IIIT Hyderabad (2020 - 2022)
""",
    ),
    (
        "arjun_rao",
        "pdf",
        """Arjun Rao
Email: arjun.rao@example.com | Phone: +91-9800088899

Summary
DevOps engineer specializing in Kubernetes and CI/CD automation.

Skills
Go, Kubernetes, Docker, Helm, Terraform, GitHub Actions

Experience
DevOps Engineer, Cloudforge Systems (2019 - Present)
- Managed multi-cluster Kubernetes deployments across 3 regions
- Built CI/CD pipelines in GitHub Actions cutting deploy time by 50%

Education
B.Tech in Computer Science, BITS Pilani (2015 - 2019)
""",
    ),
    (
        "meera_joshi",
        "pdf",
        """Meera Joshi
Email: meera.joshi@example.com | Phone: +91-9800099900

Summary
Full-stack developer with a focus on Python backends and Flask APIs.

Skills
Python, Flask, PostgreSQL, React, Redis, Celery

Experience
Full-Stack Developer, Orbit Labs (2020 - Present)
- Built Flask APIs backed by PostgreSQL and Redis caching
- Used Celery for background job processing of resume parsing tasks

Education
B.Tech in Information Technology, COEP Pune (2016 - 2020)
""",
    ),
    (
        "rajesh_kumar",
        "pdf",
        """Rajesh Kumar
Email: rajesh.kumar@example.com | Phone: +91-9800011200

Summary
.NET backend developer with enterprise cloud experience on Azure.

Skills
C#, .NET Core, ASP.NET, Azure Functions, SQL Server

Experience
Software Engineer, Meridian Enterprise (2019 - Present)
- Built ASP.NET Core services deployed on Azure Functions
- Optimized SQL Server queries, cutting report generation time by 40%

Education
B.E. in Computer Engineering, Pune University (2015 - 2019)
""",
    ),
]


def write_txt(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def write_docx(path: Path, text: str) -> None:
    document = Document()
    for line in text.strip("\n").split("\n"):
        document.add_paragraph(line)
    document.save(str(path))


def write_pdf(path: Path, text: str) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in text.strip("\n").split("\n"):
        pdf.set_x(pdf.l_margin)
        if line.strip():
            pdf.multi_cell(0, 6, line)
        else:
            pdf.ln(6)
    pdf.output(str(path))


WRITERS = {"txt": write_txt, "docx": write_docx, "pdf": write_pdf}


def main() -> None:
    RESUMES_DIR.mkdir(parents=True, exist_ok=True)
    for name, fmt, text in RESUMES:
        out_path = RESUMES_DIR / f"resume_{name}.{fmt}"
        WRITERS[fmt](out_path, text)
        print(f"Created {out_path.relative_to(RESUMES_DIR.parent)}")
    print(f"\nDone. {len(RESUMES)} sample resumes written to '{RESUMES_DIR}/'.")


if __name__ == "__main__":
    main()
