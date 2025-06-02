import os
import logging
import re  # Import the regular expression module
from openai import OpenAI
from dotenv import load_dotenv
import tiktoken
from dbManager import DatabaseManager

db_manager = DatabaseManager()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)
analyst_hints = """
            use timestamps to cite any events or data points.
            General Flight Data Interpretation
            * Determine flight duration from first arming to final disarming.
            * Identify maximum and minimum values for altitude, temperature, voltage, and current.
            * Track flight phases: takeoff, climb, cruise, descent, landing.
            * Extract and summarize flight mode changes and the duration spent in each mode.
            * Interpret GPS quality using HDOP, VDOP, and satellite count metrics.
            * Use timestamps to correlate telemetry events and sequence of actions.

            Anomaly Detection Heuristics
            * Flag rapid changes in altitude (e.g., >10 meters per second).
            * Identify GPS anomalies: loss of fix, large position jumps, high HDOP/VDOP.
            * Detect RC signal loss: long gaps in RCIN data or failsafe mode triggers.
            * Highlight battery issues: sudden voltage drops >1V within a few seconds, high battery temperature (>60°C), large current spikes.
            * Monitor inconsistent motor behavior: high current draw with low throttle, RPM mismatch if available.
            * Detect mode instability: frequent or unexpected mode changes, especially to failsafe or RTL.
            * Identify log error messages such as GPS glitch, EKF variance, or barometer inconsistency.
            * Mark times when telemetry data appears to be missing, frozen, or invalid.

            Investigative Behavior Guidelines
            * When asked vague questions like “Are there any issues?”, provide a structured summary of potential anomalies and affected subsystems.
            * When asked follow-up questions, use prior conversation context (e.g., user previously focused on GPS or battery).
            * Ask clarifying questions if the user’s query is ambiguous or could relate to multiple subsystems.
            * Prioritize issues that would affect flight safety, such as power failures, GPS loss, or signal loss.
            * Support reasoning with relevant timestamps, value trends, and subsystem names.
            * Avoid binary judgments unless clearly supported by the data; instead, describe patterns or suggest likely causes.
            """

# Global conversation history
messages = []

def get_prompt(input_message):
    """Build conversation context with proper role alternation"""
    context = []
    
    # Add the new user message
    messages.append(input_message)
    
    # Build context with proper role alternation
    for index, message in enumerate(messages):
        if index % 2 == 0:
            context.append({"role": "user", "content": message})
        else:
            context.append({"role": "assistant", "content": message})
    
    return context

