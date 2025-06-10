import os
import autogen


def main() -> None:
    """Run a simple AutoGen chat using an Ollama model."""
    model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    endpoint = os.getenv("OLLAMA_API_ENDPOINT", "http://localhost:11434")

    llm_config = {
        "config_list": [
            {
                "api_type": "ollama",
                "model": model,
                "client_host": endpoint,
            }
        ]
    }

    assistant = autogen.AssistantAgent("assistant", llm_config=llm_config)
    user = autogen.UserProxyAgent("user", human_input_mode="ALWAYS")

    assistant.initiate_chat(user, message="Hello! How can I help you today?")


if __name__ == "__main__":
    main()
