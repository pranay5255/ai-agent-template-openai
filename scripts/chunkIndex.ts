const { readFileSync } = require('fs');
const OpenAI = require('openai');
const { Client } = require('pg');
require('dotenv/config');

// Function to read and split the content of a Markdown file into chunks of 2000 characters
function splitMarkdownFile(filePath: string, chunkSize: number = 2000): string[] {
    const data = readFileSync(filePath, 'utf-8');
    const chunks = [];
    for (let i = 0; i < data.length; i += chunkSize) {
        chunks.push(data.substring(i, i + chunkSize));
    }
    return chunks;
}

// Function to create embeddings using OpenAI API
async function createEmbeddings(text: string, apiKey: string): Promise<number[]> {
    const openai = new OpenAI({ apiKey });
    const response = await openai.embeddings.create({
        model: 'text-embedding-ada-002',
        input: text,
    });

    return response.data[0].embedding;
}

// Function to store embeddings in PostgreSQL with pgvector
// Function to store embeddings in PostgreSQL with pgvector
async function storeEmbeddings(client: InstanceType<typeof Client>, embeddings: number[], chunkIndex: number) {
    const query = `
        INSERT INTO markdown_embeddings (chunk_index, embedding)
        VALUES ($1, $2)
        ON CONFLICT (chunk_index) DO NOTHING;
    `;

    // Convert embeddings array into a string format PostgreSQL can interpret
    const formattedEmbeddings = `'{${embeddings.join(',')}}'`;  // Format the array

    const values = [chunkIndex, formattedEmbeddings];
    await client.query(query, values);
}


async function main() {
    const markdownFilePath = '/home/pranay/Documents/ethglobal_singapore/LLMexperiments_ethglobal/ai-agent-template-openai/cyfrin-audit-reports/reports_md/2023-03-13-beanstalk_wells_v0.1.md';
    const openaiApiKey = process.env.OPENAI_API_KEY;
    const pgClient = new Client({
        user: 'postgres',
        host: 'localhost',
        database: 'auditVectors',
        password: 'pass',
        port: 5432,
    });

    if (!openaiApiKey) {
        console.error('OpenAI API key is not set in the environment variables.');
        process.exit(1);
    }

    try {
        await pgClient.connect();

        const chunks = splitMarkdownFile(markdownFilePath);

        for (let i = 0; i < chunks.length; i++) {
            const chunkText = chunks[i];
            const embeddings = await createEmbeddings(chunkText, openaiApiKey);

            await storeEmbeddings(pgClient, embeddings, i);
        }
    } catch (error) {
        if (error instanceof Error) {
            console.error('Error:', error.message);
        } else {
            console.error('Unexpected error:', error);
        }
        process.exit(1);
    } finally {
        await pgClient.end();
    }
}

main().then(() => {
    console.log('Process completed successfully.');
}).catch(err => {
    console.error('Process failed:', err);
});