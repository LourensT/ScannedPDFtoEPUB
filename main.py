from typing import Tuple, Dict

from openai import OpenAI
import tiktoken
import pdf2image

import logging
import os
import json
import base64
import argparse


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def main(pdf_fp: str, output_fp: str, store_temp: bool = False, temp_dir: str = "temp/") -> None:
    """
    Convert a scanned PDF afile to text.
    """
    # set new logging file
    assert ".pdf" in pdf_fp, "The input file must be a PDF file."

    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    with open(output_fp, "w") as f:
        f.write("")

    # set logging
    filename_root = f"{pdf_fp.split('/')[-1].split('.')[0]}_to_{output_fp.split('/')[-1].split('.')[0]}"
    filename = f"{filename_root}"
    i = 0
    while os.path.exists(f"{filename}.log"):
        filename = f"{filename_root}_{i}"
        i += 1
    filename = f"{filename}.log"
    logging.basicConfig(filename=filename, level=logging.INFO)

    # convert the pdf to images
    images = pdf2image.convert_from_path(pdf_fp)

    # initialize the OCR object
    ocr = OCR()

    # initialize the context at the start
    context = {
        "book_title": "Unknown",
        "author": "Unknown",
        "current_chapter": "Unknown",
    }

    number_of_pages = len(images)
    logging.info(f"Number of pages: {number_of_pages}")

    for i, image in enumerate(images):
        print(f"Processing page {i + 1}/{number_of_pages}")
        image.save(f'{temp_dir}{i}.png', 'PNG')
        # TODO pass this directly instead of saving first
        markdown, context = ocr.process_page(f'{temp_dir}{i}.png', context)
        logging.info(f"Page {i + 1}/{number_of_pages} processed. Deduced context {context}")

        if markdown[0] == "#":
            markdown = "\n" + markdown
        markdown = "\n" + markdown

        with open(output_fp, "a") as f:
            f.write(markdown)

    sent, received, image_cost = ocr.cost_est()
    logging.info(f"Total cost: {sent + received + image_cost} USD")

    if not store_temp:
        for i in range(len(images)):
            os.remove(f"{temp_dir}{i}.png")

        # remove the temp directory
        os.rmdir(temp_dir)


