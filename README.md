#  INTELLECTA – AI-Powered Study Assistant

**INTELLECTA** is an AI-powered study assistant designed to make learning smarter, easier, and more interactive. Built using Python, Streamlit, and Google Gemini AI, it helps students understand concepts, prepare for examinations, and organize their study activities in one place.

##  Features

- **AI Chatbot:** Ask questions and get AI-generated answers.
- **Study Mode:** Generate structured, exam-oriented answers based on marks.
- **PDF Summarizer:** Upload PDF documents and get concise summaries.
- **Quiz Generator:** Generate topic-based quizzes for practice.
- **Flashcards:** Create interactive flashcards to improve learning and revision.
- **Study Planner:** Organize study tasks and track your progress.
- **Chat History:** Save and revisit previous conversations using SQLite.

##  Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Streamlit | Interactive web application |
| Google Gemini AI | AI-powered responses and content generation |
| SQLite | Chat history storage |
| PyPDF | PDF text extraction |
| Python-dotenv | Environment variable management |

##  Project Structure

```text
AI-Study-Assistant/
│
├── app.py
├── requirements.txt
├── intellecta-logo.png
├── .gitignore
└── README.md
```

##  Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/codehub-eeb/INTELLECTA.git
```

### 2. Navigate to the project folder

```bash
cd INTELLECTA
```

### 3. Create a virtual environment

```bash
python -m venv venv
```

### 4. Activate the virtual environment

**Windows:**

```bash
venv\Scripts\activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure your Gemini API key

Create a `.env` file in the project root directory:

```env
GEMINI_API_KEY=your_gemini_api_key
```

Get your API key from [Google AI Studio](https://aistudio.google.com/).

**Note:** Never share or upload your `.env` file or API key to GitHub.

### 7. Run the application

```bash
streamlit run app.py
```

The application will open in your browser at:

```text
http://localhost:8501
```

##  Project Objective

The main objective of INTELLECTA is to provide students with an intelligent learning environment where they can simplify complex topics, prepare for examinations, practice through quizzes, and manage their study schedules efficiently.

##  Future Enhancements

- User authentication and personalized profiles
- More advanced learning analytics
- Improved study recommendations
- Cloud-based storage
- Additional AI-powered learning tools

##  Developer

**Shaan G. Teli**

Full Stack Developer | AI & Python Enthusiast

## 📄 License

This project is developed for educational and learning purposes.
