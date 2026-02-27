from transformers import AutoModel, AutoTokenizer

MODEL_NAME = "microsoft/graphcodebert-base"

print("Downloading GraphCodeBERT...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)
print("Done. Model cached locally.")
