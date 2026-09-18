import os

from google import genai
from dotenv import load_dotenv

class IA:
    def __init__(self):
        load_dotenv()
        API = os.getenv("GEMINI_API_KEY")

        self.client = genai.Client(api_key=API)
        self.prompt = f""" 
        Você é um fisioterapeuta e deve ajudar outro fisioterapeuta utilizando as fontes,
        responda a pergunta em português brasil, não invente informações, 
        se achar que algum texto da fonte não ajuda na resposta apenas ignore ele, 
        não use markdown na resposta. Cite as fontes como se fosse um artigo científico. 
        No final das fontes coloque quais as páginas usadas.
        """

    def response(self, question, chunks):
        print("[IA] Generating answer..")
        interaction = self.client.interactions.create(
            model="gemini-3.8-flash",
            input= f"{self.prompt} Pergunta {question} Fontes: {chunks}"
        )
        print(f"[IA] Answer: {interaction.output_text}")
        return interaction.output_text