"""
title: Cloudflare AI Manifold Pipeline
author: open-webui
date: 2024-07-01
version: 1.0
license: MIT
description: A pipeline for generating text using the Cloudflare AI API.
requirements: requests
environment_variables: CLOUDFLARE_API_KEY, CLOUDFLARE_ACCOUNT_ID
"""

from typing import List, Union, Generator, Iterator
from schemas import OpenAIChatMessage
from pydantic import BaseModel
import os
import requests
import json

from utils.pipelines.main import pop_system_message


class Pipeline:
    class Valves(BaseModel):
        CLOUDFLARE_ACCOUNT_ID: str = ""
        CLOUDFLARE_API_KEY: str = ""

    def __init__(self):
        self.type = "manifold"
        self.id = "cloudflare"
        self.name = "Cloudflare AI: "
        
        self.valves = self.Valves(
            **{
                "CLOUDFLARE_ACCOUNT_ID": os.getenv(
                    "CLOUDFLARE_ACCOUNT_ID",
                    "",
                ),
                "CLOUDFLARE_API_KEY": os.getenv(
                    "CLOUDFLARE_API_KEY", 
                    ""
                ),
            }
        )
        
        self.base_url = "https://api.cloudflare.com/client/v4/accounts"
        self.update_headers()
        
        # Get models from API
        self.pipelines = self.get_cloudflare_models()
        print(f"Initialized with {len(self.pipelines)} models")

    def update_headers(self):
        self.headers = {
            'Authorization': f'Bearer {self.valves.CLOUDFLARE_API_KEY}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def get_cloudflare_models(self):
        """Get available models from Cloudflare AI API"""
        # Define a minimal set of models that we know work with Cloudflare
        fallback_models = [
            {"id": "@cf/meta/llama-3-8b-instruct", "name": "Llama 3 8B Instruct"},
            {"id": "@cf/mistral/mistral-7b-instruct-v0.1", "name": "Mistral 7B Instruct"},
        ]
        
        # Check if we have credentials
        if not self.valves.CLOUDFLARE_API_KEY or not self.valves.CLOUDFLARE_ACCOUNT_ID:
            print("No Cloudflare credentials provided, returning fallback models")
            return fallback_models
            
        print(f"Using Cloudflare Account ID: {self.valves.CLOUDFLARE_ACCOUNT_ID[:5]}...")
        
        try:
            # Try to get models from the API
            print(f"Fetching models from Cloudflare AI API")
            url = f"{self.base_url}/{self.valves.CLOUDFLARE_ACCOUNT_ID}/ai/models"
            print(f"Request URL: {url}")
            print(f"Request headers: {self.headers}")
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")
            
            if response.status_code != 200:
                print(f"Failed to fetch models: {response.status_code} {response.reason}")
                try:
                    error_data = response.json()
                    print(f"Error response: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Error text: {response.text}")
                return []
                
            data = response.json()
            print(f"Response data: {json.dumps(data, indent=2)}")
            
            if not data.get('success', False) or 'result' not in data:
                print(f"Unexpected response format: {data}")
                return []
                
            # Extract models from the response
            models = []
            result_data = data.get('result', [])
            print(f"Processing {len(result_data)} models from response")
            
            for model in result_data:
                model_id = model.get('id', '')
                capabilities = model.get('capabilities', {})
                
                # Check if model is a text generation model that can be used for chat
                is_text_model = False
                model_type = model.get('type', '').lower()
                
                # Models that can be used for chat completions
                if model_type in ['text-generation', 'chat-completions', 'text-to-text'] or 'chat' in model_type:
                    is_text_model = True
                
                print(f"Model: {model_id}, Type: {model_type}, Capabilities: {capabilities}")
                
                # Include all models that might work with chat completions
                if model_id and (is_text_model or 'chat_completions' in str(capabilities).lower()):
                    display_name = model.get('name', model_id)
                    
                    # Add model provider to name if available
                    provider = model.get('provider', '')
                    if provider and provider.lower() not in display_name.lower():
                        display_name = f"{display_name} ({provider})"
                    
                    models.append({
                        "id": model_id,
                        "name": display_name
                    })
                    print(f"Added model: {model_id} ({display_name})")
            
            # If no models found, return fallback models
            if not models:
                print("No chat completion models found in API response, using fallback models")
                return fallback_models
                
            # Sort models alphabetically
            models.sort(key=lambda x: x["name"])
            
            print(f"Found {len(models)} Cloudflare AI models")
            return models
            
        except Exception as e:
            print(f"Error fetching Cloudflare models: {str(e)}")
            return fallback_models

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
        self.update_headers()
        
        # Get models from API
        self.pipelines = self.get_cloudflare_models()
        print(f"Updated with {len(self.pipelines)} models")
        pass

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        """Process a chat completion request through the Cloudflare AI API"""
        print(f"pipe:{__name__}")
        
        # Check if credentials are provided
        if not self.valves.CLOUDFLARE_API_KEY:
            return "Error: No Cloudflare API key provided. Please add your API key in the pipeline valves."
        if not self.valves.CLOUDFLARE_ACCOUNT_ID:
            return "Error: No Cloudflare Account ID provided. Please add your Account ID in the pipeline valves."
        
        # Extract just the model name without the pipeline prefix
        model_name = model_id.split(".", 1)[-1] if "." in model_id else model_id
        print(f"Using model: {model_name}")
        
        # Verify the model exists in our list of models
        model_exists = False
        for model in self.pipelines:
            if model["id"] == model_name:
                model_exists = True
                break
                
        if not model_exists:
            return f"Error: Model '{model_name}' not found in available Cloudflare models. Please select a different model."
        
        # Create a clean payload with only the fields Cloudflare API expects for chat completions
        payload = {
            "model": model_name,
            "messages": body.get("messages", []),
            "stream": body.get("stream", True),
        }
        
        # Add optional parameters if they exist in the body
        for param in ["temperature", "top_p", "max_tokens", "presence_penalty", "frequency_penalty"]:
            if param in body and body[param] is not None:
                payload[param] = body[param]
        
        # Remove fields that Cloudflare API doesn't expect
        for key in ['user', 'chat_id', 'title']:
            if key in payload:
                del payload[key]
        
        # Validate messages format
        if not payload.get("messages"):
            return "Error: No messages provided in the request"
        
        # Cloudflare has two different endpoints we can try
        # First, try the v1 chat completions endpoint
        if model_name.startswith("@cf/"):
            # For models with @cf/ prefix, use the run endpoint
            model_id_for_url = model_name.replace("@cf/", "")
            url = f"{self.base_url}/{self.valves.CLOUDFLARE_ACCOUNT_ID}/ai/run/{model_id_for_url}"
            # Remove model from payload as it's in the URL
            if "model" in payload:
                del payload["model"]
        else:
            # For other models, use the chat completions endpoint
            url = f"{self.base_url}/{self.valves.CLOUDFLARE_ACCOUNT_ID}/ai/v1/chat/completions"
            # Keep model in payload
            payload["model"] = model_name
        
        print(f"Sending request to {url}")
        
        try:
            # Debug information
            print(f"Sending payload to Cloudflare API: {json.dumps(payload, indent=2)}")
            
            # Make the API request
            r = requests.post(
                url=url,
                json=payload,
                headers=self.headers,
                stream=True,
                timeout=60  # Add timeout to prevent hanging
            )
            
            print(f"Response status: {r.status_code}")
            print(f"Response headers: {r.headers}")
            
            # Handle non-200 responses
            if r.status_code != 200:
                error_message = f"Error: {r.status_code} {r.reason} for url: {r.url}"
                
                try:
                    error_detail = r.json()
                    print(f"Error response: {json.dumps(error_detail, indent=2)}")
                    
                    # Extract error message from different possible formats
                    if isinstance(error_detail, dict):
                        if "errors" in error_detail and error_detail["errors"]:
                            error_message += f". {error_detail['errors'][0]['message'] if error_detail['errors'] else ''}"
                        elif "error" in error_detail:
                            if isinstance(error_detail["error"], dict) and "message" in error_detail["error"]:
                                error_message += f". {error_detail['error']['message']}"
                            else:
                                error_message += f". {error_detail['error']}"
                except:
                    try:
                        error_detail = r.text
                        print(f"Error text: {error_detail}")
                        if error_detail:
                            error_message += f". Details: {error_detail}"
                    except:
                        pass
                
                # Add troubleshooting information
                error_message += "\n\nTroubleshooting: Please check that your Cloudflare API key and Account ID are correct and have the necessary permissions."
                
                # If first attempt failed and we used the run endpoint, try the chat completions endpoint as fallback
                if url.endswith(f"/ai/run/{model_id_for_url}") and r.status_code in [400, 404]:
                    print(f"First attempt failed with {r.status_code}, trying chat completions endpoint as fallback")
                    fallback_url = f"{self.base_url}/{self.valves.CLOUDFLARE_ACCOUNT_ID}/ai/v1/chat/completions"
                    fallback_payload = dict(payload)
                    fallback_payload["model"] = model_name
                    
                    try:
                        print(f"Sending fallback request to {fallback_url}")
                        print(f"Fallback payload: {json.dumps(fallback_payload, indent=2)}")
                        
                        r_fallback = requests.post(
                            url=fallback_url,
                            json=fallback_payload,
                            headers=self.headers,
                            stream=True,
                            timeout=60
                        )
                        
                        print(f"Fallback response status: {r_fallback.status_code}")
                        
                        if r_fallback.status_code == 200:
                            print("Fallback request succeeded")
                            r = r_fallback  # Use the successful response
                            # Continue with normal processing below
                            if fallback_payload["stream"]:
                                return r.iter_lines()
                            else:
                                return r.json()
                    except Exception as fallback_e:
                        print(f"Fallback request failed: {str(fallback_e)}")
                        # Continue with original error
                
                return error_message
            
            # Return the response based on streaming preference
            if payload["stream"]:
                return r.iter_lines()
            else:
                return r.json()
                
        except requests.exceptions.Timeout:
            return "Error: Request to Cloudflare AI API timed out. Please try again later."
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to Cloudflare AI API. Please check your internet connection."
        except Exception as e:
            print(f"Exception in Cloudflare AI API call: {str(e)}")
            return f"Error: {str(e)}"
