"""Download only Retailrocket's real events.csv from Kaggle."""
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
TARGET = DATA_DIR / "events.csv"

def main():
    if TARGET.exists() and TARGET.stat().st_size > 1_000_000:
        print(f"Dataset already exists: {TARGET} ({TARGET.stat().st_size:,} bytes)")
        return

    # Kaggle CLI must be configured with the user's own Kaggle API token.
    command = [
        sys.executable, "-m", "kaggle", "datasets", "download",
        "-d", "retailrocket/ecommerce-dataset",
        "-f", "events.csv",
        "-p", str(DATA_DIR),
        "--unzip",
    ]
    print("Downloading the real Retailrocket events.csv from Kaggle...")
    print("This may take a few minutes depending on your connection.")
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError:
        raise SystemExit("Kaggle CLI is unavailable. Run: pip install kaggle")
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            "Kaggle download failed. Check that your Kaggle API token is configured. "
            "See README.md for setup and manual download instructions."
        ) from exc

    # Kaggle may leave the downloaded archive in data/. Extract only events.csv.
    for archive in DATA_DIR.glob("*.zip"):
        with zipfile.ZipFile(archive) as zf:
            candidates = [n for n in zf.namelist() if Path(n).name == "events.csv"]
            if candidates and not TARGET.exists():
                with zf.open(candidates[0]) as src, TARGET.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
        archive.unlink(missing_ok=True)

    if not TARGET.exists() or TARGET.stat().st_size < 1_000_000:
        raise SystemExit("events.csv was not found after download. Check the Kaggle dataset files.")
    print(f"Dataset ready: {TARGET} ({TARGET.stat().st_size / (1024*1024):.1f} MB)")

if __name__ == "__main__":
    main()
