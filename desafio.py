import hashlib
import numpy as np

def gerar_desafio(seed: str, size: int = 64):
    h = hashlib.sha256(seed.encode()).digest()
    rng = np.random.default_rng(int.from_bytes(h[:8], "big"))
    x, y = np.meshgrid(np.linspace(0, 1, size), np.linspace(0, 1, size))
    freqs = rng.uniform(2, 10, size=4)
    campo = sum(np.sin(f * x * np.pi) * np.cos(f * y * np.pi) for f in freqs)
    return campo, h.hex()

if __name__ == "__main__":
    import sys
    seed = sys.argv[1] if len(sys.argv) > 1 else "teste-seed-001"
    campo, hash_seed = gerar_desafio(seed)
    np.save(f"desafio_{hash_seed[:8]}.npy", campo)
    print(f"Seed: {seed}")
    print(f"Hash da seed: {hash_seed}")
    print(f"Desafio salvo em: desafio_{hash_seed[:8]}.npy")
    print(f"Shape: {campo.shape}, min={campo.min():.4f}, max={campo.max():.4f}")
