# Personal Book Selection Assistant

## Overview

Personal Book Selection Assistant is an AI-powered recommendation system designed to help users decide whether a book is worth reading. Users can either upload a book cover image or enter the title of a book. Based on the user's reading preferences and history, the system provides a recommendation to **Buy**, **Try**, or **Skip** the book.

The project utilizes the BERT (Bidirectional Encoder Representations from Transformers) model to understand book-related information and generate personalized recommendations.

---

## Features

- Search for books using their title.
- Upload book cover images for identification and analysis.
- Personalized recommendations based on reading habits.
- AI-driven decision support using the BERT model.
- Recommendation categories:
  - Buy
  - Try
  - Skip

---

## Technology Stack

### Frontend
- HTML
- CSS
- JavaScript

### Backend
- Python
- Flask

### Machine Learning
- BERT
- Hugging Face Transformers
- PyTorch

### Database
- SQLite / MySQL (depending on implementation)

---

## Project Structure

```text
personal_book_selection_assistant/
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── templates/
│
├── model/
│
├── uploads/
│
├── app.py
├── requirements.txt
└── README.md
```

---

## Installation

### Clone the Repository

```bash
git clone https://github.com/vinyyzz/personal_book_selection_assistant.git
cd personal_book_selection_assistant
```

### Create a Virtual Environment

```bash
python -m venv venv
```

Activate the environment:

**macOS/Linux**

```bash
source venv/bin/activate
```

**Windows**

```bash
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run the Application

```bash
python app.py
```

Access the application at:

```text
http://localhost:5000
```

---

## How It Works

1. The user uploads a book cover image or enters a book title.
2. The system retrieves and processes relevant book information.
3. User reading preferences and history are analyzed.
4. The BERT model evaluates the book's relevance to the user's interests.
5. The system provides one of the following recommendations:
   - Buy
   - Try
   - Skip

---

## Use Case

Readers often face difficulty selecting their next book from the large number of available options. This application serves as a personalized reading assistant by leveraging machine learning and natural language processing techniques to provide informed recommendations based on individual reading preferences.

---

## Future Enhancements

- User authentication and profile management
- Integration with external book databases
- Reading history tracking
- Advanced recommendation algorithms
- Multi-language support
- Mobile application support

---

## Author

Vinay Kumar V

GitHub: https://github.com/vinyyzz

---

## License

This project was developed for educational and research purposes.
