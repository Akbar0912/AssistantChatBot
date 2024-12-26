from langchain_ollama import ChatOllama
from langchain.chains import LLMChain
from .prompt import get_sql_prompt

class LLMChainManager:
    @staticmethod
    def setup_chain(schema: str) -> LLMChain:
        """Setup LLM chain with Ollama"""
        llm = ChatOllama(
            model="llama3.2-vision",
            temperature=0.1,
            top_p=0.95,
            top_k=40,
            repeat_penalty=1.1
        )
        
        prompt = get_sql_prompt()
        
        return LLMChain(
            llm=llm,
            prompt=prompt,
            verbose=True
        )