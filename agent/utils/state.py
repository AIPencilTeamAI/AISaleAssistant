from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages] #give bot what is going on in the main chat
    raw_input: dict