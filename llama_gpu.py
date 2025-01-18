from langchain_community.llms import LlamaCpp
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler
from langchain_core.prompts import PromptTemplate

MODEL_PATH="llama3.2-vision"

def load_model()-> LlamaCpp:
    """Loads llama model"""
    callback_manager : CallbackManager = CallbackManager([StreamingStdOutCallbackHandler()])
    
    Llama_model : LlamaCpp = LlamaCpp(
        model_path=MODEL_PATH,
        temperature=0.5,
        max_tokens=2000,
        top_p=1,
        callback_manager=callback_manager,
        verbose=True
    )
    
    return Llama_model

llm = load_model()

model_prompt: str ="""
Question: What is the largest country on Earth?
"""

response: str = llm(model_prompt)

