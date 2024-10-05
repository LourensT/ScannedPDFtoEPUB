from openai import OpenAI
import base64
import json
import os


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def OCR(base64_img, prev_page_content, curr_try=1, temp=0):

    client = OpenAI()

    instruction = """ This is a page of a photoscanned book. Your task is to format the text as markdown.
Format chapter titles as H1 (`#`), and paragraph titles as H2 (`##`). If you encounter an image, add a description as such <image showing: >, and the caption.
You also have access to context from previous pages, such as the book title, author, current chapter, and the last sentence of the previous page.
Use this to deduct when text at the top or the bottom of the page is repetition of the title, author, or chapter, so you can omit it.
Note this common mistake: if the title/author/chapter title is on the top of the page, you should not include it in the output as a header.
Just ignore it, unless it is the cover page or the first page of the chapter.
DO NOT include the title of the chapter of the chapter as a header, UNLESS it is part of the text in the image.
Also disregard page numbers. In your output, also include the previous context for the next page, updated with information from this page."""

    messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": instruction},
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

    # https://platform.openai.com/docs/guides/structured-outputs
    # structured format

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

    response = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        n=1,
        temperature=temp,
        messages=messages,
        response_format={"type": "json_schema", "json_schema": {"strict": True, "name": "markdown", "schema": schema}},
    )

    try:
        # result = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
        result = json.loads(response.choices[0].message.content)
    except Exception as e:
        # logging.error(f"Error in OpenAI response: {e}, try {curr_try}")
        # if error is json decode error
        print(response, e)
        if curr_try < 3:
            if e == json.decoder.JSONDecodeError:
                return OCR(base64_img, prev_page_content, curr_try + 1, temp=temp + 0.1)
            else:
                return OCR(base64_img, prev_page_content, curr_try + 1)
        else:
            print(response)
            raise ValueError("Error in OpenAI response")

    # logging.info(f"RESPONSE: {result}")

    return result


if __name__ == '__main__':
    # append the output to a file
    fp = "output2.md"
    # if not exist, creat it
    if not os.path.exists(fp):
        with open(fp, "w") as f:
            f.write("")

    files = os.listdir("temp")
    i = 0
    context = {
        "book_title": "Unknown",
        "author": "Unknown",
        "current_chapter": "Unknown",
    }

    # %%
    # i = 107
    # context = {'book_title': 'Clandestine in Chile (1986)', 'author': 'Gabriel Garcia Marquez', 'current_chapter': 'Those Who Stayed Are Also Exiles', "ending_last_page": "as I looked\nat it again in the garden, I couldn’t be sure whether my\nmother had created that painstaking reconstruction so that I\nwould not miss my former home if I were to return one day,\nor whether it was left as is to remember me by, should I die\nin exile."}
    while f"{i}.png" in files:
        print(i, context)
        base64_image = encode_image("temp/" + f"{i}.png")
        resp = OCR(base64_image, prev_page_content=context)
        markdown = resp["markdown"]
        context = resp["context_from_previous_pages"]
        context["ending_last_page"] = markdown[-min(len(markdown), 200):]

        if markdown[0] == "#":
            markdown = "\n" + markdown
        markdown = "\n" + markdown
        
        with open(fp, "a") as f:
            f.write(markdown)

        i += 1
