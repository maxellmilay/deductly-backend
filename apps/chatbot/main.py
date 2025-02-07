import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import TextLoader, PyPDFLoader


load_dotenv()

deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
model = "deepseek-r1-distill-llama-70b"
deepseek = ChatGroq(api_key=deepseek_api_key, model_name=model)

parser = StrOutputParser()
deepseek_chain = deepseek | parser
# print(deepseek_chain.invoke("Hello, how are you?"))

current_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(current_dir, "data.txt")
loader = TextLoader(data_path, encoding="utf-8")
document = loader.load()

template = """
You are a helpful assistant that can answer questions about the text provided.

Text: {context}

Question: {question}
"""

question = "what is tax deduction"
final_template = template.format(context=document, question=question)
answer = deepseek_chain.invoke(final_template)
final_answer = (
    answer.split("</think>")[-1].strip() if "</think>" in answer else answer.strip()
)
print(final_answer)
