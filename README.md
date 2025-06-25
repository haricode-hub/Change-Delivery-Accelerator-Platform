# 🧠 Flexcube Documentation, Code, Test Case & Test Data Generator

A full-stack AI-powered application that automates the generation of **Flexcube documentation**, **PL/SQL code**, **test cases**, and **test data** using **Flask**, **React**, **Qdrant**, and **LLMs** (LLaMA 3.3 via Groq API).

---

## 🚀 Features

### 📄 1. Functional Document Generator (`/generate-doc`)
- Generates `.docx` Word documents with Flexcube functional specifications.
- Uses LLM + vector search (Qdrant) from Flexcube user guides (v12.x and v14.x).
- Includes logo, structured formatting, and auto-named output.

### 🧪 2. Test Case Generator (`/generate-test-cases`)
- Creates structured `.xlsx` test cases for Flexcube screens/functions.
- Queries Qdrant vector DB (Flexcube User Guides + `fn_tables2`) for examples.
- Formats output for easy QA/test team consumption.

### 🧬 3. Test Data Generator
- **STDCIF (`/generate-stdcif`)**: Generates CIF test data (default: 50 records).
- **STDCUSAC (`/generate-stdcusac`)**: Generates Customer Account data (default: 10 records).
- Uses pre-defined Excel templates and logic to synthesize realistic test data.

### 💡 4. PL/SQL Code Generator (`/generate-code`)
- Accepts natural language input and generates PL/SQL code snippets.
- Integrates with Qdrant (SQL & DDL collections).
- Uses Groq’s LLaMA 3.3 model for intelligent code generation.

### 🌐 5. React Frontend (`/`)
- Clean and modern React-based UI served via Flask.
- Integrated with backend using RESTful APIs.
- CORS-enabled for smooth cross-origin communication.

---

## 🛠️ Tech Stack

| Layer       | Tech Used                          |
|-------------|------------------------------------|
| **Frontend** | React                              |
| **Backend**  | Flask, Waitress (production WSGI)  |
| **Vector DB**| Qdrant                             |
| **LLM**      | Groq API (LLaMA 3.3)               |
| **Documents**| `python-docx`, `openpyxl`          |
| **Env Config**| `python-dotenv`, `pydantic`       |

