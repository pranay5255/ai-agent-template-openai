import os
import json
import openai
import requests
import os
from openai import OpenAI
import numpy as np
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity

# Step 0: Load API keys from .env file
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')  # Load OpenAI API key
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')  # Load Etherscan API key
ETHERSCAN_BASE_URL = 'https://api.etherscan.io/api'


client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
)

# Function to load embeddings from a file (JSON format)
def load_embeddings_from_file(input_file):
    """
    Load embeddings from a JSON file.
    
    Parameters:
    - input_file: File path to load the embeddings from.

    Returns:
    - List of embeddings with metadata.
    """
    with open(input_file, 'r') as f:
        embeddings = json.load(f)
    # Convert embeddings from list to numpy array
    for embedding in embeddings:
        embedding['embedding'] = np.array(embedding['embedding'])
    return embeddings

# Function to retrieve smart contract source code from Etherscan
def get_smart_contract_source_code_and_abi(contract_address):
    """
    Retrieve the verified source code and ABI of a smart contract from Etherscan.
    
    Parameters:
    - contract_address: Address of the smart contract on Ethereum.

    Returns:
    - A tuple containing the source code and ABI of the contract.
    """
    url = f"{ETHERSCAN_BASE_URL}?module=contract&action=getsourcecode&address={contract_address}&apikey={ETHERSCAN_API_KEY}"
    response = requests.get(url)
    result = response.json()
    if result['status'] == '1' and result['message'] == 'OK':
        source_code = result['result'][0]['SourceCode']
        abi = result['result'][0]['ABI']
        return source_code, abi
    else:
        raise Exception("Error fetching smart contract source code and ABI from Etherscan: " + result['message'])


# Function to create embeddings using OpenAI's API
def create_embeddings(text: str, api_key: str, model: str = 'text-embedding-ada-002') -> list:
    url = "https://api.openai.com/v1/embeddings"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "input": text[:7000],
        "model": model
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code != 200:
        raise Exception(f"Error {response.status_code}: {response.text}")
    
    # Return the embeddings from the response
    return response.json()['data'][0]['embedding']

# Function to find the top k similar markdown chunks
def find_top_similar_chunks(source_code_embedding, markdown_embeddings, top_k=2):
    """
    Find the top k most similar markdown chunks based on cosine similarity.
    
    Parameters:
    - source_code_embedding: Embedding of the smart contract source code.
    - markdown_embeddings: List of markdown embeddings.
    - top_k: Number of top similar chunks to retrieve.

    Returns:
    - List of top k most similar markdown chunks (with file names and chunk indices).
    """
    similarities = []
    for chunk in markdown_embeddings:
        similarity = cosine_similarity([source_code_embedding], [chunk['embedding']])[0][0]
        similarities.append({
            "file": chunk['file'],
            "chunk_index": chunk['chunk_index'],
            "similarity": similarity,
            "text": chunk['text']
        })
    sorted_chunks = sorted(similarities, key=lambda x: x['similarity'], reverse=True)
    return sorted_chunks[:3]

# Function to create final prompt for the model
def create_final_prompt(query, top_chunks):
    """
    Create the final prompt by combining the input query with relevant text chunks.
    
    Parameters:
    - query: The user's input query.
    - top_chunks: List of top similar markdown chunks.

    Returns:
    - Final prompt string.
    """
    relevant_text = "\n\n".join([f"File: {chunk['file']} (Chunk {chunk['chunk_index']}):\n{chunk['text']}" for chunk in top_chunks])
    return f"{query}\n\nRelevant Information from Markdown Files:\n{relevant_text}"

# Function to generate response using OpenAI GPT model

def generate_response(prompt):
    """
    Generate a response using RedPill's language model based on the final prompt.
    
    Parameters:
    - prompt: The input prompt for the generative model.

    Returns:
    - Generated response from the model.
    """
    print("Prompt:\n", prompt)
    
    url = "https://api.red-pill.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer sk-QqGlrvZb8AkQunwXnmohAvWF2o5H8p4tOoLOWLwvXdMBOjK5"
    }
    data = {
        "model": "claude-3-5-sonnet-20240620",
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 1
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code != 200:
        raise Exception(f"Error {response.status_code}: {response.text}")
    
    return response.json()['choices'][0]['message']['content'].strip()


# Example usage of the RAG pipeline
if __name__ == "__main__":
    # Load precomputed markdown embeddings from the JSON file
    input_file = "markdown_embeddings.json"  # Replace with your path to the saved embeddings
    markdown_embeddings = load_embeddings_from_file(input_file)

    # Retrieve smart contract source code and ABI from Etherscan
    contract_address = '0xfAbA6f8e4a5E8Ab82F62fe7C39859FA577269BE3'  # Replace with the actual contract address
    source_code, abi = get_smart_contract_source_code_and_abi(contract_address)
    source_code_embedding = create_embeddings(source_code, openai.api_key)

    # Find top 3 similar markdown chunks
    top_chunks = find_top_similar_chunks(source_code_embedding, markdown_embeddings)

    # Create final prompt with relevant text and query
    query = """
    Act as an expert smart contract and Solidity developer and follow the steps mentioned:
    1. Explain the key features of the smart contract.
    2. List out its potential vulnerabilities in the contract.
    3. Use the ABI of the contract to interact with it.
    4. Use all of the above information to create a smart contract which can interact with the given contract.
    5. The output should only be solidity code which can be used to call the vulnerable functions in the given contract.
    6. The contract should be able to interact with the given contract whose source code is provided.
    7. The contract should be able to call the functions of the given contract.
    8. The deployed contract should automatically call the vulnerable functions of the given contract as soon as it is deployed.
    9. Output should only be solidity code.

    """
    final_prompt = create_final_prompt(query, top_chunks)
    final_prompt += f"\n\nSmart Contract ABI:\n{abi}"
    print("Final prompt:\n", final_prompt)

    # Generate response based on the final prompt
    response = generate_response(final_prompt)
    print("\nGenerated response:\n", response)