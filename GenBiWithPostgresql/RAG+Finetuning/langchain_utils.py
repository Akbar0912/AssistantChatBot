import os
import ast
from decimal import Decimal
from dotenv import load_dotenv
import re
load_dotenv()

db_user = os.getenv("db_user")
db_password = os.getenv("db_password")
db_host = os.getenv("db_host")
db_name = os.getenv("db_name")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")

from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq 
from table_details import table_chain as select_table
from prompts import final_prompt, answer_prompt
import streamlit as st 

@st.cache_resource
def get_chain():
    print("creating chain")
    try:
        db = SQLDatabase.from_uri(f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}")
        print(f"✅ Database terhubung. Tables: {db.get_table_names()}")
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        raise e
    llm = ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.1-8b-instant",  # or "llama-3.1-8b-instant" for faster response
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )
    print("✅ Groq LLM siap")
    # llm = ChatOllama(model="llama3.2", temperature=0)
    # print("✅ LLM siap")
    
    generate_query = final_prompt | llm | StrOutputParser()
    
    def safe_execute_query(query_dict):
        """Safely execute query with better error handling"""
        query = query_dict.get("query", "")
        
        if not query or query.startswith("Error"):
            return "No valid SQL query"
            
        if not re.match(r'^(SELECT|INSERT|UPDATE|DELETE)\b', query, re.IGNORECASE):
            return "No valid SQL query"
        
        try:
            # Execute query with timeout protection
            result = execute_query.invoke({"query": query})
            print(f"Query executed successfully, result type: {type(result)}")
            
            # Log the raw result for debugging
            if isinstance(result, str) and len(result) > 500:
                print(f"Large string result (first 200 chars): {result[:200]}...")
            else:
                print(f"Query result: {result}")
                
            return result
        except Exception as e:
            error_msg = f"Error executing query: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg
    
    def log_query(input_dict):
        try:
            raw_output = generate_query.invoke(input_dict)
            print(f"Raw LLM output: {raw_output}")
            
            # Clean up the output first
            cleaned_output = raw_output.strip()
            
            # Check if it's a narrative response (non-SQL)
            non_sql_indicators = [
                "tidak cukup jelas",
                "adalah",
                "silakan",
                "pertanyaan",
                "maaf",
                "tidak dapat"
            ]
            
            if any(indicator.lower() in cleaned_output.lower() for indicator in non_sql_indicators):
                # Check if there's still a SQL query after the narrative
                sql_match = re.search(r'(SELECT|INSERT|UPDATE|DELETE)\b[\s\S]*?;', cleaned_output, re.IGNORECASE)
                if sql_match:
                    query = sql_match.group(0).strip()
                    if not query.endswith(';'):
                        query += ';'
                    print(f"Found SQL after narrative: {query}")
                    return query
                else:
                    print("ℹ️ Pure narrative response detected")
                    # return cleaned_output.split('\n')[0]  # Return first line of narrative
                    return cleaned_output  # Return first line of narrative
            
            # Extract SQL query if present
            sql_match = re.search(r'(SELECT|INSERT|UPDATE|DELETE)[\s\S]*?;', cleaned_output, re.IGNORECASE)
            if sql_match:
                query = sql_match.group(0).strip()
                if not query.endswith(';'):
                    query += ';'
                print(f"Cleaned query: {query}")
                print("✅ Valid SQL query extracted")
                return query
            else:
                # If no SQL found, return as narrative
                print(f"No SQL found, treating as narrative: {cleaned_output}")
                return cleaned_output
                
        except Exception as e:
            print(f"❌ Error in log_query: {str(e)}")
            return f"Error generating query: {str(e)}"
    
    print("✅ create_sql_query_chain berhasil")
    execute_query = QuerySQLDataBaseTool(db=db)
    print("✅ QuerySQLDataBaseTool siap")
    
    def format_result(input_dict):
        result = input_dict.get("result")
        query = input_dict.get("query", "")
        print(f"Input to format_result: query='{query}', result type: {type(result)}, result: {result}")

        # Handle query errors
        if query.startswith("Error"):
            return {"result_formatted": query, "data_for_chart": None}

        # Check if query is a narrative (non-SQL)
        if not query.strip() or not re.match(r'^(SELECT|INSERT|UPDATE|DELETE)\b', query, re.IGNORECASE):
            print("ℹ️ Returning non-SQL response")
            result_formatted = query if query else result
            return {"result_formatted": result_formatted, "data_for_chart": None}

        # Handle SQL execution errors
        if isinstance(result, str):
            if "Error" in result or "error" in result.lower():
                print(f"⚠️ Query execution error: {result}")
                return {"result_formatted": f"Terjadi kesalahan saat menjalankan query: {result}", "data_for_chart": None}

            try:
                # Clean up the string result
                cleaned_result = result.strip()
                print(f"Cleaning result string: {cleaned_result[:200]}...")  # Show first 200 chars

                # Method 1: Try direct ast.literal_eval for well-formed strings
                if cleaned_result.startswith('[') and cleaned_result.endswith(']'):
                    try:
                        # Replace Decimal objects with their string values before parsing
                        decimal_pattern = r"Decimal\('([^']+)'\)"
                        cleaned_result = re.sub(decimal_pattern, r"'\1'", cleaned_result)
                        print(f"After Decimal replacement: {cleaned_result[:200]}...")

                        parsed_result = ast.literal_eval(cleaned_result)
                        print(f"✅ Successfully parsed with ast.literal_eval: {type(parsed_result)}")
                        result = parsed_result
                    except (ValueError, SyntaxError, TypeError) as e:
                        print(f"⚠️ ast.literal_eval failed: {str(e)}")
                        raise e  # Let it fall through to alternative methods

                # Method 2: Manual parsing using regex for malformed strings
                if isinstance(result, str):  # Still a string, need manual parsing
                    print("🔧 Using manual parsing method")

                    # Enhanced regex to handle various formats
                    # Pattern to match: ('text', Decimal('123')) or ('text', 123) or just 'text'
                    tuple_pattern = r"\(([^)]+)\)"
                    tuple_matches = re.findall(tuple_pattern, result)

                    if tuple_matches:
                        parsed_rows = []
                        for match in tuple_matches:
                            # Split by comma and clean each value
                            values = []
                            # Handle quoted strings and Decimal values
                            value_pattern = r"'([^']*)'|Decimal\('([^']*)'\)|(\d+\.?\d*)"
                            value_matches = re.findall(value_pattern, match)

                            for value_match in value_matches:
                                # Take the first non-empty group
                                value = next((group for group in value_match if group), '')
                                if value:
                                    # Try to convert to appropriate type
                                    try:
                                        # Check if it's a number
                                        if '.' in value:
                                            values.append(float(value))
                                        elif value.isdigit():
                                            values.append(int(value))
                                        else:
                                            values.append(value)
                                    except ValueError:
                                        values.append(value)

                            if values:
                                parsed_rows.append(tuple(values) if len(values) > 1 else values[0])

                        if parsed_rows:
                            result = parsed_rows
                            print(f"✅ Manual parsing successful: {len(result)} rows")
                        else:
                            # Fallback: split by common delimiters
                            print("🔧 Using fallback parsing")
                            lines = result.replace('(', '').replace(')', '').split(',')
                            result = [[line.strip().strip("'\"") for line in lines if line.strip()]]
                    else:
                        # Last resort: treat as single value
                        result = [[cleaned_result.strip().strip("'\"()[]")]]
                        print(f"🔧 Fallback to single value: {result}")

            except Exception as e:
                print(f"❌ All parsing methods failed: {str(e)}")
                # Final fallback - create a simple structure
                result = [["Error parsing result", str(result)[:100]]]

        elif isinstance(result, (list, tuple)):
            print(f"Direct list/tuple result: {type(result)}, length: {len(result)}")
            # Ensure proper format for single row results
            if result and not isinstance(result[0], (list, tuple)):
                result = [result]
                print(f"Wrapped single row: {result}")

        # Additional cleanup for Decimal objects in the result
        if isinstance(result, (list, tuple)):
            cleaned_result = []
            for row in result:
                if isinstance(row, (list, tuple)):
                    cleaned_row = []
                    for item in row:
                        if isinstance(item, Decimal):
                            # Convert Decimal to appropriate type
                            if item % 1 == 0:
                                cleaned_row.append(int(item))
                            else:
                                cleaned_row.append(float(item))
                        else:
                            cleaned_row.append(item)
                    cleaned_result.append(tuple(cleaned_row) if isinstance(row, tuple) else cleaned_row)
                else:
                    # Handle single values
                    if isinstance(row, Decimal):
                        if row % 1 == 0:
                            cleaned_result.append([int(row)])
                        else:
                            cleaned_result.append([float(row)])
                    else:
                        cleaned_result.append([row])
            result = cleaned_result
            print(f"✅ Cleaned Decimal objects: {len(result)} rows")

        # Handle empty results
        if not result or (isinstance(result, (list, tuple)) and len(result) == 0):
            print("⚠️ No data found")
            return {"result_formatted": "Tidak ada data yang ditemukan untuk kriteria yang diberikan.", "data_for_chart": None}

        # Validate result format
        if not isinstance(result, (list, tuple)):
            print(f"❌ Invalid result type after processing: {type(result)}")
            return {"result_formatted": f"Format hasil tidak valid: {type(result)}", "data_for_chart": None}

        # Continue with column extraction and formatting...
        columns = []
        # Extract column names from query
        try:
            select_clause = re.search(r"SELECT\s+(.+?)\s+FROM", query, re.IGNORECASE | re.DOTALL)
            if select_clause:
                select_part = select_clause.group(1).strip()
                raw_columns = [col.strip() for col in select_part.split(',')]

                for col in raw_columns:
                    # Handle different SELECT patterns
                    if col.upper().startswith('COUNT('):
                        alias_match = re.search(r'\bAS\s+(\w+)', col, re.IGNORECASE)
                        columns.append(alias_match.group(1) if alias_match else 'count')
                    elif col.upper().startswith('SUM('):
                        alias_match = re.search(r'\bAS\s+(\w+)', col, re.IGNORECASE)
                        columns.append(alias_match.group(1) if alias_match else 'sum')
                    elif col.upper().startswith('MAX('):
                        alias_match = re.search(r'\bAS\s+(\w+)', col, re.IGNORECASE)
                        columns.append(alias_match.group(1) if alias_match else 'max')
                    elif col.upper().startswith('MIN('):
                        alias_match = re.search(r'\bAS\s+(\w+)', col, re.IGNORECASE)
                        columns.append(alias_match.group(1) if alias_match else 'min')
                    elif col.upper().startswith('AVG('):
                        alias_match = re.search(r'\bAS\s+(\w+)', col, re.IGNORECASE)
                        columns.append(alias_match.group(1) if alias_match else 'avg')
                    else:
                        # Check for AS alias first
                        alias_match = re.search(r'\bAS\s+(\w+)', col, re.IGNORECASE)
                        if alias_match:
                            columns.append(alias_match.group(1))
                        else:
                            # Clean column name
                            clean_col = col
                            if '.' in clean_col:
                                clean_col = clean_col.split('.')[-1]
                            clean_col = re.sub(r'[`"\']', '', clean_col).strip()
                            if clean_col:
                                columns.append(clean_col)

                print(f"✅ Extracted columns from query: {columns}")
            else:
                # Fallback column naming
                if result and len(result) > 0:
                    first_row = result[0]
                    if isinstance(first_row, (list, tuple)):
                        columns = [f"Column_{i+1}" for i in range(len(first_row))]
                    else:
                        columns = ["Value"]
                else:
                    columns = ["Value"]
                    print(f"⚠️ Used fallback column naming: {columns}")
        except Exception as e:
            print(f"⚠️ Error determining columns, using defaults: {str(e)}")
            try:
                if result and len(result) > 0:
                    first_row = result[0]
                    if isinstance(first_row, (list, tuple)):
                        columns = [f"Column_{i+1}" for i in range(len(first_row))]
                    else:
                        columns = ["Value"]
                else:
                    columns = ["Value"]
            except (TypeError, IndexError):
                columns = ["Value"]

        # Format results
        try:
            formatted = []
            data_for_chart = {"columns": columns, "rows": []}

            for row in result:
                # Ensure row is iterable
                if not isinstance(row, (list, tuple)):
                    row = [row]

                # Process each value in the row
                processed_row = []
                for val in row:
                    if isinstance(val, Decimal):
                        # Convert Decimal to appropriate format
                        if val % 1 == 0:
                            processed_row.append(int(val))
                        else:
                            processed_row.append(float(val))
                    elif val is None:
                        processed_row.append("NULL")
                    elif isinstance(val, str):
                        # Clean string values
                        cleaned_val = val.strip().strip("'\"()")
                        processed_row.append(cleaned_val)
                    else:
                        processed_row.append(val)

                # Adjust row length to match columns
                if len(processed_row) < len(columns):
                    processed_row.extend(["NULL"] * (len(columns) - len(processed_row)))
                elif len(processed_row) > len(columns):
                    # Add more column names if needed
                    for i in range(len(columns), len(processed_row)):
                        columns.append(f"Column_{i+1}")

                # Create formatted string
                row_str = ", ".join([f"{col}: {val}" for col, val in zip(columns, processed_row)])
                formatted.append(f"- {row_str}")

                # Add to chart data
                data_for_chart["rows"].append([str(val) for val in processed_row])

            # Update columns in data_for_chart
            data_for_chart["columns"] = columns
            result_formatted = "\n".join(formatted)

            print(f"✅ Formatted result: {len(data_for_chart['rows'])} rows, {len(data_for_chart['columns'])} columns")
            print(f"✅ Columns: {data_for_chart['columns']}")

        except Exception as e:
            print(f"❌ Error formatting result: {str(e)}")
            return {"result_formatted": f"Error memformat hasil: {str(e)}", "data_for_chart": None}

        print(f"✅ Formatted result with {len(data_for_chart['rows'])} rows")
        return {"result_formatted": result_formatted, "data_for_chart": data_for_chart}
    
    print("✅ Format result siap")
    
    chain = (
        RunnablePassthrough()
        .assign(table_names_to_use=select_table)
        .assign(query=log_query)
        .assign(result=safe_execute_query)
        .assign(result=lambda x: execute_query.invoke({"query": x["query"]}) if x["query"] and not x["query"].startswith("Error") and re.match(r'^(SELECT|INSERT|UPDATE|DELETE)\b', x["query"], re.IGNORECASE) else "No valid SQL query") 
        .assign(format_output=lambda x: format_result(x))
        .assign(
            result_formatted=lambda x: x["format_output"]["result_formatted"],
            data_for_chart=lambda x: x["format_output"]["data_for_chart"]
        )
    )
    print("✅ Chain final berhasil created")
    return chain
    
