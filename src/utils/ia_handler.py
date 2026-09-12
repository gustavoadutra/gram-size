from google import genai
from dotenv import load_dotenv

import os

class IA:
    def __init__(self):
        load_dotenv()
        API = os.getenv("GEMINI_API_KEY")

        self.client = genai.Client(api_key=API)

    def response(self, question, chunks):
        interaction = self.client.interactions.create(
            model="gemini-3.8-flash",
            input="Você é um fisioterapeuta e deve ajudar outro fisioterapeuta utilizando as fontes, responda a pergunta em português brasil, não invente informações,"
            + f"se achar que algum texto da fonte não ajuda na resposta apenas ignore ele, não use markdown na resposta. Pergunta {question} Fontes: {chunks}"
        )
        print(interaction.output_text)
        print("=="*20)
        return interaction.output_text