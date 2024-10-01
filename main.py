from OCR import OCR
from formatter import Formatter

import argparse

# CLI interface for converting pdf to epub
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert a scanned PDF file to text.')
    # input file
    parser.add_argument('pdf_fp', type=str, help='The scanned PDF file to convert to text.')
    # output file
    parser.add_argument('output_fp', type=str, help='The output file to save the text to.')

    # optional arguments
    # store temp, default false
    parser.add_argument('--store_temp', action='store_true', help='Store temporary files.')

    args = parser.parse_args()
    pdf = OCR(args.pdf_fp)

    pdf.convert_to_images(store_temp=args.store_temp)
    ou = pdf.get_pages(store_temp=args.store_temp)

    formatter = Formatter(ou)
    md = formatter.format_data()

    with open(args.output_fp, 'w') as f:
        f.write(md)
