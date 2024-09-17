import openai
import os
from dotenv import find_dotenv, load_dotenv
import time
import logging
import streamlit as st
import matplotlib.pyplot as plt

# Load environment variables
load_dotenv()

# Get API key from environment
news_api_key = os.environ.get("NEWS_API_KEY")

# Initialize OpenAI client
client = openai.OpenAI()
model = "gpt-3.5-turbo-16k"

# Streamlit layout
st.title("OpenAI Assistant")
st.subheader("Enter a message for the assistant")

# Input box for user message
user_message = st.text_input("Message:", "")

# Button to send the message
if st.button("Send Message"):
    # ID assistant and thread (replace with your actual IDs)
    assistan_id = "asst_1pnJhZhMhebyqWLnanM10VmX"
    thread_id = "thread_x21mgTW2UVvSY1Jq9Fcyco3P"

    # Send the message to the assistant
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message
    )

    # Run the assistant with instructions
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistan_id,
        instructions="Please address the user as Akbar Pratama"
    )

    # Function to wait for the run to complete
    def wait_for_run_completion(client, thread_id, run_id, sleep_interval=5):
        """
        Waits for a run to complete and prints the elapsed time.
        :param client: The OpenAI client object.
        :param thread_id: The ID of the thread.
        :param run_id: The ID of the run.
        :param sleep_interval: Time in seconds to wait between checks.
        """
        while True:
            try:
                run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
                if run.completed_at:
                    elapsed_time = run.completed_at - run.created_at
                    formatted_elapsed_time = time.strftime(
                        "%H:%M:%S", time.gmtime(elapsed_time)
                    )
                    st.write(f"Run completed in {formatted_elapsed_time}")
                    logging.info(f"Run completed in {formatted_elapsed_time}")
                    
                    # Get messages once Run is completed!
                    messages = client.beta.threads.messages.list(thread_id=thread_id)
                    last_message = messages.data[0]
                    response = last_message.content[0].text.value
                    st.write(f"Assistant Response: {response}")
                    break
            except Exception as e:
                logging.error(f"An error occurred while retrieving the run: {e}")
                break
            logging.info("Waiting for run to complete...")
            st.write("Waiting for run to complete...")
            time.sleep(sleep_interval)
    # Function to visualize the response
    def visualize_response(response):
        # Example: Generate a bar chart from some dummy data
        categories = ['Category A', 'Category B', 'Category C']
        values = [len(response), len(response) // 2, len(response) // 3]  # Example data based on response length

        fig, ax = plt.subplots()
        ax.bar(categories, values)
        ax.set_title("Example Visualization based on Response")
        ax.set_xlabel("Categories")
        ax.set_ylabel("Values")

        # Display the chart in Streamlit
        st.pyplot(fig)

    # Wait for the run to complete
    wait_for_run_completion(client=client, thread_id=thread_id, run_id=run.id)
