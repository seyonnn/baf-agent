import os
import random

# Base directories
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STUDY_DIR = os.path.join(BASE_DIR, "data", "study_materials")
PERSONAL_DIR = os.path.join(BASE_DIR, "data", "personal_data")

os.makedirs(STUDY_DIR, exist_ok=True)
os.makedirs(PERSONAL_DIR, exist_ok=True)

# ==========================
# Study Materials Generation
# ==========================

study_templates = [
    """Unit {unit}: Introduction to {topic_title}

{topic_title} is a core concept in modern cybersecurity. In this unit, we discuss the basic definition, why it matters, and how it is used in real systems.

Subtopics:
- {topic_title} definition and core ideas
- Common use cases of {topic_title}
- Challenges and limitations

Short explanation:
{topic_expl}

Example questions:
1. Define {topic_title} and explain its purpose.
2. Give two real-world scenarios where {topic_title} is used.
3. What are some challenges when implementing {topic_title} in practice?
""",

    """Unit {unit}: Important Questions on {topic_title}

This file collects some frequently asked questions for exam preparation on {topic_title}.

Part A – Short Answer:
1. What is {topic_title}?
2. List any three key properties of {topic_title}.
3. Write a short note on why {topic_title} is important for system security.

Part B – Long Answer:
4. Explain how {topic_title} works with a simple example.
5. Discuss the advantages and drawbacks of using {topic_title} in real deployments.
""",

    """Unit {unit}: Previous Paper Snippets – {topic_title}

Below are sample questions inspired by previous university papers. They focus on understanding and applying {topic_title}.

1. Define {topic_title}. How does it contribute to the CIA triad?
2. Compare {topic_title} with one related concept of your choice.
3. A small company wants to adopt {topic_title}. What factors should they consider?
4. Case Study: Describe a situation where poor use of {topic_title} led to a security incident.
"""
]

topics = [
    ("Network Security", "Network security is about protecting data as it moves between devices over networks like the internet or local LANs."),
    ("Encryption", "Encryption converts readable data into an unreadable form so that only authorized parties with the right key can understand it."),
    ("Access Control", "Access control decides who is allowed to use which resource, and under what conditions."),
    ("Firewalls", "Firewalls are filters that decide which network traffic is allowed or blocked based on rules."),
    ("Intrusion Detection", "Intrusion detection aims to spot suspicious or malicious activity in a system or network."),
    ("Malware Analysis", "Malware analysis studies malicious software to understand how it works and how to defend against it."),
    ("Web Security", "Web security focuses on protecting websites and web applications from attacks like XSS and SQL injection."),
    ("Cloud Security", "Cloud security deals with protecting data, applications, and infrastructure hosted in cloud environments."),
    ("IoT Security", "IoT security is about protecting many small, connected devices that often have limited resources."),
    ("AI in Security", "AI in security uses machine learning and other AI techniques to detect threats and automate responses."),
]

print(f"Generating richer study materials in: {STUDY_DIR}")
study_count = 0
for unit in range(1, 6):  # Units 1–5
    for i, tmpl in enumerate(study_templates, start=1):
        topic_title, topic_expl = topics[(unit + i) % len(topics)]
        content = tmpl.format(unit=unit, topic_title=topic_title, topic_expl=topic_expl)
        fname = f"unit{unit}_{i}.txt"
        fpath = os.path.join(STUDY_DIR, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        study_count += 1
print(f"Created {study_count} study files.")

# ==========================
# Personal Docs Generation
# ==========================

print(f"Generating personal docs in: {PERSONAL_DIR}")

names = [
    "Arun Kumar", "Sneha R", "Kiran M", "Priya S", "Rahul N", "Divya P", "Vikram J"
]
cities = ["Chennai", "Bengaluru", "Hyderabad", "Pune", "Mumbai", "Delhi"]
colleges = ["REVA University", "Sample Engineering College", "Tech Institute of India"]

for i in range(1, 8):  # 7 students
    name = names[(i - 1) % len(names)]
    city = cities[(i - 1) % len(cities)]
    college = colleges[(i - 1) % len(colleges)]

    # Aadhaar-like document
    aadhaar_content = (
        f"--- Aadhaar Card (Mock) ---\n"
        f"Name           : {name}\n"
        f"Aadhaar Number : 7{i:03d} {i:04d} {i+23:04d}\n"
        f"DOB            : 200{i}-0{(i % 9) + 1}-15\n"
        f"Address        : No. {10+i}, Sample Street, {city}, India\n"
        f"\n"
        f"Note: This is a mock Aadhaar-style document for testing only.\n"
    )
    with open(os.path.join(PERSONAL_DIR, f"aadhaar_mock_{i}.txt"), "w", encoding="utf-8") as f:
        f.write(aadhaar_content)

    # College ID document
    college_id_content = (
        f"--- College ID (Mock) ---\n"
        f"Name       : {name}\n"
        f"College    : {college}\n"
        f"Student ID : REVA{i:04d}\n"
        f"Course     : MCA\n"
        f"Batch      : 202{i}-202{i+2}\n"
        f"\n"
        f"Note: This is a mock college ID document for testing only.\n"
    )
    with open(os.path.join(PERSONAL_DIR, f"college_id_mock_{i}.txt"), "w", encoding="utf-8") as f:
        f.write(college_id_content)

    # Marksheet document
    sem = (i % 4) + 1
    sgpa = round(7.0 + (i * 0.3), 2)
    marksheet_content = (
        f"--- Semester Marksheet (Mock) ---\n"
        f"Name         : {name}\n"
        f"Register No. : REG{i:05d}\n"
        f"Semester     : {sem}\n"
        f"Subjects     :\n"
        f"  - CS10{sem}1  Data Structures      : {random.randint(60, 95)}\n"
        f"  - CS10{sem}2  Operating Systems    : {random.randint(60, 95)}\n"
        f"  - CS10{sem}3  Database Systems     : {random.randint(60, 95)}\n"
        f"  - CS10{sem}4  Computer Networks    : {random.randint(60, 95)}\n"
        f"  - CS10{sem}5  Elective             : {random.randint(60, 95)}\n"
        f"\n"
        f"SGPA         : {sgpa}\n"
        f"\n"
        f"Note: This is a mock marksheet generated for testing only.\n"
    )
    with open(os.path.join(PERSONAL_DIR, f"marksheet_sem{sem}_{i}.txt"), "w", encoding="utf-8") as f:
        f.write(marksheet_content)

print("Dummy data generation complete.")