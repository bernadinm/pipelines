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

        # Initialize with environment variables if available
        self.valves = self.Valves(
            **{
                "GROK_API_KEY": os.getenv("GROK_API_KEY", ""),
                "GROK_API_BASE_URL": os.getenv("GROK_API_BASE_URL", "https://api.x.ai/v1")
            }
        )

        # Get available models
        self.pipelines = self.get_grok_models()
        
        # Log initialization
        print(f"Initialized Grok pipeline with {len(self.pipelines)} models")

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
        # Default models to use if API call fails or no API key is provided
        default_models = [
            {"id": "grok-1", "name": "Grok-1"},
            {"id": "grok-1-mini", "name": "Grok-1 Mini"},
        ]
        
        # Check if we have an API key
        if not self.valves.GROK_API_KEY:
            print("No Grok API key provided, using default models")
            return default_models
        
        try:
            # Set up headers for API request
            headers = {
                "Authorization": f"Bearer {self.valves.GROK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # First try to get models from the API
            print(f"Fetching models from {self.valves.GROK_API_BASE_URL}/models")
            r = requests.get(
                f"{self.valves.GROK_API_BASE_URL}/models", 
                headers=headers,
                timeout=10  # Add timeout to prevent hanging
            )
            
            # Check if request was successful
            if r.status_code != 200:
                print(f"Failed to fetch models: {r.status_code} {r.reason}")
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
                return default_models
            
            # Parse the response
            models_data = r.json()
            
            # Check if we got a valid response with data
            if not isinstance(models_data, dict) or "data" not in models_data:
                print(f"Unexpected response format: {models_data}")
                return default_models
            
            # Filter for Grok models
            grok_models = []
            for model in models_data["data"]:
                model_id = model.get("id", "")
                if isinstance(model_id, str) and "grok" in model_id.lower():
                    grok_models.append({
                        "id": model_id,
                        "name": model.get("name", model_id)
                    })
            
            # If no Grok models found, use defaults
            if not grok_models:
                print("No Grok models found in API response, using defaults")
                return default_models
            
            # Sort models to have newest versions first (assuming version numbers in names)
            grok_models.sort(key=lambda x: x["id"], reverse=True)
            
            print(f"Found {len(grok_models)} Grok models: {[m['id'] for m in grok_models]}")
            return grok_models

        except Exception as e:
            print(f"Error fetching Grok models: {str(e)}")
            return default_models

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        """Process a chat completion request through the Grok API"""
        print(f"pipe:{__name__}")
        
        # Check if API key is provided
        if not self.valves.GROK_API_KEY:
            return "Error: No Grok API key provided. Please add your API key in the pipeline valves."
        
        # Extract just the model name without the pipeline prefix
        model_name = model_id.split(".")[-1] if "." in model_id else model_id
        print(f"Using model: {model_name}")
        
        # Set up headers
        headers = {
            "Authorization": f"Bearer {self.valves.GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Create a clean payload with only the fields Grok API expects
        payload = {
            "model": model_name,
            "messages": body.get("messages", []),
            "stream": body.get("stream", True),
        }
        
        # Add optional parameters if they exist in the body
        for param in ["temperature", "top_p", "max_tokens", "presence_penalty", "frequency_penalty"]:
            if param in body and body[param] is not None:
                payload[param] = body[param]
        
        # Validate messages format
        if not payload.get("messages"):
            return "Error: No messages provided in the request"
        
        for i, message in enumerate(payload["messages"]):
            if "role" not in message:
                print(f"Warning: Message {i} missing 'role' field")
                message["role"] = "user"  # Default to user role
            
            if "content" not in message:
                print(f"Warning: Message {i} missing 'content' field")
                message["content"] = ""  # Default to empty content
        
        print(f"Sending request to {self.valves.GROK_API_BASE_URL}/chat/completions")
        
        try:
            # Make the API request
            r = requests.post(
                url=f"{self.valves.GROK_API_BASE_URL}/chat/completions",
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
            
            # Return the response based on streaming preference
            if payload["stream"]:
                return r.iter_lines()
            else:
                return r.json()
                
        except requests.exceptions.Timeout:
            return "Error: Request to Grok API timed out. Please try again later."
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to Grok API. Please check your internet connection."
        except Exception as e:
            print(f"Exception in Grok API call: {str(e)}")
            return f"Error: {str(e)}"
