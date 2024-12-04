# from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.llms import Ollama
import streamlit as st
import os
from dotenv import load_dotenv 

load_dotenv()

# os.environ["OPENAI_API_KEY"]=os.getenv("OPENAI_API_KEY")
## Langmith tracking
os.environ["LANGCHAIN_TRACING_V2"]="true"
os.environ["LANGCHAIN_API_KEY"]=os.getenv("LANGCHAIN_API_KEY")


# tempalate prompt

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "you are  a helpful assistant. please response to the user queries"),
        ("user", "Question:{question}")
    ])

## streamlit framework
# st.title('Langchain Demo With OPENAI API')
st.title('Langchain Demo With Llama3.2 API')
input_text=st.text_input("Search the topic u want")

#openAI LLM
# llm=ChatOpenAI(model="gpt-3.5-turbo")

#Ollama LLM
llm=Ollama(model="llama3.2-vision")
output_parser=StrOutputParser()
chain=prompt|llm|output_parser

if input_text:
    st.write(chain.invoke({'question':input_text}))
    
# llm = ChatOpenAI()
# llm.invoke("hayyy")