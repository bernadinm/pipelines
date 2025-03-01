from typing import List, Union, Generator, Iterator
from pydantic import BaseModel
import os
import requests

from utils.pipelines.main import pop_system_message


class Pipeline:
    class Valves(BaseModel):
        PERPLEXITY_API_BASE_URL: str = "https://api.perplexity.ai"
        PERPLEXITY_API_KEY: str = ""
        pass

    def __init__(self):
        self.type = "manifold"
        self.name = "Perplexity: "

        self.valves = self.Valves(
            **{
                "PERPLEXITY_API_KEY": os.getenv(
                    "PERPLEXITY_API_KEY", "your-perplexity-api-key-here"
                )
            }
        )

        # Debugging: print the API key to ensure it's loaded
        print(f"Loaded API Key: {self.valves.PERPLEXITY_API_KEY}")

        # List of models
        self.pipelines = [
            {
                "id": "sonar-deep-research",
                "name": "Sonar Deep Research (128k)"
            },
            {
                "id": "sonar-reasoning-pro",
                "name": "Sonar Reasoning Pro (128k)"
            },
            {
                "id": "sonar-reasoning",
                "name": "Sonar Reasoning (128k)"
            },
            {
                "id": "sonar-pro",
                "name": "Sonar Pro (200k)"
            },
            {
                "id": "sonar",
                "name": "Sonar (128k)"
            },
            {
                "id": "r1-1776",
                "name": "R1-1776 (128k)"
            }
        ]
        pass

    async def on_startup(self):
        # This function is called when the server is started.
        print(f"on_startup:{__name__}")
        pass

    async def on_shutdown(self):
        # This function is called when the server is stopped.
        print(f"on_shutdown:{__name__}")
        pass

    async def on_valves_updated(self):
        # This function is called when the valves are updated.
        print(f"on_valves_updated:{__name__}")
        # No models to fetch, static setup
        pass

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        # This is where you can add your custom pipelines like RAG.
        print(f"pipe:{__name__}")

        system_message, messages = pop_system_message(messages)
        system_prompt = "You are a helpful assistant."
        if system_message is not None:
            system_prompt = system_message["content"]

        print(f"System prompt: {system_prompt}")
        print(f"Messages: {messages}")
        print(f"User message: {user_message}")

        headers = {
            "Authorization": f"Bearer {self.valves.PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
            "accept": "application/json"
        }

        # Format messages properly for Perplexity API
        formatted_messages = [{"role": "system", "content": system_prompt}]
        
        # Add all previous messages from the conversation history
        for msg in messages:
            formatted_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
            
        # Add the current user message if it's not empty and not already in messages
        if user_message and (not messages or messages[-1]["role"] != "user" or messages[-1]["content"] != user_message):
            formatted_messages.append({"role": "user", "content": user_message})
            
        payload = {
            "model": model_id,
            "messages": formatted_messages,
            "stream": body.get("stream", True),
            "return_citations": True,
            "return_images": True
        }

        if "user" in payload:
            del payload["user"]
        if "chat_id" in payload:
            del payload["chat_id"]
        if "title" in payload:
            del payload["title"]

        print(f"Payload to Perplexity API: {payload}")

        try:
            r = requests.post(
                url=f"{self.valves.PERPLEXITY_API_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                stream=True,
            )

            r.raise_for_status()

            if body.get("stream", False):
                return r.iter_lines()
            else:
                response = r.json()
                # Extract citations if they exist
                citations = []
                if "citations" in response:
                    citations = [
                        f'<a href="{citation["url"]}" target="_blank" rel="noopener noreferrer">{citation["title"]}</a>'
                        for citation in response["citations"]
                    ]
                
                # Format the response with citations
                content = response["choices"][0]["message"]["content"]
                if citations:
                    sources_html = "<br><br><b>Sources:</b><br>" + "<br>".join([f"• {citation}" for citation in citations])
                    content = f"{content}{sources_html}"

                formatted_response = {
                    "id": response["id"],
                    "model": response["model"],
                    "created": response["created"],
                    "usage": response["usage"],
                    "object": response["object"],
                    "choices": [
                        {
                            "index": choice["index"],
                            "finish_reason": choice["finish_reason"],
                            "message": {
                                "role": choice["message"]["role"],
                                "content": content
                            },
                            "delta": {"role": "assistant", "content": ""}
                        } for choice in response["choices"]
                    ]
                }
                return formatted_response
        except Exception as e:
            return f"Error: {e}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Perplexity API Client")
    parser.add_argument("--api-key", type=str, required=True,
                        help="API key for Perplexity")
    parser.add_argument("--prompt", type=str, required=True,
                        help="Prompt to send to the Perplexity API")

    args = parser.parse_args()

    pipeline = Pipeline()
    pipeline.valves.PERPLEXITY_API_KEY = args.api_key
    response = pipeline.pipe(
        user_message=args.prompt, model_id="sonar", messages=[], body={"stream": False})

    print("Response:", response)