class OCR:
    """
    Uses OpenAI API to convert the data to markdown format.
    """
    MODEL = 'gpt-4o'
    schema = {
        "type": "object",
        "title": "markdown and context",
        "additionalProperties": False,
        "required": ["markdown", "context_from_previous_pages"],
        "properties": {
            "markdown": {
                "type": "string",
                "description": "The markdown-formatted text"
            },
            "context_from_previous_pages": {
                "type": "object",
                "title": "context",
                "description": "Information about the position of the text in the document",
                "additionalProperties": False,
                "required": ["book_title", "author", "current_chapter"],
                "properties": {
                    "book_title": {
                        "type": "string",
                        "description": "The book title",
                    },
                    "author": {
                        "type": "string",
                        "description": "The author of the book",
                    },
                    "current_chapter": {
                        "type": "string",
                        "description": "The chapter title",
                    }
                }
            }
        }
    }

    def __init__(self):
        self.encoding = tiktoken.encoding_for_model(self.MODEL)

        self.tokens_sent = 0
        self.tokens_received = 0
        self.images_sent = 0

        self.client = OpenAI()

        # load the prompt instruction
        with open("img_instruction.txt", "r") as f:
            self.img_instruction = f.read()
        with open("txt_instruction.txt", "r") as f:
            self.txt_instruction = f.read()

    def process_page(self, scan_fp: str, context: dict) -> Tuple[str, Dict]:
        """
        Process a single page.

        :param scan_fp: The file path to the scanned image.
        """

        base64_image = encode_image(scan_fp)
        try:
            resp = self.with_gpt_ocr(base64_image, prev_page_content=context)
        except json.decoder.JSONDecodeError:
            logging.debug("Error in OpenAI response, possibly the content violates their content policy, using local OCR.")
            resp = self.with_local_ocr(scan_fp)

        markdown = resp["markdown"]
        context = resp["context_from_previous_pages"]
        context["ending_last_page"] = markdown[-min(len(markdown), 200):]

        return markdown, context

    def with_gpt_ocr(self, base64_img: str, prev_page_content: Dict[str, str]) -> Tuple[str, Dict]:
        """
        Format the data into markdown format using OpenAI API.

        :param base64_img: The base64 encoded image.
        :param prev_page_content: The context from previous pages.
        """
        messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.img_instruction},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_img}",
                            }
                        }
                    ],
                }
            ]

        if 'ending_last_page' in prev_page_content:
            messages[0]['content'].append({"type": "text", "text": f"The last page ended with: {prev_page_content.pop('ending_last_page')}"})

        messages[0]['content'].append({"type": "text", "text": f"context_from_previous_pages: {str(prev_page_content)}"})

        response = self.client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            n=1,
            temperature=0,
            messages=messages,
            response_format={"type": "json_schema", "json_schema": {"strict": True, "name": "markdown", "schema": self.schema}},
        )

        self.tokens_sent += response.usage.prompt_tokens
        self.tokens_received += response.usage.completion_tokens
        self.images_sent

        result = json.loads(response.choices[0].message.content)

        logging.info(f"with_gpt_ocr gave result: {result}")

        return result

    def with_local_ocr(self, scan_fp: str, prev_page_content: Dict[str, str]) -> Tuple[str, Dict]:
        """
        Format the data into markdown format using pytesseract, and error correction using OpenAI API.

        :param scan_fp: The file path to the scanned image.
        :param prev_page_content: The context from previous pages.

        :throws ImportError: If pytesseract is not installed.
        """
        try:
            import pytesseract
        except ImportError:
            raise ImportError("OpenAI refused OCR for a page. Please install pytesseract using `pip install pytesseract` to do the OCR locally.")

        block = pytesseract.image_to_string(scan_fp)

        messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.txt_instruction},
                        {
                            "type": "text",
                            "text": block,
                        }
                    ],
                }
            ]

        if 'ending_last_page' in prev_page_content:
            messages[0]['content'].append({"type": "text", "text": f"The last page ended with: {prev_page_content.pop('ending_last_page')}"})

        messages[0]['content'].append({"type": "text", "text": f"context_from_previous_pages: {str(prev_page_content)}"})

        response = self.client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            n=1,
            temperature=0,
            messages=messages,
            response_format={"type": "json_schema", "json_schema": {"strict": True, "name": "markdown", "schema": self.schema}},
        )

        self.tokens_sent += response.usage.prompt_tokens
        self.tokens_received += response.usage.completion_tokens

        try:
            result = json.loads(response.choices[0].message.content)
        except json.decoder.JSONDecodeError:
            logging.error("Error in OpenAI response, possibly the content violates their content policy, no error correction done.")
            result = {"markdown": block, "context_from_previous_pages": prev_page_content}

        logging.info(f"with_local_ocr gave result: {result}")

        return result

    def cost_est(self) -> Tuple[float, float, float]:
        # source: https://community.openai.com/t/proposal-introducing-an-api-endpoint-for-token-count-and-cost-estimation/664585
        # updated on 12 sept 2024

        # {model : [dollar_per_1m_sent_tokens, dollar_per_1m_received_tokens, price_per 1000 x 10000 picture ]}
        pricing = {
            "gpt-4o": [5, 15, 0.001913],
        }

        sent_cost = self.tokens_sent * pricing[self.MODEL][0] / 1_000_000
        received_cost = self.tokens_received * pricing[self.MODEL][1] / 1_000_000
        image_cost = self.images_sent * pricing[self.MODEL][2]

        return sent_cost, received_cost, image_cost


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert a scanned PDF file to text.')
    # input file
    parser.add_argument('pdf_fp', type=str, help='The scanned PDF file to convert to text.')
    # output file
    parser.add_argument('output_fp', type=str, help='The output file to save the text to.')

    # optional arguments
    # store temp, default false
    parser.add_argument('--store_temp', action='store_true', help='Store temporary files.')
    # different temp directory
    parser.add_argument('--temp_dir', type=str, help='The temporary directory to store the images.', default='temp/')

    args = parser.parse_args()
    main(args.pdf_fp, args.output_fp, store_temp=args.store_temp, temp_dir=args.temp_dir)
