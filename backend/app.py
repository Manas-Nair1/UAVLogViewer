# backend/app.py
from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Dict, Any
import logging

from baseLLM import create_chat_completion
from dbManager import DatabaseManager

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

# Initialize database manager
db_manager = DatabaseManager()

# In-memory storage for parsed data
parsed_data_store = {}

# Track sessions to detect new uploads
session_counters = {}

# Pydantic models for request/response
class ChatMessage(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    status: str

@app.post("/api/parsed-data")
async def receive_parsed_data(data: Dict[str, Any] = Body(...)):
    """Endpoint to receive parsed flight data from JS frontend"""
    logger.info("Received request to /api/parsed-data")
    logger.info(f"Request data keys: {data.keys()}")

    session_id = data.get("sessionId", "default")
    message_type = data.get("messageType", "unknown")
    message_list = data.get("messageList", {})
    is_new_upload = data.get("isNewUpload", False)  # Flag from frontend for new file uploads

    # Log the message type
    logger.info(f"Message Type: {message_type}")
    if "messageList" in data:
        logger.info("Keys under 'messageList':")
        for key in message_list.keys():
            logger.info(f"- {key}")

    try:
        # Check if this is a new session or new upload
        if session_id not in session_counters:
            session_counters[session_id] = 0
            is_first_message = True
        else:
            is_first_message = False
        
        # Clear all tables on new upload or first message of new session
        if is_new_upload or is_first_message:
            logger.info("Clearing all existing tables for new upload")
            db_manager.clear_all_tables()
            # Clear in-memory store as well
            parsed_data_store.clear()
            session_counters[session_id] = 0
        
        session_counters[session_id] += 1
        
        # Create table for this message type (will replace if needed)
        table_name = db_manager.create_table_for_message_type(message_type, message_list, replace_existing=True)
        
        # Insert data into the table
        db_manager.insert_data_into_table(table_name, message_list)
        
        # Also store in memory for backward compatibility
        if session_id not in parsed_data_store:
            parsed_data_store[session_id] = {"data": {}}
        
        parsed_data_store[session_id]["data"][message_type] = message_list
        
        logger.info(f"Successfully processed data for message type: {message_type}")
        
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        return {"status": "error", "message": f"Failed to process data: {str(e)}"}

    return {"status": "success", "message": "Data received and stored", "session_id": session_id, "table_name": table_name}


@app.get("/api/tables")
async def get_tables():
    """Endpoint to list all tables in the database"""
    try:
        tables = db_manager.get_all_tables()
        return {"status": "success", "tables": tables}
    except Exception as e:
        logger.error(f"Error getting tables: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/api/table/{table_name}")
async def get_table_data(table_name: str, limit: int = 100):
    """Endpoint to retrieve data from a specific table"""
    try:
        columns, data = db_manager.get_table_data(table_name, limit)
        return {"status": "success", "table": table_name, "data": data, "count": len(data)}
    except Exception as e:
        logger.error(f"Error getting table data: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.delete("/api/clear-database")
async def clear_database():
    """Endpoint to manually clear all data from the database"""
    try:
        db_manager.clear_all_tables()
        parsed_data_store.clear()
        session_counters.clear()
        return {"status": "success", "message": "Database cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing database: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/api/database-summary")
async def get_database_summary():
    """Endpoint to get a summary of the database structure"""
    try:
        tables = db_manager.get_all_tables()
        summary = {"tables": []}
        
        for table_name in tables:
            schema = db_manager.get_table_schema(table_name)
            row_count = db_manager.get_table_row_count(table_name)
            
            table_info = {
                "name": table_name,
                "row_count": row_count,
                "columns": schema
            }
            summary["tables"].append(table_info)
        
        return {"status": "success", "summary": summary}
    except Exception as e:
        logger.error(f"Error getting database summary: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"message": "UAV Logger Chatbot API is running"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
    
@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_llm(chat_request: ChatMessage):
    """Endpoint to chat with the LLM about flight data"""
    try:
        logger.info(f"Received chat message: {chat_request.message}")
        
        # Get database context to provide to the LLM
        context_info = ""
        try:
            tables = db_manager.get_all_tables()
            if tables:
                context_info = f"\nAvailable flight data tables: {', '.join(tables)}\n"
                
                # Get summary of data
                summary = await get_database_summary()
                if summary.get("status") == "success":
                    table_summaries = []
                    for table in summary["summary"]["tables"]:
                        table_summaries.append(f"- {table['name']}: {table['row_count']} rows")
                    context_info += "Data summary:\n" + "\n".join(table_summaries)
        except Exception as e:
            logger.warning(f"Could not get database context: {e}")
        
        # Enhance the user message with context
        enhanced_message = f"""You are an assistant helping analyze UAV/drone flight log data. 
        
{context_info}

User question: {chat_request.message}

Please provide helpful analysis or insights about the flight data. If the user asks about specific data, let them know what tables are available."""

        # Get response from LLM
        response = create_chat_completion(enhanced_message)
        
        logger.info("Successfully generated LLM response")
        return ChatResponse(response=response, status="success")
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.post("/api/chat/clear")
async def clear_chat_history():
    """Endpoint to clear chat history"""
    try:
        # Import and clear the messages list from baseLLM
        from baseLLM import messages
        messages.clear()
        
        return {"status": "success", "message": "Chat history cleared"}
    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/api/chat/context")
async def get_chat_context():
    """Endpoint to get current database context for chat"""
    try:
        tables = db_manager.get_all_tables()
        context = {
            "available_tables": tables,
            "table_summaries": []
        }
        
        for table_name in tables:
            try:
                row_count = db_manager.get_table_row_count(table_name)
                schema = db_manager.get_table_schema(table_name)
                context["table_summaries"].append({
                    "name": table_name,
                    "row_count": row_count,
                    "columns": [col["name"] for col in schema]
                })
            except Exception as e:
                logger.warning(f"Could not get info for table {table_name}: {e}")
        
        return {"status": "success", "context": context}
    except Exception as e:
        logger.error(f"Error getting chat context: {str(e)}")
        return {"status": "error", "message": str(e)}


# filepath: c:\Users\Admin\Documents\GitHub\cvcBackup\UAVLogViewer\backend\app.py
@app.get("/")
async def root():
    return {"message": "UAV Logger Chatbot API is running"}