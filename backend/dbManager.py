import sqlite3
import os
import logging
from typing import Dict, Any, List, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database manager for UAV log data"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            self.db_path = os.path.join(os.getenv('APPDATA'), 'uav_logs.db')
        else:
            self.db_path = db_path
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    

    @staticmethod
    def sanitize_table_name(name: str) -> str:
        """Sanitize table name for SQLite"""
        # Replace special characters with underscores
        sanitized = name.replace('[', '_').replace(']', '_').replace('-', '_')
        # Remove any other non-alphanumeric characters except underscores
        sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in sanitized)
        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = "_" + sanitized
        return sanitized
    
    def clear_all_tables(self):
        """Clear all existing tables from the database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all table names
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Drop all tables
                for table in tables:
                    cursor.execute(f'DROP TABLE IF EXISTS "{table}"')
                    logger.info(f"Dropped table: {table}")
                
                conn.commit()
                logger.info("All tables cleared from database")
                
        except Exception as e:
            logger.error(f"Error clearing tables: {str(e)}")
            raise e
    
    def create_table_for_message_type(self, message_type: str, message_list: Dict[str, Any], replace_existing: bool = False) -> str:
        """Create a table for the given message type with appropriate columns"""
        table_name = self.sanitize_table_name(message_type)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Drop existing table if replace_existing is True
            if replace_existing:
                cursor.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                logger.info(f"Dropped existing table: {table_name}")
            
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
    
    def insert_data_into_table(self, table_name: str, message_list: Dict[str, Any]) -> None:
        """Insert data into the specified table"""
        with self.get_connection() as conn:
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
    
    def get_all_tables(self) -> List[str]:
        """Get list of all tables in the database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return [row[0] for row in cursor.fetchall()]
    
    def get_table_data(self, table_name: str, limit: int = 100) -> Tuple[List[str], List[Dict]]:
        """Get data from a specific table"""
        with self.get_connection() as conn:
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
            
            return columns, data
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema information for a table"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            columns = cursor.fetchall()
            return [{"name": col[1], "type": col[2], "nullable": not col[3]} for col in columns]
    
    def get_table_row_count(self, table_name: str) -> int:
        """Get row count for a table"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            return cursor.fetchone()[0]
        
    def execute_query(self, query: str) -> List[Tuple]:
        """Execute an arbitrary SQL query and return the results"""
        try:
            # Validate that the query contains only one statement
            if ";" in query.strip() and query.strip().count(";") > 1:
                raise ValueError("Only single SQL statements are allowed.")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                
                cursor.execute(query.strip())  # Execute the sanitized query
                results = cursor.fetchall()
                return results
        except sqlite3.Error as e:
            logger.error(f"SQLite error executing query: {query}, Error: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"Error executing query: {query}, Error: {str(e)}")
            raise e