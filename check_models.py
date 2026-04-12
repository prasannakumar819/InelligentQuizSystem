from groq import Groq

client = Groq(api_key="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")

models = client.models.list()

for m in models.data:
    print(m.id)