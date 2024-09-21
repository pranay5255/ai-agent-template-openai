import os
import json
import openai
import markdown
import numpy as np
import requests
from pathlib import Path
from dotenv import load_dotenv

# Step 0: Load API keys from .env file
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')  # Load OpenAI API key

# Function to parse markdown files and split into chunks
def parse_markdown_files(folder_path, chunk_size=300):
    """
    Parse all markdown files in a folder and return their content as chunks.
    
    Parameters:
    - folder_path: Path to the folder containing markdown files.
    - chunk_size: Number of words per chunk for splitting large documents.

    Returns:
    - List of document chunks.
    """
    chunks = []
    for file_path in Path(folder_path).glob("*.md"):
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            plain_text = markdown.markdown(content)
            words = plain_text.split()
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                chunks.append({
                    "file": file_path.name,
                    "chunk_index": i // chunk_size,
                    "text": chunk
                })
    return chunks

# Function to create embeddings using OpenAI's API
def create_embeddings(text: str, api_key: str, model: str = 'text-embedding-ada-002') -> list:
    url = "https://api.openai.com/v1/embeddings"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "input": text,
        "model": model
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code != 200:
        raise Exception(f"Error {response.status_code}: {response.text}")
    
    # Return the embeddings from the response
    return response.json()['data'][0]['embedding']

# Function to create embeddings for markdown chunks
def create_embeddings_for_chunks(chunks, api_key):
    """
    Create embeddings for each chunk of markdown content using OpenAI embeddings API.
    
    Parameters:
    - chunks: List of dictionaries with chunked text data.
    - api_key: OpenAI API key.

    Returns:
    - List of embeddings and corresponding chunk metadata.
    """
    embeddings = []
    for chunk in chunks:
        embedding = create_embeddings(chunk['text'], api_key)
        embeddings.append({
            "file": chunk['file'],
            "chunk_index": chunk['chunk_index'],
            "embedding": embedding,
            "text": chunk['text']  # Storing the text for future reference
        })
    return embeddings

# Function to save embeddings to a file (JSON format)
def save_embeddings_to_file(embeddings, output_file):
    """
    Save the embeddings to a JSON file.
    
    Parameters:
    - embeddings: List of embeddings with metadata.
    - output_file: File path to save the embeddings.
    """
    with open(output_file, 'w') as f:
        json.dump(embeddings, f)

# Main execution
if __name__ == "__main__":
    markdown_folder = "/home/pranay/Documents/ethglobal_singapore/LLMexperiments_ethglobal/ai-agent-template-openai/cyfrin-audit-reports/reports_md"  # Replace with your folder path
    output_file = "markdown_embeddings.json"  # Output file for embeddings

    # Step 1: Parse markdown files
    markdown_chunks = parse_markdown_files(markdown_folder)

    # Step 2: Create embeddings for markdown chunks
    markdown_embeddings = create_embeddings_for_chunks(markdown_chunks, openai.api_key)

    # Save the embeddings to a JSON file
    save_embeddings_to_file(markdown_embeddings, output_file)

    print(f"Embeddings saved to {output_file}")