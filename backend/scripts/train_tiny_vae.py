"""Offline training script for the tiny composition VAE."""

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch
from torch.utils.data import DataLoader, TensorDataset

from app.layers.vae_model import CompositionVAE, ELEMENT_VOCAB, MAX_ELEMENT_COUNT, MODEL_FILE
from app.core.utils import parse_chemical_formula


def make_random_formula():
    elements = random.sample(ELEMENT_VOCAB, k=random.randint(2, 4))
    counts = [random.randint(1, MAX_ELEMENT_COUNT) for _ in elements]
    parts = [f"{el}{count if count > 1 else ''}" for el, count in zip(elements, counts)]
    return "".join(parts)


def formula_to_vector(formula: str):
    counts = parse_chemical_formula(formula)
    return [min(MAX_ELEMENT_COUNT, counts.get(el, 0)) / MAX_ELEMENT_COUNT for el in ELEMENT_VOCAB]


def main():
    torch.manual_seed(42)
    random.seed(42)

    samples = [make_random_formula() for _ in range(1200)]
    vectors = [formula_to_vector(x) for x in samples]
    data = torch.tensor(vectors, dtype=torch.float32)

    dataset = TensorDataset(data)
    loader = DataLoader(dataset, batch_size=32, shuffle=True)

    model = CompositionVAE(len(ELEMENT_VOCAB), 8)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    mse = torch.nn.MSELoss()

    epochs = 60
    for epoch in range(epochs):
        total_loss = 0.0
        for batch in loader:
            x = batch[0]
            optimizer.zero_grad()
            outputs = model(x)
            recon = outputs["recon"]
            mu = outputs["mu"]
            logvar = outputs["logvar"]
            recon_loss = mse(recon, x)
            kld = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
            loss = recon_loss + 0.1 * kld
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * x.size(0)

        avg_loss = total_loss / len(dataset)
        if epoch % 10 == 0 or epoch == epochs - 1:
            print(f"Epoch {epoch+1}/{epochs}, loss={avg_loss:.5f}")

    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), MODEL_FILE)
    print(f"Saved VAE weights to {MODEL_FILE}")

    model.eval()
    with torch.no_grad():
        z = torch.randn(5, 8)
        decoded = model.decode(z).cpu().numpy()
        for i, vector in enumerate(decoded):
            counts = [int(round(min(1.0, max(0.0, val)) * MAX_ELEMENT_COUNT)) for val in vector]
            formula = "".join([f"{el}{cnt if cnt != 1 else ''}" for el, cnt in zip(ELEMENT_VOCAB, counts) if cnt > 0])
            print(f"Sample {i+1}: {formula}")


if __name__ == "__main__":
    main()
