"""Download small public Loghub sample datasets used by this project."""
from pathlib import Path
from urllib.request import urlretrieve

DATASETS = {
    "Apache_2k.log": "https://raw.githubusercontent.com/logpai/loghub/master/Apache/Apache_2k.log",
    "HDFS_2k.log": "https://raw.githubusercontent.com/logpai/loghub/master/HDFS/HDFS_2k.log",
}

out_dir = Path("data/loghub")
out_dir.mkdir(parents=True, exist_ok=True)

for filename, url in DATASETS.items():
    path = out_dir / filename
    print(f"Downloading {filename}...")
    urlretrieve(url, path)
    print(f"Saved {path}")
