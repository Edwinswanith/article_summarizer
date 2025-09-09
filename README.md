# AI Document Summarizer

A Flask-based web application that uses AI to summarize documents with text and image content, featuring text-to-speech conversion and intelligent document processing.

## Features

- **Multi-format Document Processing**: Supports various document formats (PDF, DOCX, etc.)
- **AI-Powered Summarization**: Uses advanced language models to generate comprehensive summaries
- **Image Analysis**: Extracts and analyzes images from documents using Google Gemini Vision
- **Text-to-Speech**: Converts summaries to audio files for accessibility
- **Reference Extraction**: Automatically extracts and organizes document references
- **Session Management**: Secure session handling with automatic cleanup
- **Real-time Processing**: Shows processing progress and handles large documents efficiently

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **AI/ML**: Google Gemini API for text and image analysis
- **Frontend**: HTML, CSS, JavaScript
- **Audio Processing**: Text-to-speech conversion
- **File Processing**: Support for multiple document formats

## Project Structure

```
new/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (not tracked)
├── templates/
│   └── index.html                 # Main web interface
├── static/
│   ├── style.css                  # Application styling
│   ├── script.js                  # Frontend JavaScript
│   ├── audio/                     # Generated audio files
│   └── images/                    # Extracted document images
├── utility/
│   ├── file_processing.py         # Document parsing and text extraction
│   ├── summary_processing.py      # AI-powered text summarization
│   ├── audio_processing.py        # Text-to-speech conversion
│   ├── gemini_image_summarize.py  # Image analysis with Gemini Vision
│   ├── gemini_summarize_tool.py   # Gemini API integration
│   └── rag_processing.py          # RAG (Retrieval-Augmented Generation)
├── uploads/                       # Temporary file uploads
└── instance/                      # Flask instance folder
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd new
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the root directory with:
   ```
   FLASK_SECRET_KEY=your_secret_key_here
   GOOGLE_API_KEY=your_gemini_api_key_here
   # Add other required API keys
   ```

5. **Initialize the database**:
   The application will automatically create the SQLite database on first run.

## Usage

1. **Start the application**:
   ```bash
   python app.py
   ```
   The app will run on `http://localhost:8000`

2. **Upload a document**:
   - Navigate to the web interface
   - Select a document file (PDF, DOCX, etc.)
   - Click upload to begin processing

3. **View results**:
   - Read the AI-generated summary
   - Listen to the audio version (if generated)
   - Review extracted references
   - Download or save results as needed

4. **Clean up**:
   - Use the cleanup function to remove temporary files
   - Sessions automatically expire after 24 hours

## Features in Detail

### Document Processing
- Extracts text from multiple document formats
- Preserves document structure and page information
- Handles embedded images and graphics
- Maintains reference formatting

### AI Summarization
- Uses Google Gemini for intelligent text analysis
- Context-aware summarization considering document structure
- Integrates image content analysis with text
- Generates coherent, comprehensive summaries

### Image Analysis
- Extracts images from documents automatically
- Analyzes image content using Gemini Vision API
- Correlates image content with surrounding text
- Includes visual information in final summary

### Audio Generation
- Converts text summaries to speech
- Supports multiple audio formats
- Optimized for clarity and comprehension
- Accessible design for users with visual impairments

## Configuration

### Environment Variables
- `FLASK_SECRET_KEY`: Flask session encryption key
- `GOOGLE_API_KEY`: Google Gemini API access key
- Additional API keys as required by utility modules

### Session Configuration
- 24-hour session lifetime
- Secure cookie settings
- Automatic cleanup of temporary files
- SQLAlchemy-based session storage

## Development

### Running in Development Mode
```bash
export FLASK_ENV=development
python app.py
```

### File Upload Limits
The application handles file uploads with appropriate size limits and validation.

### Error Handling
Comprehensive error handling for:
- Invalid file formats
- API failures
- Processing errors
- Session management issues

## Security Features

- Secure session management with encrypted cookies
- File upload validation and sanitization
- Automatic cleanup of temporary files
- Environment-based configuration
- CSRF protection through Flask-Session

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
- Check the error logs in the console
- Ensure all environment variables are properly set
- Verify API keys are valid and have sufficient quota
- Review file format compatibility

## Changelog

### Version 1.0
- Initial release with core summarization features
- Multi-format document support
- AI-powered text and image analysis
- Audio generation capabilities
- Web-based user interface 
