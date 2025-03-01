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
        self.pipelines = self.get_cloudflare_models()

    def update_headers(self):
        self.headers = {
            'Authorization': f'Bearer {self.valves.CLOUDFLARE_API_KEY}',
            'Content-Type': 'application/json'
        }

    def get_cloudflare_models(self):
        """Get available models from Cloudflare AI API or return defaults if unavailable"""
        # Default models to use if API call fails or no credentials are provided
        default_models = [
            {"id": "@cf/meta/llama-3.1-8b-instruct", "name": "Llama 3.1 8B Instruct"},
            {"id": "@cf/meta/llama-3.1-70b-instruct", "name": "Llama 3.1 70B Instruct"},
            {"id": "@cf/meta/llama-3-8b-instruct", "name": "Llama 3 8B Instruct"},
            {"id": "@cf/meta/llama-3-70b-instruct", "name": "Llama 3 70B Instruct"},
            {"id": "@cf/mistral/mistral-7b-instruct-v0.1", "name": "Mistral 7B Instruct"},
            {"id": "@cf/mistral/mistral-large-latest", "name": "Mistral Large"},
            {"id": "@cf/anthropic/claude-3-haiku-20240307", "name": "Claude 3 Haiku"},
            {"id": "@cf/anthropic/claude-3-sonnet-20240229", "name": "Claude 3 Sonnet"},
            {"id": "@cf/anthropic/claude-3-opus-20240229", "name": "Claude 3 Opus"},
        ]
        
        # Check if we have credentials
        if not self.valves.CLOUDFLARE_API_KEY or not self.valves.CLOUDFLARE_ACCOUNT_ID:
            print("No Cloudflare credentials provided, using default models")
            return default_models
        
        try:
            # Try to get models from the API
            print(f"Fetching models from Cloudflare AI API")
            url = f"{self.base_url}/{self.valves.CLOUDFLARE_ACCOUNT_ID}/ai/models"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                print(f"Failed to fetch models: {response.status_code} {response.reason}")
                return default_models
                
            data = response.json()
            
            if not data.get('success', False) or 'result' not in data:
                print(f"Unexpected response format: {data}")
                return default_models
                
            # Extract models from the response
            models = []
            for model in data['result']:
                model_id = model.get('id', '')
                if model_id and model.get('capabilities', {}).get('chat_completions', False):
                    display_name = model.get('name', model_id)
                    models.append({
                        "id": model_id,
                        "name": display_name
                    })
            
            # If no models found, use defaults
            if not models:
                print("No chat completion models found in API response, using defaults")
                return default_models
                
            # Sort models alphabetically
            models.sort(key=lambda x: x["name"])
            
            print(f"Found {len(models)} Cloudflare AI models")
            return models
            
        except Exception as e:
            print(f"Error fetching Cloudflare models: {str(e)}")
            return default_models

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
        self.pipelines = self.get_cloudflare_models()
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
        model_name = model_id.split(".")[-1] if "." in model_id else model_id
        print(f"Using model: {model_name}")
        
        # Create a clean payload with only the fields Cloudflare API expects
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
        
        url = f"{self.base_url}/{self.valves.CLOUDFLARE_ACCOUNT_ID}/ai/v1/chat/completions"
        print(f"Sending request to {url}")
        
        try:
            # Make the API request
            r = requests.post(
                url=url,
                json=payload,
                headers=self.headers,
                stream=True,
                timeout=60  # Add timeout to prevent hanging
            )
            
            # Handle non-200 responses
            if r.status_code != 200:
                error_message = f"Error: {r.status_code} {r.reason} for url: {r.url}"
                
                try:
                    error_detail = r.json()
                    print(f"Error response: {error_detail}")
                    if isinstance(error_detail, dict) and "errors" in error_detail:
                        error_message += f". {error_detail['errors'][0]['message'] if error_detail['errors'] else ''}"
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
            return "Error: Request to Cloudflare AI API timed out. Please try again later."
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to Cloudflare AI API. Please check your internet connection."
        except Exception as e:
            print(f"Exception in Cloudflare AI API call: {str(e)}")
            return f"Error: {str(e)}"
