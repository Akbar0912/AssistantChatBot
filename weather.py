import openai
import os
from dotenv import load_dotenv
import requests
import json
import streamlit as st
from datetime import datetime
import time
# import plotly.express as px

load_dotenv()

# API keys
news_api_key = os.environ.get("NEWS_API_KEY")
weather_api_key = os.environ.get("WEATHER_API_KEY")
client = openai.OpenAI()
model = "gpt-3.5-turbo-16k"

def get_sales_revenue(year):
    url = f"http://127.0.0.1:5000/api/sales_revenue?year={year}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            sales_data = response.json()
            return sales_data
        else:
            return f"Error: Unable to fetch sales data for year {year}"
    
    except requests.exceptions.RequestException as e:
        return f"Error occurred during API request: {e}"

# def get_weather(city):
    url = f"https://api.openweathermap.org/data/2.5/weather?appid={weather_api_key}&q={city}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            weather_data = response.json()
            
            # Extracting relevant details
            coord = weather_data["coord"]
            weather = weather_data["weather"][0]
            main = weather_data["main"]
            wind = weather_data["wind"]
            clouds = weather_data["clouds"]
            sys = weather_data["sys"]
            visibility = weather_data["visibility"]
            
            weather_summary = f"""
                City: {weather_data['name']}
                Country: {sys['country']}
                Coordinates: {coord['lat']}, {coord['lon']}
                Weather: {weather['main']} - {weather['description']}
                Temperature: {main['temp']} K
                Feels Like: {main['feels_like']} K
                Min Temperature: {main['temp_min']} K
                Max Temperature: {main['temp_max']} K
                Pressure: {main['pressure']} hPa
                Humidity: {main['humidity']}%
                Wind Speed: {wind['speed']} m/s
                Wind Direction: {wind['deg']} degrees
                Cloudiness: {clouds['all']}%
                Visibility: {visibility} meters
                Sunrise: {datetime.utcfromtimestamp(sys['sunrise']).strftime('%Y-%m-%d %H:%M:%S')}
                Sunset: {datetime.utcfromtimestamp(sys['sunset']).strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            return weather_summary
    
        else:
            return "Error: Unable to fetch weather data"
    
    except requests.exceptions.RequestException as e:
        return f"Error occurred during API request: {e}"

class AssistantManager:
    # thread_id = "thread_h35fO7EyjIYi2fP664TRU2Fo"
    # assistant_id = "asst_uZ9Ew4iC857rCfmLyzL1MoFR"
    thread_id = "thread_lJyOI9j9Kl8gvNB1xlGS0Nel"
    assistant_id = "asst_5yD5pIrURjhLk1VAsTVfI9A3"

    def __init__(self, model: str = model):
        self.client = client
        self.model = model
        self.assistant = None
        self.thread = None
        self.run = None
        self.summary = None

        # Retrieve existing assistant and thread if IDs are already set
        if AssistantManager.assistant_id:
            self.assistant = self.client.beta.assistants.retrieve(
                assistant_id=AssistantManager.assistant_id
            )
        if AssistantManager.thread_id:
            self.thread = self.client.beta.threads.retrieve(
                thread_id=AssistantManager.thread_id
            )

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

    def create_thread(self):
        if not self.thread:
            thread_obj = self.client.beta.threads.create()
            AssistantManager.thread_id = thread_obj.id
            self.thread = thread_obj
            print(f"ThreadId::; {self.thread.id}")

    def add_message_to_thread(self, role, content):
        if self.thread:
            self.client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role=role,
                content=content
            )

    def run_assistant(self, instructions):
        if self.thread and self.assistant:
            self.run = self.client.beta.threads.runs.create(
                thread_id=self.thread.id,
                assistant_id=self.assistant.id,
                instructions=instructions,
            )

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
            arguments = json.loads(action["function"]["arguments"])

            # if func_name == "get_weather":
            #     # prompt
            #     output = get_weather(city=arguments["city"]) 
            #     print(f"YEAHHHH;;;;;{output}")
            #     tool_outputs.append({"tool_call_id": action["id"], "output": output})
                
            if func_name == "get_sales_revenue":
                # prompt
                output = get_sales_revenue(year=arguments["year"])
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
                time.sleep(5)
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=self.thread.id,
                    run_id=self.run.id
                )
                print(f"RUN STATUS:: {run_status.model_dump_json(indent=4)}")

                if run_status.status == "completed":
                    self.process_message()
                    break
                elif run_status.status == "requires_action":
                    print("FUNCTION CALLING NOW...")
                    self.call_required_functions(
                        required_actions=run_status.required_action.submit_tool_outputs.model_dump()
                    )

    def run_steps(self):
        run_steps = self.client.beta.threads.runs.steps.list(
            thread_id=self.thread.id,
            run_id=self.run.id
        )
        print(f"Run-steps::: {run_steps}")
        return run_steps.data
        
def main():
    manager = AssistantManager()
    
    # Streamlit interface
    st.title("Keuangan Perusahaan")
    
    with st.form(key="user_input_form"):
        # city = st.text_input("Enter city:")
        year = st.text_input("Masukkan Prompt:")
        # month = st.text_input("Enter month:")
        submit_button = st.form_submit_button(label="Run Assistant")
        
        if submit_button:
            manager.create_assistant(
                    name="Sales Revenue and expenses Summarizer",
                    instructions="You are a sales data assistant who knows how to retrieve and summarize sales data for a given year and month. then find out the range of product quantities",
                    tools=[
                        {
                            "type":"function",
                            "function":{
                                "name":"get_sales_revenue",
                                "description":"Fetch the sales revenue and expenses details for a given year and month and also display the highest and lowest products",
                                "parameters":{
                                    "type":"object",
                                    "properties":{
                                        "year":{
                                            "type":"string",
                                            "description":"The year for which to fetch the sales data.",
                                        },
                                        "month":{
                                            "type":"string",
                                            "description":"The month for which to fetch the sales data.",
                                        }
                                    },
                                    "required":["year", "month"],  
                                },
                            },
                        }]
            )
            # manager.create_assistant(
            #     name="Weather Summarizer",
            #     instructions="You are a personal weather assistant who knows how to fetch weather details for a given city and provide a summary.",
            #     tools=[
            #         {
            #         "type":"function",
            #         "function":{
            #             "name":"get_weather",
            #             "description":"Fetch the weather details for a given city.",
            #             "parameters":{
            #                 "type":"object",
            #                 "properties":{
            #                     "city":{
            #                         "type":"string",
            #                         "description":"The city for which to fetch the weather, e.g., Bandung",
            #                     }
            #                 },
            #                 "required":["city"],  
            #             },
            #         },
            #     }]
            # )
            manager.create_thread()
            
            # Add the message and run the assistant
            manager.add_message_to_thread(
                role="user",
                content=f"Provide the sales data for {year}"
                )
            manager.run_assistant(instructions="Provide details of sales income and expenses including when required a range")
            # manager.add_message_to_thread(
            #     role="user",
            #     content=f"Provide the weather details for {city}.",
            # )
            # manager.run_assistant(instructions="Provide the weather details.")
            
            # Wait for completions and process messages
            manager.wait_for_completion()
            
            summary = manager.get_summary()
            
            st.write(summary)
            
            st.text("Runs Steps:")
            st.code(manager.run_steps(), line_numbers=True)

if __name__ == "__main__":
    main()
