
# import streamlit as st
# import pandas as pd
# import matplotlib.pyplot as plt
# import openai
# from dotenv import load_dotenv
# import pdfplumber
# import pydeck as pdk
# import re


# load_dotenv()
# # Setup OpenAI API Key
# client = openai.OpenAI()

# # load dataset
# def load_data(file):
#     encodings = ['utf-8', 'ISO-8859-1', 'windows-1252', 'utf-16']
#     for encoding in encodings:
#         try:
#             return pd.read_csv(file, encoding=encoding)
#         except UnicodeDecodeError:
#             continue
#     raise ValueError("Unable to decode the file with the given encodings.")

# # Load text from PDF
# def load_pdf(file):
#     with pdfplumber.open(file) as pdf:
#         text = ""
#         for page in pdf.pages:
#             page_text = page.extract_text()
#             if page_text:
#                 text += page_text
#     return text

# # Function to detect if user query asks for a chart
# def is_chart_query(query):
#     chart_keywords = ['line','line chart', 'bar', 'bar chart', 'area chart', 'area', 'grafik', 'map chart', 'map']
#     return any(keyword in query.lower() for keyword in chart_keywords)

# # Function to extract the column name from the query
# def extract_column(query, columns):
#     for column in columns:
#         if column.lower() in query.lower():
#             return column
#     return None

# # Function to detect chart type from query
# def detect_chart_type(query):
#     if 'line chart' in query.lower() or 'line' in query.lower():
#         return 'Line Chart'
#     elif 'bar chart' in query.lower() or 'bar' in query.lower():
#         return 'Bar Chart'
#     elif 'area chart' in query.lower() or 'area' in query.lower():
#         return 'Area Chart'
#     elif 'map chart' in query.lower() or 'peta' in query.lower() or 'lokasi' in query.lower():
#         return 'Map Chart'
#     return None  # Default behavior can be defined here

# # Function to handle chart query and automatically detect column
# def handle_chart_query(df, query):
#     chart_type = detect_chart_type(query)
#     column = extract_column(query, df.columns)  # Extract column from query
    
#     if column is None:  # If no column found, automatically choose the first numeric column
#         numeric_columns = df.select_dtypes(include=['number']).columns
#         if len(numeric_columns) > 0:
#             column = numeric_columns[0]  # Automatically select the first numeric column
#         else:
#             return "Error: No numeric columns found in the dataset for visualization."

#     if pd.api.types.is_numeric_dtype(df[column]):
#         create_visualization(df, chart_type, column)
#         return f"Displaying {chart_type} for {column}"
#     return "Could not find a relevant numeric column for the chart."

# # Function to check if user query is related to internal data
# def is_internal_query(user_input):
#     keywords = ['data', 'analisis', 'tahun', 'grafik', 'average', 'max', 'room type', 'count']
#     pattern = re.compile(r'\b(?:' + '|'.join(keywords) + r')\b', re.IGNORECASE)
#     return bool(pattern.search(user_input))

# # function handle user data query
# def handle_data_query(df, query):
#     # Implement logic to handle user queries like "What is the average price?"
#     if is_internal_query(query):
#         return generate_analysis(df, query)
#     else:
#         return generate_analysis(query)

# # Function to generate analysis with OpenAI
# def generate_analysis(prompt, df=None):
#     if df is not None:
#         # Cek apakah pertanyaan berkaitan dengan data dalam DataFrame
#         if is_chart_query(prompt):
#             response = handle_chart_query(df, prompt)
#             return response
#         else:
#             # Jika pertanyaan tidak terkait dengan data, gunakan OpenAI
#             response = client.chat.completions.create(
#                 model="gpt-3.5-turbo",
#                 messages=[
#                     {"role": "system", "content": "kamu adalah seorang assistan yang dapat menjawab segala pertanyaan dan memberikan solusi"},
#                     {"role": "user", "content": prompt},
#                 ]
#             )
#             return response.choices[0].message.content
#     else:
#         # Jika tidak ada DataFrame, langsung gunakan OpenAI
#         response = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "system", "content": "You are a helpful assistant."},
#                 {"role": "user", "content": prompt},
#             ]
#         )
#         return response.choices[0].message.content

