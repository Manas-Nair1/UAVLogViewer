# backend/app.py
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Dict, Any
import logging
import sqlite3
import os
import json

db_path = os.path.join(os.getenv('APPDATA'), 'uav_logs_temp.db')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    """Get a new database connection"""
    return sqlite3.connect(db_path)

def sanitize_table_name(name: str) -> str:
    """Sanitize table name for SQLite"""
    # Replace special characters with underscores
    sanitized = name.replace('[', '_').replace(']', '_').replace('-', '_')
    # Remove any other non-alphanumeric characters except underscores
    sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in sanitized)
    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = 'table_' + sanitized
    return sanitized

def create_table_for_message_type(message_type: str, message_list: Dict[str, Any]):
    """Create a table for the given message type with appropriate columns"""
    table_name = sanitize_table_name(message_type)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get all field names from messageList
        field_names = list(message_list.keys())
        
        # Create column definitions - all as REAL for numeric data
        columns = ['id INTEGER PRIMARY KEY AUTOINCREMENT']
        columns.extend([f'"{field}" REAL' for field in field_names])
        
        # Create table
        create_table_sql = f'''
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            {', '.join(columns)}
        )
        '''
        
        logger.info(f"Creating table: {table_name}")
        cursor.execute(create_table_sql)
        conn.commit()
        
        return table_name

def insert_data_into_table(table_name: str, message_list: Dict[str, Any]):
    """Insert data into the specified table"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get field names and their data
        field_names = list(message_list.keys())
        
        # Determine the number of records (assuming all fields have the same number of entries)
        if not field_names:
            return
            
        first_field = message_list[field_names[0]]
        if not isinstance(first_field, dict):
            return
            
        record_count = len(first_field)
        
        # Prepare insert statement
        placeholders = ', '.join(['?' for _ in field_names])
        field_names_quoted = ', '.join([f'"{field}"' for field in field_names])
        insert_sql = f'INSERT INTO "{table_name}" ({field_names_quoted}) VALUES ({placeholders})'
        
        # Prepare data for insertion
        records = []
        for i in range(record_count):
            record = []
            for field in field_names:
                value = message_list[field].get(str(i))
                record.append(value)
            records.append(record)
        
        # Insert all records
        cursor.executemany(insert_sql, records)
        conn.commit()
        
        logger.info(f"Inserted {len(records)} records into table {table_name}")

# In-memory storage for parsed data
parsed_data_store = {}

@app.post("/api/parsed-data")
async def receive_parsed_data(data: Dict[str, Any] = Body(...)):
    """Endpoint to receive parsed flight data from JS frontend"""
    logger.info("Received request to /api/parsed-data")
    logger.info(f"Request data keys: {data.keys()}")

    session_id = data.get("sessionId", "default")
    message_type = data.get("messageType", "unknown")
    message_list = data.get("messageList", {})

    # Log the message type
    logger.info(f"Message Type: {message_type}")
    if "messageList" in data:
        logger.info("Keys under 'messageList':")
        for key in message_list.keys():
            logger.info(f"- {key}")

    try:
        # Create table for this message type
        table_name = create_table_for_message_type(message_type, message_list)
        
        # Insert data into the table
        insert_data_into_table(table_name, message_list)
        
        # Also store in memory for backward compatibility
        if session_id not in parsed_data_store:
            parsed_data_store[session_id] = {"data": {}}
        
        parsed_data_store[session_id]["data"][message_type] = message_list
        
        logger.info(f"Successfully processed data for message type: {message_type}")
        
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        return {"status": "error", "message": f"Failed to process data: {str(e)}"}

    return {"status": "success", "message": "Data received and stored", "session_id": session_id, "table_name": table_name}

@app.get("/api/parsed-data/{session_id}")
async def get_parsed_data(session_id: str):
    """Endpoint to retrieve stored data for a session"""
    if session_id not in parsed_data_store:
        return {"status": "error", "message": f"No data found for session {session_id}"}
    
    # Return a summary instead of the full data which could be very large
    data = parsed_data_store[session_id].get("data", {})
    summary = {
        "session_id": session_id,
        "message_types": list(data.keys()),
        "message_counts": {k: len(v) for k, v in data.items() if isinstance(v, list)}
    }
    
    return {"status": "success", "summary": summary}

@app.get("/api/tables")
async def get_tables():
    """Endpoint to list all tables in the database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
        
        return {"status": "success", "tables": tables}
    except Exception as e:
        logger.error(f"Error getting tables: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/api/table/{table_name}")
async def get_table_data(table_name: str, limit: int = 100):
    """Endpoint to retrieve data from a specific table"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT * FROM "{table_name}" LIMIT ?', (limit,))
            rows = cursor.fetchall()
            
            # Get column names
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            columns = [row[1] for row in cursor.fetchall()]
            
            # Convert to list of dictionaries
            data = []
            for row in rows:
                data.append(dict(zip(columns, row)))
        
        return {"status": "success", "table": table_name, "data": data, "count": len(data)}
    except Exception as e:
        logger.error(f"Error getting table data: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"message": "UAV Logger Chatbot API is running"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)