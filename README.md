# PDF Analyzer AI

A web application that allows users to upload PDF documents and interact with them using various AI models through OpenRouter.

## Features

- PDF document upload and text extraction
- Interactive chat interface with AI models
- Multiple AI model selection
- Web search integration for enhanced responses
- Clean and responsive user interface

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Pip package manager

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pdf-analyzer-ai.git
cd pdf-analyzer-ai
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file and add your OpenRouter API key:
```
OPENROUTER_API_KEY=your_api_key_here
```

### Running the Application

```bash
flask run
```

Visit `http://localhost:5000` in your web browser.

## Project Structure

```
pdf-analyzer-ai/
├── app.py               # Main application file
├── requirements.txt     # Python dependencies
├── templates/           # HTML templates
│   └── index.html
├── static/              # Static files (CSS, JS)
├── uploads/             # Temporary storage for uploaded PDFs
├── README.md            # This documentation
└── .gitignore           # Files to ignore in version control
```

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/YourFeatureName`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/YourFeatureName`)
5. Open a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenRouter for providing access to multiple AI models
- Flask for the web framework
- PyMuPDF for PDF text extraction
