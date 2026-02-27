import torch
import torch.nn as nn
from transformers import AutoModel


class CodeQualityModel(nn.Module):
    def __init__(self):
        super().__init__()
        # Load the downloaded GraphCodeBERT as the base
        self.encoder = AutoModel.from_pretrained("microsoft/graphcodebert-base")

        # Regression head, squeezes embedding down to a single score
        self.regressor = nn.Sequential(
            nn.Linear(768, 256), nn.ReLU(), nn.Dropout(0.1), nn.Linear(256, 1)
        )

    def forward(self, input_ids, attention_mask):
        # Get the embedding from GraphCodeBERT
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)

        # Take the mean of all token embeddings
        embedding = outputs.last_hidden_state.mean(dim=1)

        # Pass through regression head to get a score
        score = self.regressor(embedding)
        return score, embedding  # return both so you can use either