def create_history(messages):
    """Create chat history with better context management"""
    history = ChatMessageHistory()
    
    # Limit history to last 10 messages to avoid context overload
    recent_messages = messages[-10:] if len(messages) > 10 else messages
    
    for message in recent_messages:
        if message["role"] == "user":
            history.add_user_message(message["content"])
        elif message["role"] == "assistant":
            # Only add non-error assistant messages
            if not message["content"].startswith("Error"):
                history.add_ai_message(message["content"])
    
    return history

def get_relevant_context(question, messages, max_context_length=200):
    """Extract relevant context from recent messages"""
    if not messages:
        return ""
    
    # Look for relevant context in the last few user messages
    context_parts = []
    for msg in reversed(messages[-8:]):  # Check last 8 messages
        if msg["role"] == "user" and msg["content"] != question:
            # Enhanced context detection
            relevant_keywords = [
                "pelanggan", "customer", "negara", "country", "tersebut", "itu", "dia", "mereka",
                "produk", "product", "pembayaran", "payment", "pesanan", "order", "karyawan", "employee",
                "kantor", "office", "australia", "usa", "france", "germany", "kredit", "credit"
            ]
            
            # Check for pronoun references that need context
            pronouns = ["tersebut", "itu", "dia", "mereka", "ini", "atas", "di atas", "lebih dari"]
            needs_context = any(pronoun in question.lower() for pronoun in pronouns)
            
            if needs_context or any(keyword in msg["content"].lower() or keyword in question.lower() for keyword in relevant_keywords):
                context_parts.append(msg["content"])
                if len(" ".join(context_parts)) >= max_context_length:
                    break
    
    context = " ".join(context_parts[:50])  # Limit to 3 most recent relevant messages
    print(f"📝 Enhanced context extracted: '{context}'")
    return context

