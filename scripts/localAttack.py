import requests
import openai
from dotenv import load_dotenv
import os
import json
import numpy as np

# Load environment variables from .env file
load_dotenv()
# Get API keys from environment variables
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


# Function to query both smart contract source code and ABI from Etherscan
def get_smart_contract_data(contract_address: str):
    # Query source code and ABI from Etherscan in parallel
    source_code_url = f"https://api.etherscan.io/api?module=contract&action=getsourcecode&address={contract_address}&apikey={ETHERSCAN_API_KEY}"
    abi_url = f"https://api.etherscan.io/api?module=contract&action=getabi&address={contract_address}&apikey={ETHERSCAN_API_KEY}"

    source_code_response = requests.get(source_code_url)
    abi_response = requests.get(abi_url)
    
    if source_code_response.status_code == 200 and abi_response.status_code == 200:
        source_code_data = source_code_response.json()
        abi_data = abi_response.json()
        
        if source_code_data["status"] == "1" and abi_data["status"] == "1":  # Successful response
            contract_source_code = source_code_data["result"][0]["SourceCode"]
            contract_abi = abi_data["result"]
            return contract_source_code, contract_abi
        else:
            raise Exception(f"Error fetching contract data: {source_code_data['message']} or {abi_data['message']}")
    else:
        raise Exception(f"HTTP Error: {source_code_response.status_code} or {abi_response.status_code}")

# Function to calculate cosine similarity between two vectors
def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

# Function to find the top 3 relevant chunks from embeddings.json
def get_relevant_chunks(contract_code: str, contract_abi: str, embeddings_file: str = 'embeddings.json'):
    with open(embeddings_file, 'r', encoding='utf-8') as f:
        embeddings_data = json.load(f)
    
    # Create embeddings for the contract code and ABI
    combined_text = contract_code + contract_abi
    combined_embedding = create_embeddings(combined_text, OPENAI_API_KEY)
    
    # Calculate similarity with each chunk and sort by similarity
    similarities = []
    for data in embeddings_data:
        chunk_embedding = data['embedding']
        similarity = cosine_similarity(combined_embedding, chunk_embedding)
        similarities.append((similarity, data['file'], data['chunk_index'], chunk_embedding))
    
    # Sort by similarity in descending order and get top 3
    similarities.sort(reverse=True, key=lambda x: x[0])
    top_chunks = similarities[:3]
    
    return top_chunks

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

# Function to send smart contract code and ABI to GPT-4 API for analysis or processing
def query_gpt4(contract_code: str, contract_abi: str, relevant_chunks: list):
    relevant_texts = "\n\n".join([f"### Relevant Chunk {i+1}:\n{chunk[1]}" for i, chunk in enumerate(relevant_chunks)])
    print(relevant_texts)
    prompt = f"""
Analyze the following smart contract. Provide a detailed explanation of the contract's functionality, potential security issues, and its use cases.

### Relevant Context:
{relevant_texts}

### Smart Contract ABI:
{contract_abi}

### Smart Contract Source Code:
{contract_code}

"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response['choices'][0]['message']['content']

# Main function to fetch contract data (both code and ABI) and send them to GPT-4
def main(contract_address: str):
    try:
        # Step 1: Fetch smart contract code and ABI from Etherscan
        contract_code, contract_abi = get_smart_contract_data(contract_address)
        print("Smart contract data fetched successfully.")
        
        # Step 2: Get relevant chunks from embeddings.json
        relevant_chunks = get_relevant_chunks(contract_code, contract_abi)
        print("Relevant chunks fetched successfully.")
        
        # Step 3: Query GPT-4 with the smart contract code, ABI, and relevant chunks
        gpt4_response = query_gpt4(contract_code, contract_abi, relevant_chunks)
        print("GPT-4 Response:")
        print(gpt4_response)
        
    except Exception as e:
        print(f"Error: {str(e)}")

# Example usage
if __name__ == "__main__":
    contract_address = "0xfAbA6f8e4a5E8Ab82F62fe7C39859FA577269BE3"
    main(contract_address)