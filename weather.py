import openai
import os
from dotenv import load_dotenv
import requests
import json
import streamlit as st
import re
import time
import pandas as pd
import matplotlib.pyplot as plt

load_dotenv()

# API keys
client = openai.OpenAI()
model = "gpt-4"

@st.cache_data
def get_data():
    url = f"http://127.0.0.1:5000/data"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            sales_data = response.json()
            print(sales_data)
            return sales_data
        else:
            return f"Error: Unable to fetch sales data for year"
    
    except requests.exceptions.RequestException as e:
        return f"Error occurred during API request: {e}"

# Fungsi untuk memvisualisasikan data dalam bentuk grafik
# def visualize_data(data):
    # tahun = data["categories_column"][0]["tahun"]
    # adhb = [100, 200, 150, 300, 250]  # Ganti dengan nilai sebenarnya dari data
    # kontribusi = [50, 80, 70, 120, 100]  # Ganti dengan nilai sebenarnya dari data

    # # Membuat grafik
    # x = range(len(tahun))

    # plt.figure(figsize=(10, 6))
    # plt.bar(x, adhb, width=0.4, label='Adhb', color='blue', align='center')
    # plt.bar([p + 0.4 for p in x], kontribusi, width=0.4, label='Kontribusi', color='orange', align='center')

    # plt.xlabel('Tahun')
    # plt.ylabel('Nilai')
    # plt.title('Grafik Adhb dan Kontribusi berdasarkan Tahun')
    # plt.xticks([p + 0.2 for p in x], tahun)  # Menyusun label tahun di tengah grafik
    # plt.legend()
    # plt.grid(axis='y')

    # # Simpan grafik ke dalam file dan tampilkan di Streamlit
    # plt.savefig("grafik.png")
    # st.image("grafik.png")

class AssistantManager:
    thread_id = "thread_0iSSBseK9nkiQ2xO2C1wvXJM"
    assistant_id = "asst_r01yLHThKUBkaym2yyJ5FwRv"

    def __init__(self, model: str = model):
        self.client = client
        self.model = model
        self.assistant = None
        self.thread = None
        self.run = None
        self.summary = None

        if AssistantManager.assistant_id:
            self.assistant = self.client.beta.assistants.retrieve(
                assistant_id=AssistantManager.assistant_id
            )
        if AssistantManager.thread_id:
            self.thread = self.client.beta.threads.retrieve(
                thread_id=AssistantManager.thread_id
            )
    # membuat assisten baru jika belum ada
    def create_assistant(self, name, instructions, tools):
        if not self.assistant:
            assistant_obj = self.client.beta.assistants.create(
                name=name,
                instructions=instructions,
                tools=tools,
                model=self.model,
            )
            AssistantManager.assistant_id = assistant_obj.id
            self.assistant = assistant_obj
            print(f"AssisId::: {self.assistant.id}")
            
    # membuat thread baru untuk berkomunikasi dengan assisten
    def create_thread(self):
        if not self.thread:
            thread_obj = self.client.beta.threads.create()
            AssistantManager.thread_id = thread_obj.id
            self.thread = thread_obj
            print(f"ThreadId::; {self.thread.id}")
            
    # menambahkan pesan ke thread yang ada
    def add_message_to_thread(self, role, content):
        if self.thread:
            self.client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role=role,
                content=content
            )
    # menjalankan assistant
    def run_assistant(self, instructions):
        if self.thread and self.assistant:
            self.run = self.client.beta.threads.runs.create(
                thread_id=self.thread.id,
                assistant_id=self.assistant.id,
                instructions=instructions,
            )
    # memproses pesan yang diterima dari asisten
    def process_message(self):
        if self.thread:
            messages = self.client.beta.threads.messages.list(
                thread_id=self.thread.id
            )
            summary = []

            last_message = messages.data[0]
            role = last_message.role
            response = last_message.content[0].text.value
            summary.append(response)

            self.summary = "\n".join(summary)
            print(f"SUMMARY-----> {role.capitalize()}: ==> {response}")

    def call_required_functions(self, required_actions):
        if not self.run:
            return
        tool_outputs = []

        for action in required_actions["tool_calls"]:
            func_name = action["function"]["name"]
            # arguments = json.loads(action["function"]["arguments"])
                
            if func_name == "get_data":
                output = get_data()
                # output = get_sales_revenue(year=arguments["year"])
                print(f"Sales revenue output: {output}")
                tool_outputs.append({"tool_call_id": action["id"], "output": json.dumps(output)})

            else:
                raise ValueError(f"Unknown Function: {func_name}")

        print("SUBMITTING OUTPUT BACK TO THE ASSISTANT......")
        
        self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=self.thread.id,
            run_id=self.run.id,
            tool_outputs=tool_outputs
        )

    def get_summary(self):
        return self.summary

    def wait_for_completion(self):
        if self.thread and self.run:
            while True:
                time.sleep(1)
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=self.thread.id,
                    run_id=self.run.id
                )
                print(f"RUN STATUS:: {run_status.model_dump_json(indent=4)}")

                if run_status.status == "completed":
                    self.process_message()
                    st.write("Run Completed")
                    break
                elif run_status.status == "requires_action":
                    print("FUNCTION CALLING NOW...")
                    self.call_required_functions(
                        required_actions=run_status.required_action.submit_tool_outputs.model_dump()
                    )
                    print(f"ISI dari model Dump {run_status.required_action.submit_tool_outputs.model_dump()}")
                # st.write("Waiting for run to complete...")

    def run_steps(self):
        if not self.run:
            return "Run has not been initialized."
        run_steps = self.client.beta.threads.runs.steps.list(
            thread_id=self.thread.id,
            run_id=self.run.id
        )
        print(f"Run-steps::: {run_steps}")
        return run_steps.data

def is_internal_query(user_input):
    keywords = ['data', 'analisis', 'tahun', 'grafik']
    pattern = re.compile(r'\b(?:' + '|'.join(keywords) + r')\b', re.IGNORECASE)
    
    return bool(pattern.search(user_input))

def assistant_response(user_input):
    response = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": user_input}]
    )
    return response.choices[0].message.content

def main():
    manager = AssistantManager()
    
    st.title("Data Analisis")
    
    with st.form(key="user_input_form"):
        prompt= st.text_input("Masukkan Prompt:")
        submit_button = st.form_submit_button(label="Run Assistant")
        
        if submit_button:
            if is_internal_query(prompt):
                manager.create_assistant(
                    name="Digital Analisis",
                    instructions="""Anda adalah asisten analisis data bisnis yang cerdas dan mampu menjawab semua pertanyaan...""",
                    tools=[{
                        "type": "function",
                        "function": {
                            "name": "get_data",
                            "description": "Mengambil data dari API",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": [],
                            }
                        },
                    }]
                )
                
                
                manager.create_thread()
                
                manager.add_message_to_thread(
                    role="user",
                    content=prompt
                )
                manager.run_assistant(instructions="Mengambil data dari API...")
                
                manager.wait_for_completion()
                
                summary = manager.get_summary()
                
                # visualize_data(summary)
                
                st.write(f"INI HASIL SUMMARY {summary}")
            else:
                general_response = assistant_response(prompt)
                st.write(general_response)
            
            st.text("Runs Steps:")
            st.code(manager.run_steps(), line_numbers=True)

if __name__ == "__main__":
    main()
