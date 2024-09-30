import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import openai
from dotenv import load_dotenv
import pdfplumber


load_dotenv()
# Setup OpenAI API Key
client = openai.OpenAI()

# load dataset
def load_data(file):
    return pd.read_csv(file)

# Load text from PDF
def load_pdf(file):
    with pdfplumber.open(file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    return text

# Function to extract the column name from the query
def extract_column(query, columns):
    for column in columns:
        if column.lower() in query.lower():
            return column
    return None

# function handle user data query
def handle_data_query(df, query):
    # Implement logic to handle user queries like "What is the average price?"
    if "average" in query.lower():
        column = extract_column(query, df.columns)  # Extract column to calculate average
        if column:
            return f"The average of {column} is {df[column].mean()}"
        else:
            return "I couldn't find a column to calculate the average."
    elif "max" in query.lower():
        column = extract_column(query, df.columns)  # Extract column to find maximum value
        if column:
            return f"The maximum of {column} is {df[column].max()}"
        else:
            return "I couldn't find a column to calculate the maximum."
    # Add other types of queries as needed
    return "I couldn't process your query."

# Function to generate analysis with OpenAI
def generate_analysis(prompt, df=None):
        if df is not None:
            response = handle_data_query(df, prompt)
            return response
        else:   
            response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ]
        )   
        return response.choices[0].message.content

# Function to create visualizations based on user input
def create_visualization(df, chart_type, column):
    if chart_type == 'Line Chart':
        st.line_chart(df[column])
    elif chart_type == 'Bar Chart':
        st.bar_chart(df[column])
    elif chart_type == 'Area Chart':
        st.area_chart(df[column])

# Streamlit App Title
st.title("AI Data Analysis & Visualization")

# Step 1: File Upload
uploaded_file = st.file_uploader("Upload your CSV file", type=['csv', 'pdf'])

if uploaded_file is not None:
    if uploaded_file.name.endswith('.csv'):
        # Read the CSV file
        df = pd.read_csv(uploaded_file)
        st.write("CSV file uploaded successfully!")
        st.dataframe(df.head())

        # Step 2: Visualization Options for CSV
        st.write("Select column and chart type for visualization:")
        column = st.selectbox("Select a column to visualize", df.columns)
        chart_type = st.selectbox("Select chart type", ['Line Chart', 'Bar Chart', 'Area Chart'])

        if st.button("Generate Chart"):
            create_visualization(df, chart_type, column)
        
        # Step 3: User Input for Analysis
        user_question = st.text_input("Ask your data analysis question")

        if user_question:
            analysis_response = generate_analysis(f"Analyze the following data:\n{df.head()}\n{user_question}")
            st.write("AI Analysis Response:")
            st.write(analysis_response)

    elif uploaded_file.name.endswith('.pdf'):
        # Read the PDF file and extract text
        pdf_text = load_pdf(uploaded_file)
        st.write("PDF file uploaded successfully!")
        st.write("Extracted Text from PDF:")
        st.write(pdf_text[:2000])  # Display first 2000 characters of the PDF text for context

        # Step 3: User Input for Analysis on PDF Text
        user_question = st.text_input("Ask a question about the PDF content")

        if user_question:
            analysis_response = generate_analysis(f"Analyze the following PDF text:\n{pdf_text[:2000]}\n{user_question}")
            st.write("AI Analysis Response:")
            st.write(analysis_response)
