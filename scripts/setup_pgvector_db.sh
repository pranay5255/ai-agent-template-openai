#!/bin/bash

# Variables
DB_NAME="auditVectors"
DB_USER="postgres"
DB_PASSWORD="pass"
DB_HOST="localhost"
DB_PORT="5432"
TABLE_NAME="markdown_embeddings"

# Drop the database if it exists
sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;"

# Drop the user if it exists
sudo -u postgres psql -c "DROP USER IF EXISTS $DB_USER;"

# Create the user with the necessary privileges using the postgres user
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "ALTER USER $DB_USER CREATEDB;"

# Create the database
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

# Connect to the database and create the pgvector extension and table
PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -h $DB_HOST -p $DB_PORT -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS vector;"
PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -h $DB_HOST -p $DB_PORT -d $DB_NAME -c "
CREATE TABLE IF NOT EXISTS markdown_embeddings (
    id SERIAL PRIMARY KEY,
    chunk_index INT,
    embedding VECTOR(1536) -- Adjust the dimension based on your embedding size
);"

# Print success message
echo "Database reset and setup completed successfully."