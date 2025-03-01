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

        # Initialize with available models
        self.pipelines = self.get_perplexity_models()
        
        # Log initialization
        print(f"Initialized Perplexity pipeline with {len(self.pipelines)} models")

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
        # Refresh models when valves are updated
        self.pipelines = self.get_perplexity_models()
        pass
        
    def get_perplexity_models(self):
        """Fetch available models from Perplexity API or return defaults if unavailable"""
        # Default models to use if API call fails or no API key is provided
        default_models = [
            {"id": "sonar-deep-research", "name": "Sonar Deep Research (128k)"},
            {"id": "sonar-reasoning-pro", "name": "Sonar Reasoning Pro (128k)"},
            {"id": "sonar-reasoning", "name": "Sonar Reasoning (128k)"},
            {"id": "sonar-pro", "name": "Sonar Pro (200k)"},
            {"id": "sonar", "name": "Sonar (128k)"},
            {"id": "r1-1776", "name": "R1-1776 (128k)"}
        ]
        
        # Check if API key is provided
        if not self.valves.PERPLEXITY_API_KEY:
            print("No Perplexity API key provided, using default models")
            return default_models
        
        try:
            # Set up headers for API request
            headers = {
                "Authorization": f"Bearer {self.valves.PERPLEXITY_API_KEY}",
                "Content-Type": "application/json",
                "accept": "application/json"
            }
            
            # Try to get models from the API
            print(f"Fetching models from {self.valves.PERPLEXITY_API_BASE_URL}/models")
            r = requests.get(
                f"{self.valves.PERPLEXITY_API_BASE_URL}/models", 
                headers=headers,
                timeout=10  # Add timeout to prevent hanging
            )
            
            # Check if request was successful
            if r.status_code != 200:
                print(f"Failed to fetch models: {r.status_code} {r.reason}")
                return default_models
            
            # Parse the response
            models_data = r.json()
            
            # Check if we got a valid response with data
            if not isinstance(models_data, dict) or "data" not in models_data:
                print(f"Unexpected response format: {models_data}")
                return default_models
            
            # Format the models for the UI
            perplexity_models = []
            for model in models_data["data"]:
                model_id = model.get("id", "")
                model_name = model.get("name", model_id)
                
                # Add context window info if available
                context_window = model.get("context_window", None)
                if context_window:
                    context_size = f"({context_window//1000}k)" if context_window >= 1000 else f"({context_window})"
                    model_name = f"{model_name} {context_size}"
                
                perplexity_models.append({
                    "id": model_id,
                    "name": model_name
                })
            
            # If no models found, use defaults
            if not perplexity_models:
                print("No models found in API response, using defaults")
                return default_models
            
            # Sort models alphabetically
            perplexity_models.sort(key=lambda x: x["name"])
            
            print(f"Found {len(perplexity_models)} Perplexity models: {[m['id'] for m in perplexity_models]}")
            return perplexity_models

        except Exception as e:
            print(f"Error fetching Perplexity models: {str(e)}")
            return default_models

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        """Process a chat completion request through the Perplexity API"""
        print(f"pipe:{__name__}")
        
        # Check if API key is provided
        if not self.valves.PERPLEXITY_API_KEY:
            return "Error: No Perplexity API key provided. Please add your API key in the pipeline valves."
        
        # Extract just the model name without the pipeline prefix
        model_name = model_id.split(".")[-1] if "." in model_id else model_id
        print(f"Using model: {model_name}")
        
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
            "model": model_name,
            "messages": formatted_messages,
            "stream": body.get("stream", True),
            "return_citations": True,
            "return_images": True
        }
        
        # Add optional parameters if they exist in the body
        for param in ["temperature", "top_p", "max_tokens", "presence_penalty", "frequency_penalty"]:
            if param in body and body[param] is not None:
                payload[param] = body[param]

        if "user" in payload:
            del payload["user"]
        if "chat_id" in payload:
            del payload["chat_id"]
        if "title" in payload:
            del payload["title"]

        print(f"Payload to Perplexity API: {payload}")

        try:
            print(f"Sending request to {self.valves.PERPLEXITY_API_BASE_URL}/chat/completions")
            
            r = requests.post(
                url=f"{self.valves.PERPLEXITY_API_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                stream=True,
                timeout=60  # Add timeout to prevent hanging
            )
            
            # Handle non-200 responses
            if r.status_code != 200:
                error_message = f"Error: {r.status_code} {r.reason} for url: {r.url}"
                
                try:
                    error_detail = r.json()
                    print(f"Error response: {error_detail}")
                    if isinstance(error_detail, dict) and "error" in error_detail:
                        error_message += f". {error_detail['error'].get('message', '')}"
                except:
                    try:
                        error_detail = r.text
                        print(f"Error text: {error_detail}")
                        if error_detail:
                            error_message += f". Details: {error_detail}"
                    except:
                        pass
                
                return error_message

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
        except requests.exceptions.Timeout:
            return "Error: Request to Perplexity API timed out. Please try again later."
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to Perplexity API. Please check your internet connection."
        except Exception as e:
            print(f"Exception in Perplexity API call: {str(e)}")
            return f"Error: {str(e)}"


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
