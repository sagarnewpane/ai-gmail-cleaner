# CleanMail - Automated Gmail Cleanup Tool

CleanMail is a Python-based tool that helps you automatically organize and clean up your Gmail inbox. It uses the Gmail API and a generative AI model to classify your emails, allowing you to quickly deal with unimportant messages and manage unsubscribe links.

## Features

- **Email Classification**: Automatically classifies emails as `IMPORTANT`, `NOT IMPORTANT`.
- **Interactive Workflow**: Puts you in control with interactive prompts to confirm actions like moving emails to a "Review" label or to the Trash.
- **Database Storage**: Fetches and stores your email metadata in a local SQLite database for fast, offline processing and to avoid re-fetching data from Gmail.
- **Unsubscribe Helper**: Extracts all unsubscribe links from your emails and lets you either export them to a CSV file or view them in the terminal for easy unsubscribing.
- **Smart & Safe**:
    - Creates a "Review" label in your Gmail for you to double-check emails classified as "NOT IMPORTANT" before they are moved to Trash.
    - Remembers which emails have been processed to avoid re-classifying them every time.

## How It Works

1.  **Authentication**: Securely connects to your Gmail account using OAuth 2.0. The first time you run it, you'll be asked to authorize access.
2.  **Fetching**: Downloads metadata for all your emails (sender, subject, snippet, etc.) and stores them in a local `emails.db` file.
3.  **Classification**: For any unclassified emails in the database, it sends the content to the **Gemini API** to determine their category.
4.  **Sorting**:
    - Emails marked as `NOT IMPORTANT` are moved to a newly created `Review` label in your Gmail account.
    - You are then prompted to confirm if you want to move all emails under the `Review` label to the Trash.
5.  **Unsubscribing**: It scans the database for unsubscribe links and gives you the option to export them to a CSV file or print them in the terminal.

## Setup

### 1. Prerequisites
- Python 3.6+
- `pip` for installing packages

### 2. Google Cloud Project & Gmail API
- Go to the [Google Cloud Console](https://console.cloud.google.com/).
- Create a new project.
- Enable the **Gmail API** for your project.
- Create OAuth 2.0 credentials for a **Desktop app**.
- Download the credentials JSON file and save it as `credentials.json` in the root of this project directory.

### 3. Gemini API Key
This project uses the Gemini API to classify emails. You'll need to get a free API key from Google AI Studio.

1.  Go to [Google AI Studio](https://aistudio.google.com/app/apikey) and create an API key.
2.  Export the API key as an environment variable in your terminal. This keeps your key secure and out of the source code.

    -   **For Linux/macOS:**
        ```bash
        export GEMINI_API_KEY="YOUR_API_KEY"
        ```
    -   **For Windows (Command Prompt):**
        ```bash
        set GEMINI_API_KEY="YOUR_API_KEY"
        ```
    -   **For Windows (PowerShell):**
        ```powershell
        $env:GEMINI_API_KEY="YOUR_API_KEY"
        ```

    Replace `"YOUR_API_KEY"` with the actual key you obtained.

### 4. Installation
Clone the repository and install the required Python packages:
```bash
git clone <your-repo-url>
cd <your-repo-name>
pip install -r requirements.txt
```

## Usage

Run the main script from your terminal:
```bash
python3 main.py
```

- **First Run**: The script will open a new browser window for you to log in to your Google account and authorize the application. After authorization, a `token.json` file will be created to store your credentials for future runs.
- **Database**: The script will create an `emails.db` file to store email data. If the database already exists, you'll be prompted to either start fresh or continue with the existing data.
- **Follow the Prompts**: The script will guide you through the process of classifying emails, moving them, and handling unsubscribe links.

## Files in this Project

- `main.py`: The main entry point of the application.
- `connectGmail.py`: Handles the connection and authentication with the Gmail API.
- `CreateDb.py`: Creates the initial SQLite database and table.
- `StoreMail.py`: Fetches emails from Gmail and stores them in the database.
- `ClassifyMail.py`: Classifies emails using the **Gemini API**.
- `SortMail.py`: Sorts emails by creating labels and moving messages.
- `Unsubscribe.py`: Extracts and manages unsubscribe links.
- `requirements.txt`: A list of all the Python packages required to run the project.
- `credentials.json`: Your downloaded Google Cloud credentials (you must provide this).
- `token.json`: Automatically generated to store your access tokens.
- `emails.db`: The SQLite database where email data is stored.
