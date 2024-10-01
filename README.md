# Scanned PDF to Epub


## Aproach

1. PDF -> images with pdf2image
    * Saves the images in `tempimages/`
2. OCR with pytesseract
3. Error correction and formatting with OpenAI API
    * Save (in markdown) as `book.txt`
4. Convert to Epub with Pandadoc
    * `pandoc book.txt -o book.epub`


## Install (linux/wsl)
1. Make venv, and install pytesseract and other requirements

`python3 -m venv env`

`source env/bin/activate`

`pip install -r requirements.txt`
2. Install tesseract engine from https://tesseract-ocr.github.io/tessdoc/Installation.html

`sudo apt install tesseract-ocr`

`sudo apt install libtesseract-dev`

2. Install pandoc
    1. download the amd64 .deb from https://github.com/jgm/pandoc/releases/
    2. `sudo dpkg -i $DEB` where `$DEB` is the downloaded file
3. Set environemnt variable `OPENAI_API_KEY` to your OpenAI API key

## Later
- [ ] support non-scanned PDFs
- [ ] image support
- [ ] footnote support
- [ ] table support