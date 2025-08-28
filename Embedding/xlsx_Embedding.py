#XLSE ONLY !!!
#XLSE ONLY !!!
#XLSE ONLY !!!
import re
import pandas as pd

print("Reading File...")
excel = pd.read_excel("product_list_expanded.xlsx")
names = (list(excel["Name"]))
descriptions = list(excel["Description"])
prices = list(excel["Price"])

from langchain_ollama import OllamaEmbeddings
embedding = OllamaEmbeddings(model = "bge-m3:latest") #1024 dim
names_embedded = [] 
descriptions_embedded = []

print("Embedding...")
for name in names:
    names_embedded.append(str(embedding.embed_query(name)))
for description in descriptions:
    descriptions_embedded.append(str(embedding.embed_query(description)))

import psycopg2
connection = psycopg2.connect("host=100.107.93.75 dbname=Chatbot_db user=n8n_user password=n8n_pass") 
cursor = connection.cursor()
print("Storing vectors...")
for i in range(len(names_embedded)):
    name = names[i]
    description = descriptions[i]
    price = prices[i]
    name_embedded = names_embedded[i]
    description_embedded = descriptions_embedded[i]
    cursor.execute("INSERT INTO product_information (name, description, price, name_embedded, description_embedded) VALUES (%s, %s, %s, %s, %s)", 
                                                    (name, description, price, name_embedded, description_embedded) )

connection.commit()
cursor.close()
connection.close()

print("Success!")
