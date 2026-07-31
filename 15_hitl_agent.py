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


#=========================Initializing Models================================

load_dotenv()
llm = HuggingFaceEndpoint(
    repo_id="meta-llama/Llama-3.1-8B-Instruct",
    task="text-generation",
)
model = ChatHuggingFace(llm=llm)

model1 = ChatGroq(
    model="llama-3.3-70b-versatile",
)

#========================Creating States ====================================

class ChatState(TypedDict):
    messages : Annotated[list[BaseMessage],add_messages]



#========================Creating tool =======================================

@tool
def get_stock_price(symbol:str)->dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL','TSLA')
    using Alpha Vantage with API key in the URL.
    """
    API_KEY = "T8LZU4O7OR97TYDJ"
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={API_KEY}"
    response = requests.get(url=url)
    return response.json()

@tool
def purchase_stock(symbol:str,quantity:int)->dict:
    """
    Purchase the given stock in given quantity

    Human in the loop:
    Before purchasing the stock process interrupt and confirmed purchasing order from human.
    """
    decision = interrupt(f"Approve buying {quantity} shares of {symbol}: yes/no?")

    if isinstance(decision,str) and decision.lower() == 'yes':
        return {
            'status':'success',
            'message':f"Purchase order placed for {quantity} shares  of {symbol}",
            'symbol':symbol,
            'quantity':quantity
        }
    else:
        return {
            'status':'declined',
            'message':f"Purchase order declined by Humman for {quantity} shares of {symbol}",
            'symbol':symbol,
            'quantity':quantity
        }

#----------making tool list------------

tools = [get_stock_price,purchase_stock]

# ---------making tool llm -------------

llm_with_tools = model1.bind_tools(tools)







#========================Creating Nodes ======================================

def chat_node (state:ChatState):

    message = llm_with_tools.invoke(state['messages'])

    return  {
        'messages':
        [message]
    }

   


tool_node = ToolNode(tools)


#=========================Creating Graph========================================
builder = StateGraph(ChatState)

builder.add_node('chat_node',chat_node)
builder.add_node('tools',tool_node)


builder.add_edge(START,'chat_node')
builder.add_conditional_edges('chat_node',tools_condition)
builder.add_edge('tools','chat_node')

checkpointer = MemorySaver()

workflow = builder.compile(checkpointer=checkpointer)


#==========================Creating Run loop====================================

config = {'configurable':{'thread_id':'12345'}}

while True:
    user_input = input("You: ")
    if user_input.lower().strip() in {'exit' , 'quit' , 'stop' , 'bye'}:
        print('AI: goodbye')
        break


    #-----------initial state ------------
    initial_state = {'messages':[HumanMessage(content=user_input)]}

    #-----------run graph-----------------

    result = workflow.invoke(
        initial_state,
        config= config
    )

    #-----------interrupt code-----------
    interrupts = result.get('__interrupt__',[])

    if interrupts:
        question = interrupts[0].value

        print("HITL: ",question)
        decision = input("Your Decision: ").strip().lower()

        result = workflow.invoke(
            Command(
                resume=decision,
            ),
            config=config
            
        )
    last_messages = result['messages'][-1]
    result = last_messages.content

    print(f"AI: {result}")




    