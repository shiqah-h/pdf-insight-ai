from flask import Flask, request, jsonify, render_template, send_from_directory, g
from werkzeug.utils import secure_filename
import os
import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup
import logging
import re
import PyPDF2
import json
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Create Flask app instance
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
logger.info(f"Upload directory created/verified at: {app.config['UPLOAD_FOLDER']}")

# Initialize global variables for stored data
global_pdf_text = ""

# OpenRouter models configuration
OPENROUTER_MODELS = [
    {"id": "deepseek/deepseek-r1:free", "name": "DeepSeek R1", "description": "Advanced model optimized for reasoning and analysis"},
    {"id": "google/gemini-2.0-flash-exp:free", "name": "Gemini Flash", "description": "Fast and efficient version of Gemini"},
    {"id": "google/gemini-2.0-pro-exp-02-05:free", "name": "Gemini Pro", "description": "Latest Gemini model with enhanced capabilities"},
    {"id": "deepseek/deepseek-r1-distill-llama-70b:free", "name": "DeepSeek R1 Distill", "description": "Distilled version of DeepSeek R1 based on Llama 70B"}
]

# Serve static files (CSS, JS)
@app.route('/static/<path:filename>')
def serve_static(filename):
    """
    Serve static files from the 'static' directory.

    Args:
        filename (str): The filename of the static file to serve.

    Returns:
        The static file.
    """
    return send_from_directory('static', filename)

# Route for the main page
@app.route('/')
def index():
    """
    Render the main page.

    Returns:
        The rendered main page.
    """
    return render_template('index.html')

# Web search function using DuckDuckGo
def perform_web_search(query):
    """
    Perform a web search using DuckDuckGo.

    Args:
        query (str): The search query.

    Returns:
        The search results.
    """
    try:
        # Using DuckDuckGo's HTML page with parameters
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Encode query for URL
        encoded_query = requests.utils.quote(query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        # Use BeautifulSoup to parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find search results
        results = []
        for result in soup.select('.result'):
            title_elem = result.select_one('.result__title')
            snippet_elem = result.select_one('.result__snippet')
            link_elem = result.select_one('.result__url')
            
            if title_elem and snippet_elem:
                title = title_elem.get_text(strip=True)
                snippet = snippet_elem.get_text(strip=True)
                link = link_elem.get_text(strip=True) if link_elem else ""
                
                results.append({
                    'title': title,
                    'snippet': snippet,
                    'link': link
                })
                
                if len(results) >= 3:  # Limit to 3 results
                    break
        
        # Format results into a concise summary
        summary = "Web Search Results:\n\n"
        for result in results:
            summary += f"- {result['title']}\n  {result['link']}\n  {result['snippet']}\n\n"
        
        return summary
    except Exception as e:
        logger.error(f"Web search error: {str(e)}")
        return None

# Endpoint to handle file uploads
@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Handle file uploads.

    Returns:
        A JSON response with the uploaded file's filename and text length.
    """
    try:
        # Check if the file is present in the request
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        # Check if the file is a PDF
        if file and file.filename.endswith('.pdf'):
            # Read and extract text from the PDF
            pdf_document = fitz.open(stream=file.read(), filetype="pdf")
            text = ""
            for page in pdf_document:
                text += page.get_text()
            
            # Store the extracted text in the global variable
            global global_pdf_text
            global_pdf_text = text
            
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            logger.info(f"Saving file to: {filepath}")
            
            # Ensure directory exists again just to be safe
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            file.save(filepath)
            logger.info(f"File saved successfully at: {filepath}")
            
            return jsonify({
                'filename': file.filename,
                'text_length': len(text)
            })
        else:
            return jsonify({'error': 'Invalid file type. Please upload a PDF.'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint to handle chat requests
@app.route('/chat', methods=['POST'])
def chat():
    """
    Handle chat requests.

    Returns:
        A JSON response with the chat response.
    """
    try:
        # Get data from the request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        message = data.get('message')
        model_id = data.get('model', 'google/gemini-2.0-pro-exp-02-05:free')
        enable_web_search = data.get('enableWebSearch', False)

        if not message:
            return jsonify({'error': 'No message provided'}), 400

        if not global_pdf_text:
            return jsonify({'error': 'No PDF has been uploaded yet'}), 400

        # Construct the system message
        system_message = f"You are an AI assistant helping to analyze a PDF document. Here's the extracted text from the PDF:\n\n{global_pdf_text}\n\nPlease help answer questions about this document."

        # If web search is enabled, perform the search
        web_context = ""
        if enable_web_search:
            try:
                search_results = perform_web_search(message)
                if search_results:
                    web_context = f"\n\nRelevant web search results:\n{search_results}"
            except Exception as e:
                print(f"Web search error: {str(e)}")
                # Continue without web search results if there's an error

        # Combine system message, web context, and user message
        full_message = f"{system_message}{web_context}\n\nUser: {message}\nAssistant:"

        # Check for API key before making the request
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return jsonify({'error': 'OpenRouter API key is not configured. Please check your .env file.'}), 400

        try:
            # Make the API call
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'HTTP-Referer': 'http://localhost:5000',
                    'X-Title': 'PDF Analyzer'
                },
                json={
                    'model': model_id,
                    'messages': [
                        {'role': 'user', 'content': full_message}
                    ]
                }
            )
            
            # Log the response status and headers for debugging
            logger.info(f"OpenRouter API Response Status: {response.status_code}")
            logger.info(f"OpenRouter API Response Headers: {response.headers}")
            
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', {}).get('message')
                    if error_message:
                        logger.error(f"OpenRouter API Error: {error_message}")
                        return jsonify({'error': f"OpenRouter API Error: {error_message}"}), response.status_code
                    else:
                        logger.error(f"OpenRouter API Error: Status {response.status_code}")
                        return jsonify({'error': f"OpenRouter API Error: Status {response.status_code}"}), response.status_code
                except Exception as e:
                    logger.error(f"Failed to parse error response: {str(e)}")
                    return jsonify({'error': f'API request failed with status {response.status_code}'}), response.status_code

            response_data = response.json()
            logger.info("Successfully received response from OpenRouter API")
            
            if 'error' in response_data:
                error_message = response_data['error'].get('message') if isinstance(response_data['error'], dict) else str(response_data['error'])
                logger.error(f"Error in response data: {error_message}")
                return jsonify({'error': error_message}), 400

            # Extract the assistant's message from the response
            assistant_message = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
            if not assistant_message:
                logger.error("No response content found in API response")
                return jsonify({'error': 'No response content found'}), 500

            return jsonify({'response': assistant_message})

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return jsonify({'error': f'Failed to connect to OpenRouter API: {str(e)}'}), 500
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Check if the OpenRouter API key is set
    if not os.getenv('OPENROUTER_API_KEY'):
        logger.warning("OPENROUTER_API_KEY is not set. Please configure it in your environment variables.")
    # Run the Flask app
    app.run(debug=True)
