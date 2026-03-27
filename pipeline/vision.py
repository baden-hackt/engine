import openai
import base64
import cv2
import numpy as np
from dotenv import load_dotenv


load_dotenv("../.env")

client = openai.OpenAI()


def estimate_fill_level(crop: np.ndarray) -> int | None:
    """
    Encode the crop as JPEG.
    Send it to GPT-4o's vision API.
    Parse the response as an integer.
    Return the integer if valid (0-100), otherwise return None.
    """
    _, buffer = cv2.imencode('.jpg', crop)
    image_b64 = base64.standard_b64encode(buffer).decode('utf-8')

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=16,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "This is a photo of a shelf compartment. It holds a maximum of 6 cans at full capacity. Count how many cans you see in the image. Calculate the fill percentage as (count / 6) * 100. If there are more than 6 cans, return 100. If the shelf is empty, return 0. Respond with ONLY a single integer number, nothing else."
                        }
                    ]
                }
            ]
        )

        text = response.choices[0].message.content.strip()
        value = int(text)

        if value < 0:
            value = 0
        if value > 100:
            value = 100

        return value

    except Exception as e:
        print(f"WARNING: Vision API error: {e}")
        return None
