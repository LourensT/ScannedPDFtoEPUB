from typing import List

import openai
import tiktoken
import logging

import json


class Formatter:
    """
    Uses OpenAI API to convert the data to markdown format.
    """
    MODEL = 'gpt-4o'
    INSTRUCTION = "The following file is the output of Optical Character Recognition of a scanned book. However, it is very messy. Your task is to format it as the markdown file format. Please remove page numbering. Also note that many books repeat the title/chapter and author on every page, and this might be erroneously repeated in the text. If so, do not mistake it for a header, and remove it! If there are mistaken characters in the text, do your best guess at error correcting. Please format the document with headers, with chapter titles as H1 (# Chapter), and paragraph titles as H2 (##). If you encounter an image caption, add a <missing image> tag before the caption."
    CONTEXT = 128_000
    BLOCK_SIZE = 1_000

    def __init__(self, data: List[str]):
        self.encoding = tiktoken.encoding_for_model(self.MODEL)
        self.TOKEN_SENT = 0
        self.TOKEN_RECEIVED = 0

        # chunk the data
        self.blocks, block_sizes = self.chunk_data(data)
        print(f"Number of blocks: {len(self.blocks)}")

        # print number of tokens in the data
        data_tokens = sum(block_sizes)
        instruction_tokens = len(self.encoding.encode(self.INSTRUCTION))
        est_sent = (len(self.blocks) * instruction_tokens) + data_tokens
        est_received = data_tokens
        cost_est = self.cost_est(est_sent, est_received)
        print(f"Estimated cost for {est_sent, est_received}: {cost_est[0]:.2f}$ sent, {cost_est[1]:.2f}$ received")

        if sum(cost_est) > 10:
            raise ValueError("Estimated cost is more than $10")

    def chunk_data(self, data: List[str]):
        """
        Split the data into chunks of at most self.BLOCK_SIZE tokens
        """
        # split self.data in blocsk of at most 100_000 tokens
        blocks = []
        blocks_sizes = []
        block = ""
        curr_block_size = 0
        print(f"Number of lines: {len(data)}")
        for line in data:
            line_size = len(self.encoding.encode(line))
            if curr_block_size + line_size > self.BLOCK_SIZE:
                blocks.append(block)
                blocks_sizes.append(curr_block_size)
                block = ""
                curr_block_size = 0

            block += line
            curr_block_size += line_size

        blocks.append(block)
        blocks_sizes.append(curr_block_size)

        return blocks, blocks_sizes

    def format_data(self, store_temp=False):
        """
        Format the data into markdown format
        """

        for (i, block) in enumerate(self.blocks):
            if block == "":
                print("Empty block")
                continue
            formatted = self.handle_block(block)
            if not formatted:
                raise ValueError("Error in OpenAI call")

            markdown = formatted["markdown"]
            if store_temp:
                print(i)
                with open("temp.md", "a") as f:
                    f.write(markdown)

        with open("temp.md", "r") as f:
            md = f.read()

        return md

    def handle_block(self, block: str, curr_try=1):
        """
        block: str
        """
        print("Handling block...")

        prompt = self.INSTRUCTION + f"\n```{block}```"

        messages = [
            {"role": "system", "content": "You are a diligent editor working on a book manuscript."},
            {"role": "user", "content": prompt},
        ]

        token_cost = sum([len(self.encoding.encode(m['content'])) for m in messages])
        if token_cost > self.CONTEXT:
            logging.error(f"Prompt too long: {token_cost} tokens")
            return None

        function_resp = [{
            "type": "function",
            "function": {
                "name": "submit_markdown",
                "description": "Submit markdown-formatted, error-corrected text",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "markdown": {
                            "type": "string",
                            "description": "The markdown-formatted, error-corrected text"
                            }
                        }
                    }
                }
            }
        ]

        logging.info(f"OpenAI call, with function calling, with prompt of {token_cost}.")
        response = openai.chat.completions.create(
            model=self.MODEL,
            messages=messages,
            temperature=0,
            n=1,
            tools=function_resp,
            tool_choice={"type": "function", "function": {"name": function_resp[0]['function']['name']}}
        )
        self.TOKEN_SENT += response.usage.prompt_tokens
        self.TOKEN_RECEIVED += response.usage.completion_tokens

        try:
            result = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
        except Exception as e:
            logging.error(f"Error in OpenAI response: {e}, try {curr_try}")
            print(response)
            if curr_try < 3:
                return self.handle_block(block, curr_try + 1)
            else:
                print(response)
                raise ValueError("Error in OpenAI response")

        logging.info(f"RESPONSE: {result}")

        return result

    def cost_est(self, sent, received):
        # source: https://community.openai.com/t/proposal-introducing-an-api-endpoint-for-token-count-and-cost-estimation/664585
        # updated on 12 sept 2024

        # {model : [dollar_per_1m_sent_tokens, dollar_per_1m_received_tokens]}
        pricing = {
            "gpt-4o": [5, 15],
            "gpt-4o-2024-08-06": [2.5, 10],
            "gpt-4o-2024-05-13": [5, 15],
            "gpt-4o-mini": [0.15, 0.6],
            "gpt-4o-mini-2024-07-18": [0.15, 0.6],
            "chatgpt-4o-latest": [5.00, 15.00],
            "gpt-4-turbo": [10.00, 30.00],
            "gpt-4-turbo-2024-04-09": [10.00, 30.00],
            "gpt-4": [30.00, 60.00],
            "gpt-4-32k": [60.00, 120.00],
            "gpt-4-0125-preview": [10.00, 30.00],
            "gpt-4-1106-preview": [10.00, 30.00],
            "gpt-4-vision-preview": [10.00, 30.00],
            "gpt-3.5-turbo-0125": [0.50, 1.50],
            "gpt-3.5-turbo-instruct": [1.50, 2.00],
            "gpt-3.5-turbo-1106": [1.00, 2.00],
            "gpt-3.5-turbo-0613": [1.50, 2.00],
            "gpt-3.5-turbo-16k-0613": [3.00, 4.00],
            "gpt-3.5-turbo-0301": [1.50, 2.00],
            "davinci-002": [2.00, 2.00],
            "babbage-002": [0.40, 0.40]
        }

        sent_cost = sent * pricing[self.MODEL][0] / 1_000_000
        received_cost = received * pricing[self.MODEL][1] / 1_000_000

        return sent_cost, received_cost


if __name__ == '__main__':
    # with open("tests/marquezsmall.txt", "r") as f:
    #     data = f.readlines()

    # save logging to file
    logging.basicConfig(filename='formatter.log', level=logging.INFO)

    data = []
    import os
    files = os.listdir("temp/")
    i = 0
    while f"{i}.txt" in files:
        with open(f"temp/{i}.txt", "r") as f:
            data.extend(f.readlines())
        i += 1

    formatter = Formatter(data)
    md = formatter.format_data(store_temp=True)
    # save
    with open("full.md", "w") as f:
        f.write(md)