# # Function to create visualizations based on user input
# def create_visualization(df, chart_type, column):
#     plt.figure(figsize=(10, 6))  # Mengatur ukuran grafik
#     if chart_type == 'Line Chart':
#         plt.plot(df[column], marker='o', linestyle='-', markersize=4)
#         plt.title(f'Line Chart of {column}')
#         plt.xlabel('Index')
#         plt.ylabel(column)
#         plt.grid(True)
#     elif chart_type == 'Bar Chart':
#         plt.bar(df.index, df[column], color='skyblue')
#         plt.title(f'Bar Chart of {column}')
#         plt.xlabel('Index')
#         plt.ylabel(column)
#         plt.xticks(rotation=45, ha='right')  # Rotasi label sumbu X
#     elif chart_type == 'Area Chart':
#         plt.fill_between(df.index, df[column], color='lightgreen', alpha=0.7)
#         plt.title(f'Area Chart of {column}')
#         plt.xlabel('Index')
#         plt.ylabel(column)
#         plt.grid(True)
#     elif chart_type == 'Map':
#         create_pydeck_visualization(df)
#     plt.tight_layout()  # Menghindari potongan label
#     st.pyplot(plt)
#     plt.close()

# # Function to create Pydeck visualization
# def create_pydeck_visualization(df):
#     if 'latitude' in df.columns and 'longitude' in df.columns:

#         layer = [
#             pdk.Layer(
#                 "HexagonLayer",
#                 df,
#                 get_position="[longitude, latitude]",
#                 radius=1000,
#                 elevation_scale=10,
#                 elevation_range=[0, 3000],
#                 pickable=True,
#                 extruded=True,
#                 auto_highlight=True,
#                 tooltip={"text": "{name}, {host_name}"},

#             ),
#             pdk.Layer(
#                 "ScatterplotLayer",
#                 df,
#                 get_position='[longitude, latitude]',
#                 get_color='[200, 30, 0, 160]',
#                 elevation_scale=51,
#                 get_radius=1000,
#                 pickable=True,
#                 # tooltip={"text": "{name}, {host_name}"},
#             )
#         ]

#         view_state = pdk.ViewState(
#             latitude=df['latitude'].mean(),
#             longitude=df['longitude'].mean(),
#             zoom=9,
#             pitch=50,
#         )

#         deck = pdk.Deck(
#             layers=layer, 
#             initial_view_state=view_state, 
#             # tooltip={"text": "{name}, {host_name}"},
#             tooltip={
#                     "html": "<b>Name:</b> {host_name}<br><b>Place:</b> {neighbourhood}<br>",
#                     "style": {"backgroundColor": "steelblue", "color": "white"}
#             },
#         )
        
#         st.pydeck_chart(deck)
        
#         # event = st.pydeck_chart(deck)
#         # event.selection
#     else:
#         st.error("Dataframe harus memiliki kolom 'latitude' dan 'longitude'.")

# # Streamlit App Title
# st.title("AI Data Analysis & Visualization")

# # Step 1: File Upload
# uploaded_file = st.file_uploader("Upload your CSV file", type=['csv', 'pdf'])

# if uploaded_file is not None:
#     if uploaded_file.name.endswith('.csv'):
#         # Read the CSV file
#         df = pd.read_csv(uploaded_file)
#         st.write("CSV file uploaded successfully!")
#         st.dataframe(df)
        
#         # Step 2: Map Button
#         if st.button('Generate Map Chart'):
#             st.session_state['map_generated'] = True
#             st.session_state['map_already_rendered'] = False
            
#         # Check if map was already generated in session state and display it
#         if st.session_state.get('map_generated'):
#             create_pydeck_visualization(df)

#         # Step 2: Visualization Options for CSV
#         user_chart = st.text_input("Ask your visualization chart")
        
#         if user_chart:
#             if is_chart_query(user_chart):
#                 # Handle chart query and visualize based on user question
#                 response = handle_chart_query(df, user_chart)
        
#                 if response:
#                     st.write(response)
        
#         # Step 3: User Input for Analysis
#         user_question = st.text_input("Ask your data analysis question")

#         if user_question:
#             analysis_response = generate_analysis(f"Analyze the following data:\n{df.head()}\n{user_question}")
#             st.write("AI Analysis Response:")
#             st.write(analysis_response)

#     elif uploaded_file.name.endswith('.pdf'):
#         # Read the PDF file and extract text
#         pdf_text = load_pdf(uploaded_file)
#         st.write("PDF file uploaded successfully!")
#         st.write("Extracted Text from PDF:")
#         st.write(pdf_text[:2000])  # Display first 2000 characters of the PDF text for context

#         # Step 3: User Input for Analysis on PDF Text
#         user_question = st.text_input("Ask a question about the PDF content")

#         if user_question:
#             analysis_response = generate_analysis(f"Analyze the following PDF text:\n{pdf_text[:2000]}\n{user_question}")
#             st.write("AI Analysis Response:")
#             st.write(analysis_response)