def create_chat_completion(input_message):
    """Create a chat completion using the OpenAI API and interact with the database recursively in steps."""
    try:
        # Define system instructions for the LLM
        system_instructions = (
            "You are an flight engineer assistant capable of interacting with a SQLite database containing flight data about a singular flight. "
            "Very important: If you need to query the database, you MUST respond with: 'query database: [SQL_QUERY]' or 'analyse: [PROMPT] [DATA_TO_ANALYZE]'."
            "never query the every row in a table"
            "assume user does not know the table names, column names, or data types. you must query the database using pragma table info to find out."
            "You either generate a SQL query, request analysis, or ask clarifying questions/respond to user. Never combine these in one response. "
            "You should break down complex questions into steps and validate each step with the user before proceeding. "
            "If the query is ambiguous or fails, ask clarifying questions before generating the SQL query."
            "When referring to table or column names in SQL queries, use double quotes (\") or no quotes at all. Never use backticks (`)."
        )

        # Get conversation context
        conversation_messages = get_prompt(input_message)
        
        # Add system instructions to the conversation context
        conversation_messages.insert(0, {"role": "system", "content": system_instructions})
        
        # Create completion using OpenAI API
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation_messages,
            max_tokens=1000,
            temperature=0.1
        )
        
        # Validate the API response structure
        if not completion or not completion.choices or len(completion.choices) == 0:
            logger.error("OpenAI API response is malformed or empty.")
            return "The OpenAI API response is malformed or empty. Please try again later."

        # Extract response content
        response_content = completion.choices[0].message.content
        logger.info(f"OpenAI API response: {response_content}")
        try:
            response_content = completion.choices[0].message.content
        except IndexError:
            logger.error("OpenAI API response 'choices' list is empty.")
            clarifying_question = "The OpenAI API response was missing expected content. Retrying the request."
            messages.append(clarifying_question)
            
            # Retry mechanism with a limit
            max_retries = 3
            for attempt in range(max_retries):
                logger.info(f"Attempt {attempt + 1}/{max_retries}: Retrying API call...")
                completion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=conversation_messages,
                    max_tokens=1000,
                    temperature=0.1
                )
                if completion and completion.choices and len(completion.choices) > 0:
                    response_content = completion.choices[0].message.content
                    logger.info(f"Retry successful. Response content: {response_content}")
                    break  # Exit the retry loop if successful
                else:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries}: API response is still malformed.")
            else:  # This else belongs to the for loop
                error_message = "The OpenAI API consistently returned malformed responses. Please check the API and try again later."
                logger.error(error_message)
                return error_message
        # Check if the response requires database interaction
        if "query database:" not in response_content.lower() and "analyse:" not in response_content.lower():
            # Try to detect SQL query and add the prefix
            sql_match = re.search(r"(SELECT\s[\s\S]*?FROM\s[\s\S]*?;)", response_content, re.IGNORECASE)
            if sql_match:
                sql_query = sql_match.group(1)
                response_content = f"query database: {sql_query}"
                logger.info(f"Detected SQL query and added prefix: {response_content}")
        
        if "query database:" in response_content.lower():
            # Extract SQL query from the response
            sql_query = response_content.split("query database:")[1].strip()
            
            try:
                # Validate and sanitize the query
                if ";" in sql_query and sql_query.count(";") > 1:
                    return "The query contains multiple statements. Please provide a single SQL statement."
                
                # Use DatabaseManager to execute the query
                db_results = db_manager.execute_query(sql_query)

                if not db_results:
                    clarifying_question = (
                        f"The query returned no results. Can you confirm the structure of the table "
                        f"or provide additional details about the data you are looking for?"
                    )
                    messages.append(clarifying_question)
                    
                    # Recursive call to proceed
                    analysis_prompt = f"The query returned no results. Re-evaluate the query or try a different approach."
                    return create_chat_completion(analysis_prompt)
                
                # Add database results to the conversation history
                messages.append(f"Database results: {db_results}")
                analysis_prompt = f"Analyze these database results and provide an answer to the user's original question: {db_results}"
                return create_chat_completion(analysis_prompt)
            
            except Exception as e:
                logger.error(messages[-1])
                
                # Ask clarifying questions
                clarifying_question = (
                    f"Can you clarify the structure of the table or provide additional details about the columns? The error was: {str(e)}"
                )
                
                # Add clarifying question to conversation history
                messages.append(clarifying_question)
                return clarifying_question
        
        if "analyse:" in response_content.lower():
            parts = response_content.split("analyse:")
            if len(parts) < 2:
                return "Invalid 'analyse:' format.  It should be 'analyse: [PROMPT] [DATA]'."

            prompt_and_data = parts[1].strip()
            
            # Further split the prompt and data
            split_index = prompt_and_data.find(' ')  # Find the first space to separate prompt and data
            if split_index == -1:
                return "Invalid 'analyse:' format.  It should be 'analyse: [PROMPT] [DATA]'."
            
            analyst_prompt = prompt_and_data[:split_index].strip()
            data_to_analyze = prompt_and_data[split_index:].strip()
            
            # Invoke the flight analyst agent
            flight_analyst_input = f"hints:{analyst_hints}.\n {analyst_prompt}\nData:\n{data_to_analyze}"
            analyst_response = create_chat_completion(flight_analyst_input)
            
            # Add the analyst's response to the conversation history
            messages.append(f"Flight analyst response: {analyst_response}")
            return analyst_response
            
        # Add response to conversation history
        messages.append(response_content)
        
        return response_content
        
    except Exception as e:
        logger.error(f"Error creating chat completion: {str(e)}")
        return f"OpenAI API error: {str(e)}"


def clear_conversation():
    """Clear the conversation history"""
    global messages
    messages = []

def get_conversation_history():
    """Get the current conversation history"""
    return messages.copy()

def get_conversation_context():
    """Get formatted conversation context for debugging"""
    context = []
    for index, message in enumerate(messages):
        role = "user" if index % 2 == 0 else "assistant"
        context.append({"role": role, "content": message})
    return context