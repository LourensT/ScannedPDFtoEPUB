# Scanned PDF to Epub


## Aproach

1. OCR with pyTesseract

2. Error correction and formatting with OpenAI API
    3. Save (in markdown) as `book.txt`
3. Convert to Epub with Pandadoc
`pandoc book.txt -o book.epub`


Install (linux/wsl)
1. Make venv, and install tesseract and other requirements
`python3 -m venv env`
`source env/bin/activate`
`pip install -r requirements.txt`
2. Install pandoc
    1. download the amd64 .deb from https://github.com/jgm/pandoc/releases/
    2. `sudo dpkg -i $DEB` where `$DEB` is the downloaded file
3. Set environemnt variable `OPENAI_API_KEY` to your OpenAI API key


