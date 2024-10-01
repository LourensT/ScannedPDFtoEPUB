import pdf2image
from PIL import Image
import pytesseract

from typing import List
import os

"""
Handles the Optical Character Recognition (OCR) of a scanned PDF file.
"""

class OCR:
    temp_dir = 'temp/'

    def __init__(self, pdf_file):
        self.pdf_file = pdf_file
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def convert_to_images(self, store_temp=False):
        self.images = pdf2image.convert_from_path(self.pdf_file)

        if store_temp:
            for i, image in enumerate(self.images):
                image.save(f'{self.temp_dir}{i}.png', 'PNG')

    def ocr_core(self, file):
        text = pytesseract.image_to_string(file)
        return text

    def get_pages(self, store_temp=False) -> List[str]:
        self.text = []
        for pg, img in enumerate(self.images):
            print(pg)
            txt = self.ocr_core(img)
            self.text.append(txt)
            if store_temp:
                # store text in a file
                with open(f'{self.temp_dir}{pg}.txt', 'w') as f:
                    f.write(txt)

        return self.text


if __name__ == '__main__':
    # import timing
    import time

    pdf = OCR('tests/marquez.pdf')

    start = time.time()
    pdf.convert_to_images()
    print(f'Convert to images: {(time.time() - start)}')
    # print(pdf.get_pages(store_temp=True))
    start = time.time()
    ou = pdf.get_pages()
    print(f'OCR: {(time.time() - start)}')
    # save ou to file
    with open('output.txt', 'w') as f:
        f.write('\n'.join(ou))