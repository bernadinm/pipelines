from typing import List, Union, Generator, Iterator
from schemas import OpenAIChatMessage
from pydantic import BaseModel

import os
import requests


class Pipeline:
    class Valves(BaseModel):
        GROK_API_BASE_URL: str = "https://api.x.ai/v1"
        GROK_API_KEY: str = ""
        pass

    def __init__(self):
        self.type = "manifold"
        # Optionally, you can set the id and name of the pipeline.
        # Best practice is to not specify the id so that it can be automatically inferred from the filename, so that users can install multiple versions of the same pipeline.
        # The identifier must be unique across all pipelines.
        # The identifier must be an alphanumeric string that can include underscores or hyphens. It cannot contain spaces, special characters, slashes, or backslashes.
        # self.id = "grok_pipeline"
        self.name = "Grok: "

        self.valves = self.Valves(
            **{
                "GROK_API_KEY": os.getenv(
                    "GROK_API_KEY", "your-grok-api-key-here"
                )
            }
        )

        self.pipelines = self.get_grok_models()
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
        self.pipelines = self.get_grok_models()
        pass

    def get_grok_models(self):
        if self.valves.GROK_API_KEY:
            try:
                headers = {}
                headers["Authorization"] = f"Bearer {self.valves.GROK_API_KEY}"
                headers["Content-Type"] = "application/json"

                r = requests.get(
                    f"{self.valves.GROK_API_BASE_URL}/models", headers=headers
                )

                models = r.json()
                # Filter for Grok models and sort by version (newest first)
                grok_models = [
                    {
                        "id": model["id"],
                        "name": model["name"] if "name" in model else model["id"],
                    }
                    for model in models["data"]
                    if "grok" in model["id"].lower()
                ]
                
                # Sort models to have newest versions first
                grok_models.sort(key=lambda x: x["id"], reverse=True)
                
                return grok_models

            except Exception as e:
                print(f"Error: {e}")
                return [
                    {
                        "id": "grok-3",
                        "name": "grok-3",
                    },
                    {
                        "id": "grok-2",
                        "name": "grok-2",
                    },
                    {
                        "id": "grok-1",
                        "name": "grok-1",
                    },
                    {
                        "id": "grok-1-mini",
                        "name": "grok-1-mini",
                    },
                    {
                        "id": "error",
                        "name": "Could not fetch models from X.AI, please update the API Key in the valves.",
                    },
                ]
        else:
            return [
                {
                    "id": "grok-3",
                    "name": "grok-3",
                },
                {
                    "id": "grok-2",
                    "name": "grok-2",
                },
                {
                    "id": "grok-1",
                    "name": "grok-1",
                },
                {
                    "id": "grok-1-mini",
                    "name": "grok-1-mini",
                },
            ]

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        # This is where you can add your custom pipelines like RAG.
        print(f"pipe:{__name__}")

        print("Messages:", messages)
        print("User message:", user_message)
        print("Original body:", body)

        headers = {}
        headers["Authorization"] = f"Bearer {self.valves.GROK_API_KEY}"
        headers["Content-Type"] = "application/json"

        # Extract just the model name without the pipeline prefix
        model_name = model_id.split(".")[-1] if "." in model_id else model_id
        
        # Create a clean payload with only the fields Grok API expects
        payload = {
            "model": model_name,
            "messages": body.get("messages", []),
            "stream": body.get("stream", True),
            "temperature": body.get("temperature", 0.7),
            "max_tokens": body.get("max_tokens", 4096) if "max_tokens" in body else None,
            "top_p": body.get("top_p", 1.0) if "top_p" in body else None,
        }
        
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        # Remove fields that Grok API doesn't expect
        if "user" in payload:
            del payload["user"]
        if "chat_id" in payload:
            del payload["chat_id"]
        if "title" in payload:
            del payload["title"]

        # Ensure messages are in the correct format for Grok API
        if "messages" in payload and isinstance(payload["messages"], list):
            # Make sure each message has the required fields
            for message in payload["messages"]:
                if "role" not in message or "content" not in message:
                    print(f"Warning: Message missing required fields: {message}")

        print("Sending payload to Grok API:", payload)

        try:
            r = requests.post(
                url=f"{self.valves.GROK_API_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                stream=True,
            )

            # Print response status and headers for debugging
            print(f"Response status: {r.status_code}")
            print(f"Response headers: {r.headers}")

            if r.status_code != 200:
                error_detail = ""
                try:
                    error_detail = r.json()
                    print(f"Error response: {error_detail}")
                except:
                    try:
                        error_detail = r.text
                        print(f"Error text: {error_detail}")
                    except:
                        pass
                
                return f"Error: {r.status_code} {r.reason} for url: {r.url}. Details: {error_detail}"

            if body["stream"]:
                return r.iter_lines()
            else:
                return r.json()
        except Exception as e:
            print(f"Exception in Grok API call: {str(e)}")
            return f"Error: {str(e)}"