def invoke_chain(question, messages):
    print(f"🟠 Starting invoke_chain for question: {question}")
    try:
        chain = get_chain()
        history = create_history(messages)
        print(f"✅ Chat history created with {len(history.messages)} messages")
        
        # Get relevant context
        context = get_relevant_context(question, messages)
        print(f"📝 Context extracted: '{context}'")
        
        input_dict = {
            "question": str(question).strip(), 
            "context": context, 
            "top_k": 3, 
            "messages": history.messages
        }
        print(f"Input to chain.invoke: {input_dict}")
        
        # Get the complete response from chain
        chain_response = chain.invoke(input_dict)
        print(f"✅ Chain response keys: {list(chain_response.keys()) if isinstance(chain_response, dict) else 'Not a dict'}")
        
        # Store data_for_chart in session state if available
        if isinstance(chain_response, dict) and "data_for_chart" in chain_response:
            st.session_state["data_for_chart"] = chain_response["data_for_chart"]
            if chain_response["data_for_chart"] and chain_response["data_for_chart"].get("rows"):
                print(f"✅ Data for chart stored: {len(chain_response['data_for_chart']['rows'])} rows")
                print(f"✅ Column names: {chain_response['data_for_chart']['columns']}")
            else:
                print("ℹ️ No chart data available")
        
        # Format the final response
        if isinstance(chain_response, dict) and "result_formatted" in chain_response:
            if chain_response["result_formatted"].startswith("Error") or chain_response["result_formatted"].startswith("Terjadi kesalahan"):
                response = chain_response["result_formatted"]
            else:
                response = answer_prompt.format(result_formatted=chain_response["result_formatted"])
        else:
            response = str(chain_response)
            
        print(f"✅ Final response length: {len(response)} characters")
        return response
        
    except Exception as e:
        error_response = f"Maaf, terjadi kesalahan saat memproses pertanyaan Anda: {str(e)}"
        print(f"❌ Error in invoke_chain: {str(e)}")
        return error_response