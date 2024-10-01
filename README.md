# Scanned PDF to Epub with GPT
The idea is to convert a scanned PDF to an epub, and fix formatting using a LLM.

Project is currently in a stage where I use it for myself. The API costs are pretty bad, like a $1 per hundred pages. 

## Aproach
1. PDF -> images with pdf2image
    * Saves the images in `tempimages/`
2. OCR with pytesseract
3. Error correction and formatting with OpenAI API
    * Save (in markdown) as `book.txt`
4. Convert to Epub with Pandadoc
    * `pandoc book.txt -o book.epub`


## Install (linux/wsl, python3.10)
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
3. Set `.env` with `OPENAI_API_KEY=yourkey`

## Usage
Run the `run.sh` script with the path to the pdf as the first argument

`source run.sh path/to/pdf`

## To Do
- [ ] Restructure repo

- [ ] Progress bar
    - [ ] Parallelize OCR and OpenAI API.
- [ ] Improve chunk splitting
    - [ ] Currently chunks split at the line, should split at the page. 
    - [ ] Overlapping chunks, and how to handle them. 
- [ ] Better book metadata (author, title, etc)
    * You can use calibre for this too
- [ ] Image support

- [ ] Alternative "expensive" approach  which uses OpenAI API for all OCR. Will likely be a step function in performance.
    * How much more expensive is this really? Seems to be about 0.003 cents for a 1000x600 image. https://openai.com/api/pricing/
    * This would have many benefits:
        * Tables probably
        * Footnotes would work better
        * Equations probably