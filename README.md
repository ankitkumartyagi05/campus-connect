# 🎙️ Text To Speech App

> Convert text into natural-sounding speech with a simple Flask web app and browser interface.

## 🌐 Live Demo

[Open Live App](https://text-to-speach-rho.vercel.app/)

> Replace this placeholder with your deployed Vercel URL.

## ✨ Features

- 📝 Text input for instant speech generation
- 🎧 MP3 audio output
- 💾 Downloadable audio files
- ⚡ Fast browser-based interface
- 🛡️ Session limits and basic abuse protection
- ☁️ Ready for Vercel deployment

## 🧰 Tech Stack

- 🐍 Python
- 🌶️ Flask
- 🎤 gTTS
- 🧩 HTML, CSS, JavaScript
- 🚀 Vercel deployment support

## 📦 Installation

```bash
pip install -r requirements.txt
```

## 🚀 Run Locally

```bash
python app.py
```

Then open the app in your browser.

## 🖥️ How To Use

1. Open the homepage.
2. Type or paste the text you want to convert.
3. Enter a filename for the audio output.
4. Choose the language if your UI exposes that option.
5. Click the generate button.
6. Listen to the result or download the MP3 file.

## 🔁 App Flow

- The frontend sends your text to the backend.
- Flask validates the request and enforces session limits.
- gTTS generates the audio.
- The app returns a downloadable MP3 data URL.

## 🔌 API Endpoints

### `GET /`
Loads the web interface.

### `GET /session-status`
Returns the current session state and remaining generations.

### `POST /generate-audio`
Creates audio from the submitted text.

Example payload:

```json
{
  "text": "Hello world",
  "filename": "hello-world",
  "language": "en"
}
```

## ☁️ Deployment

This project is configured for Vercel using `api/index.py` as the Python entrypoint.

- `app.py` contains the Flask application.
- `api/index.py` exposes the app for serverless deployment.
- `vercel.json` routes all requests to the Python function.

## 🧪 Limits and Notes

- Maximum text length is limited by the backend.
- Each session has a generation limit.
- Session timeout is enforced server-side.
- Audio is cached in memory for repeated requests during runtime.

## 🗂️ Project Structure

```text
text-to-speech-app/
├── app.py
├── api/
│   └── index.py
├── templates/
│   ├── index.html
│   ├── scripts.js
│   └── style.css
├── generated_audio/
├── requirements.txt
├── vercel.json
└── README.md
```

## 📄 License

Copyright © Text To Speech App

All Rights Reserved.
