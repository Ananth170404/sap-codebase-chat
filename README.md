# 🔍 SAP Codebase Chat

> **Chat with your SAP Integration Suite / CPI project using Google Gemini.**  
> Upload any SAP project folder, understand its structure, flows, scripts, and
> configuration — all through a natural-language chat interface.

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red)
![Gemini](https://img.shields.io/badge/Google%20Gemini-2.0%20Flash-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

| Feature | Detail |
|---|---|
| 📁 **Universal folder support** | Works with any SAP CPI project structure — no hardcoding |
| 📄 **Multi-format file reading** | `.iflw`, `.groovy`, `.prop`, `.propdef`, `.xml`, `.wsdl`, `.xsl`, `.json`, `.yaml`, `.MF`, `.project`, and more |
| 🗺️ **Directory tree visualisation** | Sidebar renders the full project tree at a glance |
| 💬 **Conversational chat** | Full multi-turn conversation with memory |
| 🖼️ **Image-aware chat** | Attach screenshots, flow diagrams, or error images for analysis |
| 🤖 **SAP-aware AI** | System prompt pre-loaded with SAP CPI/iFlow expertise |
| 🔒 **Local-first** | Your code never leaves your machine (only sent to Gemini API) |
| 📦 **ZIP upload** | Zip your project and upload directly — no need to share paths |

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     Streamlit UI (app.py)                  │
│  Sidebar: API key · Load project · Directory tree          │
│  Main:    Chat messages · Image upload · Chat input        │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│                  file_processor.py                         │
│  build_directory_tree()  – pretty ASCII tree              │
│  build_codebase_context() – reads ALL text files into one  │
│                             Markdown context string        │
│  get_file_type_summary()  – counts files by extension      │
└────────────┬───────────────────────────────────────────────┘
             │  context string (up to ~225 k tokens)
             ▼
┌────────────────────────────────────────────────────────────┐
│              Google Gemini 2.0 Flash API                   │
│  • 1 M token context window                                │
│  • Multimodal (text + images)                              │
│  • Stateful multi-turn chat                                │
└────────────────────────────────────────────────────────────┘
```

### Why no vector database?

SAP CPI projects are typically small enough to fit inside Gemini's
**1 million token** context window directly.  Loading everything at once is
simpler *and* more accurate (no chunking artefacts, no retrieval misses).

For extremely large enterprise repositories you can add a RAG layer —
see [Contributing](#-contributing).

---

## 🚀 Quickstart

### 1 — Prerequisites

- Python 3.10 or newer
- A **Google Gemini API key** → [Get one free at Google AI Studio](https://aistudio.google.com/app/apikey)

### 2 — Install

```bash
# Clone the repo
git clone https://github.com/<your-org>/sap-codebase-chat.git
cd sap-codebase-chat

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3 — Configure (optional)

```bash
cp .env.example .env
# Edit .env and paste your Gemini API key
```

You can also paste the key directly in the sidebar — no `.env` needed.

### 4 — Run

```bash
streamlit run app.py
```

The app opens at **http://localhost:8501**.

---

## 📖 Usage

### Loading a project

**Option A – Upload ZIP**
1. Zip your unzipped SAP project folder.
2. In the sidebar choose *Upload ZIP File* and upload it.
3. Click **Load Project**.

**Option B – Local folder path**
1. In the sidebar choose *Local Folder Path*.
2. Paste the absolute path, e.g. `/Users/you/ESA_Exception_Handling`.
3. Click **Load Project**.

The sidebar will display the directory tree and file-type counts.

### Chatting

Type your question in the chat box. Examples:

```
"Give me a high-level summary of this SAP integration project."
"What does the Groovy script 'Custom Header' do exactly?"
"Explain the iFlow end-to-end: source → transformation → target."
"What retry mechanism is implemented and how does it work?"
"What parameters does this integration need at runtime?"
"Are there any potential issues or improvements you can spot?"
```

### Attaching images

Use the **📎 Attach an image** uploader above the chat box to include
a screenshot, error message, or flow diagram. Gemini will analyse it in
the context of your loaded codebase.

---

## 🗂️ Supported File Types

| Category | Extensions |
|---|---|
| SAP CPI | `.iflw`, `.prop`, `.propdef`, `.mf` |
| Scripting | `.groovy`, `.java`, `.js`, `.ts`, `.py`, `.sh` |
| Config | `.xml`, `.xsd`, `.wsdl`, `.xsl`, `.xslt`, `.json`, `.yaml`, `.yml`, `.toml`, `.properties` |
| Documentation | `.md`, `.txt`, `.rst` |
| Build | `.gradle`, `.pom`, `.project`, `.classpath` |
| Database | `.sql` |
| Web | `.html`, `.css` |
| Images (vision) | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg` |

---

## 📁 Project Structure

```
sap-codebase-chat/
├── app.py              # Streamlit UI + Gemini chat logic
├── file_processor.py   # Directory walker, file reader, context builder
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .gitignore
└── README.md
```

---

## 🔐 Security & Privacy

- Your source code is sent to **Google Gemini API** for analysis.
- The API key is stored only in your local `.env` or browser session (Streamlit).
- No data is stored by this application itself.
- Review [Google's data usage policy](https://ai.google.dev/terms) before loading sensitive/proprietary code.

---

## 🤝 Contributing

PRs are welcome! Some ideas for future enhancements:

- [ ] **RAG mode** — ChromaDB + Gemini embeddings for very large repos
- [ ] **File diff analysis** — compare two versions of an iFlow
- [ ] **Export chat** — download conversation as PDF/Markdown
- [ ] **iFlow visualiser** — render BPMN diagram from `.iflw` XML
- [ ] **Docker image** — one-command deployment

---

## 📄 License

MIT © 2024 — feel free to use, modify, and distribute.
