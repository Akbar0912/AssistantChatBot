import openai
import os
import time
import json
import requests
from dotenv import load_dotenv

load_dotenv()

class AssistantManager:
    thread_id = "thread_PJ6OXeGEO5e94nWw5lWBkfgX"
    assistant_id = "asst_gtpT2wBTv3KLvS4lPR8tuVbe"

    def __init__(self, model: str):
        self.client = openai.OpenAI()
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

    def create_thread(self):
        if not self.thread:
            thread_obj = self.client.beta.threads.create()
            AssistantManager.thread_id = thread_obj.id
            self.thread = thread_obj

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
            response = last_message.content[0].text.value
            summary.append(response)

            self.summary = "\n".join(summary)

    def call_required_functions(self, required_actions):
        if not self.run:
            return
        tool_outputs = []

        for action in required_actions["tool_calls"]:
            func_name = action["function"]["name"]
            arguments = json.loads(action["function"]["arguments"])

            if func_name == "get_news":
                from refactor.news import get_news  # Import the function
                output = get_news(topic=arguments["topic"])
                final_str = "".join(output)

                tool_outputs.append({"tool_call_id": action["id"], "output": final_str})
            else:
                raise ValueError(f"Unknown Function: {func_name}")

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

                if run_status.status == "completed":
                    self.process_message()
                    break
                elif run_status.status == "requires_action":
                    self.call_required_functions(
                        required_actions=run_status.required_action.submit_tool_outputs.model_dump()
                    )

    def run_steps(self):
        run_steps = self.client.beta.threads.runs.steps.list(
            thread_id=self.thread.id,
            run_id=self.run.id
        )
        return run_steps.data
