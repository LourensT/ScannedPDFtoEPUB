from openai import OpenAI
import base64
import json
import os


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def OCR(image_path, prev_page_content, curr_try=1):
    base64_image = encode_image(image_path)

    client = OpenAI()

    function_resp = [{
        "type": "function",
        "function": {
            "name": "submit_markdown",
            "description": "Submit the markdown-formatted text",
            "parameters": {
                "type": "object",
                "properties": {
                    "markdown": {
                        "type": "string",
                        "description": "The markdown-formatted  text"
                    },
                    "context_from_previous_pages": {
                        "type": "object",
                        "description": "Information about the position of the text in the document",
                        "properties": {
                            "book_title" : {
                                "type": "string",
                                "description": "The book title"
                            },
                            "author": {
                                "type": "string",
                                "description": "The author of the book"
                            },
                            "current_chapter": {
                                "type": "string",
                                "description": "The chapter title"
                            },
                        }
                    }
                }
            }
        }
    }]

    instruction = """ This is an image of a scanned book. Your task is to format the text as Markdown.
Format chapter titles as H1 (`#`), and paragraph titles as H2 (`##`). If you encounter an image, add a description as such <image showing: >, and the caption.
You also have access to context from previous pages, such as the book title, author, current chapter, and current paragraph.
Use this to deduct when text at the top or the bottom of the page is repetition of the title, author, or chapter, so you can omit it.
Note this common mistake: if the title/author/chapter title is on the top of the page, you should not include it in the output as a header, but just ignore it, unless it is the cover page or the first page of the chapter.
Also disregard page numbers. In your output, also include the previous context for the next page, updated with information from this page, if necessary."""

    messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": instruction},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        }
                    },
                    {"type": "text", "text": f"context_from_previous_pages: {str(prev_page_content)}"}
                ],
            }
        ]

    response = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        n=1,
        temperature=0,
        messages=messages,
        response_format={"tupe": "json_schema", "json_schema" : {"strict": True, "schema": {}} }
        tools=function_resp,
        tool_choice={"type": "function", "function": {"name": function_resp[0]['function']['name']}}
    )

    try:
        result = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
    except Exception:
        # logging.error(f"Error in OpenAI response: {e}, try {curr_try}")
        print(response)
        if curr_try < 3:
            return OCR(image_path, prev_page_content, curr_try + 1)
        else:
            print(response)
            raise ValueError("Error in OpenAI response")

    # logging.info(f"RESPONSE: {result}")

    return result


if __name__ == '__main__':
    # append the output to a file
    fp = "output.md"
    # if not exist, creat it
    if not os.path.exists(fp):
        with open(fp, "w") as f:
            f.write("")

    files = os.listdir("temp")
    i = 0
    context = {
        "book_title" : "Unknown",
        "author": "Unknown",
        "current_chapter": "Unknown",
    }

    i = 38
    context = {'book_title': 'Clandestine in Chile (1986)', 'author': 'Gabriel Garcia Marquez', 'current_chapter': 'Those Who Stayed Are Also Exiles'}
    while f"{i}.png" in files:
        print(i, context)
        resp = OCR(f"temp/{i}.png", prev_page_content=context)
        markdown = resp["markdown"]
        context = resp["context_from_previous_pages"]

        markdown = "\n" + markdown

        with open(fp, "a") as f:
            f.write(markdown)

        i += 1
