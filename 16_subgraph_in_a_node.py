import langgraph
from typing import Annotated,TypedDict
from langchain_groq import ChatGroq
from langchain_huggingface import ChatHuggingFace,HuggingFaceEndpoint
from langchain_core.messages import AnyMessage,AIMessage,BaseMessage,HumanMessage
from langgraph.graph import StateGraph,START,END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt,Command
from dotenv import load_dotenv
import json
import requests
from langchain.tools import tool

#=====================Creating LLMs ==================================

load_dotenv()
llm = HuggingFaceEndpoint(
    repo_id="meta-llama/Llama-3.1-8B-Instruct",
    task="text-generation",
)
generation_model = ChatHuggingFace(llm=llm)

translation_model = ChatGroq(
    model="llama-3.3-70b-versatile",
)



#=====================Parent State & Child State ====================
class ParentState(TypedDict):
    tittle:str
    Essay:str
    Urdu:str

class ChildState(TypedDict):
    Essay:str
    Urdu:str

#==================== Child Nodes ====================================

def translate(state:ChildState)->dict:
    message = state['Essay']
    prompt = f"Translate the Essay in Urdu, and don't add any extra information, just translate this given Essay \n {message}"
    result = translation_model.invoke(prompt)
    urdu = result.content
    return {'Urdu':urdu}

#==================== Child Graph ===================================

child = StateGraph(ChildState)

child.add_node('translate',translate)

child.add_edge(START,'translate')
child.add_edge('translate',END)

child_workflow = child.compile()



#=================== Parent Nodes =======================================

def generate_essay(state:ParentState)->dict:
    tittle = state['tittle']
    prompt = f"Generate a 100 word Essay on this topic - {tittle}"
    result = generation_model.invoke(prompt)
    essay = result.content
    return {'Essay':essay}

def generate_translation(state:ParentState)->dict:
    essay = state['Essay']
    result = child_workflow.invoke({'Essay':essay})
    return {'Urdu':result['Urdu']}

#=================== Parent Graph =====================================

parent = StateGraph(ParentState)

parent.add_node('generate_essay',generate_essay)
parent.add_node('generate_translation',generate_translation)

parent.add_edge(START,'generate_essay')
parent.add_edge('generate_essay','generate_translation')
parent.add_edge('generate_translation',END)

parent_workflow = parent.compile()

initial_state = {'tittle':'Pakistan'}
result = parent_workflow.invoke(initial_state)

print(result)