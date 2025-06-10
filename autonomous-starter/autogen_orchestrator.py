import autogen
from typing import Optional, Tuple


def create_manager() -> Tuple[autogen.GroupChatManager, autogen.UserProxyAgent]:
    config = autogen.config_list_from_dotenv()
    if not config:
        raise RuntimeError("No LLM configuration found")
    assistant = autogen.AssistantAgent("assistant", llm_config={"config_list": config})
    user = autogen.UserProxyAgent("user", llm_config={"config_list": config})
    groupchat = autogen.GroupChat(agents=[user, assistant], messages=[])
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config={"config_list": config})
    return manager, user


def main() -> None:
    manager, user = create_manager()
    user.initiate_chat(manager, message="Hello from Autogen Starter")


if __name__ == "__main__":
    main()
