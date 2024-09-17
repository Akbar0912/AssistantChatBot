import streamlit as st
from refactor.assistant import AssistantManager

def main():
    manager = AssistantManager(model="gpt-3.5-turbo-16k")
    
    st.title("News Summarizer")
    
    with st.form(key="user_input_form"):
        instructions = st.text_input("Enter topic:")
        submit_button = st.form_submit_button(label="Run Assistant")
        
        if submit_button:
            manager.create_assistant(
                name="News Summarizer",
                instructions="You are a personal article summarizer assistant who knows how to take a list of articles' titles and descriptions and then write a short summary of all the news articles.",
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "get_news",
                        "description": "Get the list of articles/news for the given topic",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "topic": {
                                    "type": "string",
                                    "description": "The topic for the news, e.g., Tesla",
                                }
                            },
                            "required": ["topic"],
                        },
                    },
                }]
            )
            manager.create_thread()
            
            manager.add_message_to_thread(
                role="user",
                content=f"Summarize the news on this topic: {instructions}?"
            )
            manager.run_assistant(instructions="Summarize the news")
            
            manager.wait_for_completion()
            
            summary = manager.get_summary()
            st.write(summary)
            
            st.text("Run Steps:")
            st.code(manager.run_steps(), line_numbers=True)

if __name__ == "__main__":
    main()
