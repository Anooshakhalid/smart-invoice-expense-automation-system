import os
import json
import hashlib

OUTPUT_DIR = "output"
DB_PATH = os.path.join(OUTPUT_DIR, "invoices_db.json")
os.makedirs(OUTPUT_DIR, exist_ok=True)


CATEGORY_RULES = {
    "technology": [
        "computer", "pc", "desktop", "laptop", "intel", "nvidia", "ssd", "ram",
        "monitor", "wii", "nintendo", "gameboy", "controller", "console",
        "gaming", "keyboard", "mouse", "vr-ready", "graphics"
    ],
    "fashion": [
        "shoes", "sneakers", "boots", "sandals", "heels", "flats",
        "dress", "shirt", "blouse", "pants", "jeans", "jacket", "coat",
        "hoodie", "t-shirt", "skirt", "sweater", "tunics", "leggings",
        "accessories", "belt", "scarf", "hat", "cap", "gloves", "mask",
        "fashion", "maxmara", "boden", "michael kors", "xhiliration",
        "psychedelic", "hawaiian", "striped", "knitted", "wrap"
    ],
    "home essentials": [
        "chair", "table", "sofa", "couch", "cabinet", "shelf", "lamp",
        "rug", "bedding", "mattress", "pan", "plate", "cup", "knife",
        "fork", "spoon", "blender", "kettle", "towel", "tissue",
        "mask", "detergent", "soap", "cleaning", "bath", "books"
    ]
}

# -------------------------
# JSON DB
# -------------------------
def load_db():
    if not os.path.exists(DB_PATH):
        return {"invoices": []}
    with open(DB_PATH, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_PATH, "w") as f:
        json.dump(db, f, indent=2)

# -------------------------
# HASH / DEDUPLICATION
# -------------------------
def get_file_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def already_processed(file_hash):
    db = load_db()
    for inv in db["invoices"]:
        if inv.get("_hash") == file_hash:
            return True
    return False

# -------------------------
# CATEGORY
# -------------------------
def categorize(name):
    name = name.lower()
    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw in name:
                return category
    return "uncategorized"