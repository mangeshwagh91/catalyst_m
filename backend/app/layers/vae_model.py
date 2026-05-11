"""Tiny VAE model for composition-based catalyst generation."""

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from app.core.logging import logger
from app.core.utils import parse_chemical_formula

MODEL_FILE = Path(__file__).parent / "vae_weights.pth"
ELEMENT_VOCAB = [
    "Cu", "Zn", "Al", "Ni", "Co", "Fe", "Pd", "Pt", "Ag", "Au",
    "Ti", "Mn", "Cr", "Mo", "V", "W", "O", "N", "S", "C"
]
MAX_ELEMENT_COUNT = 6
LATENT_DIM = 8
INPUT_DIM = len(ELEMENT_VOCAB)


class CompositionVAE(nn.Module):
    def __init__(self, input_dim: int, latent_dim: int):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 48),
            nn.ReLU(),
            nn.Linear(48, 32),
            nn.ReLU(),
        )
        self.fc_mu = nn.Linear(32, latent_dim)
        self.fc_logvar = nn.Linear(32, latent_dim)
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 48),
            nn.ReLU(),
            nn.Linear(48, input_dim),
        )

    def encode(self, x: torch.Tensor) -> (torch.Tensor, torch.Tensor):
        hidden = self.encoder(x)
        return self.fc_mu(hidden), self.fc_logvar(hidden)

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        decoded = self.decoder(z)
        return torch.sigmoid(decoded)  # values in (0, 1)

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        recon = self.decode(z)
        return {"recon": recon, "mu": mu, "logvar": logvar}


class VAEGenerativeModel:
    """Wrapper for the lightweight composition VAE."""

    def __init__(self):
        self.logger = logger
        self.version = "v1.0-vae"
        self.model = CompositionVAE(INPUT_DIM, LATENT_DIM)
        self.is_available = self._load_weights()

    def _load_weights(self) -> bool:
        if not MODEL_FILE.exists():
            self.logger.warning(f"VAE weights not found at {MODEL_FILE}; falling back to heuristics")
            return False

        try:
            self.model.load_state_dict(torch.load(MODEL_FILE, map_location="cpu"))
            self.model.eval()
            self.logger.info(f"Loaded VAE weights from {MODEL_FILE}")
            return True
        except Exception as e:
            self.logger.warning(f"Failed to load VAE weights: {e}; using heuristic fallback")
            return False

    def _formula_to_tensor(self, formula: str) -> torch.Tensor:
        counts = parse_chemical_formula(formula)
        vec = np.zeros(INPUT_DIM, dtype=np.float32)
        for idx, element in enumerate(ELEMENT_VOCAB):
            vec[idx] = min(MAX_ELEMENT_COUNT, counts.get(element, 0)) / MAX_ELEMENT_COUNT
        return torch.tensor(vec, dtype=torch.float32)

    def _tensor_to_formula(self, tensor: torch.Tensor) -> str:
        values = tensor.detach().cpu().numpy().clip(0.0, 1.0)
        counts = np.round(values * MAX_ELEMENT_COUNT).astype(int)
        parts = []
        for idx, count in enumerate(counts):
            if count > 0:
                element = ELEMENT_VOCAB[idx]
                if count == 1:
                    parts.append(f"{element}")
                else:
                    parts.append(f"{element}{count}")
        if not parts:
            return "Cu"
        return "".join(parts)

    def generate_compositions(
        self,
        base_composition: Optional[str] = None,
        num_samples: int = 8,
    ) -> List[str]:
        if not self.is_available:
            return []

        base_vec = None
        if base_composition:
            try:
                base_vec = self._formula_to_tensor(base_composition)
            except Exception:
                base_vec = None

        with torch.no_grad():
            if base_vec is not None:
                mu, logvar = self.model.encode(base_vec.unsqueeze(0))
                z_base = self.model.reparameterize(mu, logvar).squeeze(0)
            else:
                z_base = torch.zeros(LATENT_DIM)

            compositions = []
            seen = set()
            for _ in range(num_samples * 3):
                noise = torch.randn(LATENT_DIM)
                z = z_base + noise * 0.5
                decoded = self.model.decode(z.unsqueeze(0)).squeeze(0)
                formula = self._tensor_to_formula(decoded)
                if formula not in seen:
                    seen.add(formula)
                    compositions.append(formula)
                if len(compositions) >= num_samples:
                    break

        return compositions

    def get_model_info(self) -> Dict[str, str]:
        return {
            "version": self.version,
            "model_type": "Variational Autoencoder (VAE)",
            "training_data": "Simulated Materials Project / OC20 composition corpus",
            "status": "loaded" if self.is_available else "unavailable",
            "fallback": "heuristic generation is available if weights are missing",
        }
