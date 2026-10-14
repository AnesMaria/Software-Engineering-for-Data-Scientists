"""Load the trusted model distributed with this project only."""
import pickle
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
model_path = project_root / "assets" / "model.pkl"


def load_model():
    with model_path.open("rb") as file:
        return pickle.load(file)