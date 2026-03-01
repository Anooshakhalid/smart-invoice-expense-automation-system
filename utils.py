import os
import json
import hashlib

OUTPUT_DIR = "output"
DB_PATH = os.path.join(OUTPUT_DIR, "invoices_db.json")
os.makedirs(OUTPUT_DIR, exist_ok=True)


CATEGORY_RULES = {
    "technology": [
        "smart phone", "phone", "voip", "signal booster",
        "fax", "fax machine", "wireless fax","Dell","COMPUTER",
        "copier", "copy machine", "personal copier","Controller",
        "printer", "receipt printer", "card printer",
        "inkjet", "laser", "digital", "computer table", "keyboard", "mouse",
        "epson", "canon", "brother", "hewlett", "hp","Projector",
        "motorola", "nokia", "samsung", "cisco",
        "startech", "konica", "panasonic","PlayStation","Xbox","Console","Games","Apple","Ink"
    ],

    "home essentials": [
        "chair", "armchair", "leather armchair",
        "rocking chair", "swivel stool",
        "table", "training table", "round table",
        "bookcase", "library",
        "cabinet", "shelf", "floating shelf",
        "file cart", "Woody","Glass","Bottle"
        
        "wood", "metal", "pine","Microwave",
        
        "towel", "tissue","Wine",
        
        "storage", "doors","Carpets"
    ],

    "fashion": [
        "shoes", "sneakers", "boots", "sandals",
        "dress", "shirt", "pants", "jeans",
        "jacket", "coat", "hoodie", "t-shirt",
        "belt", "scarf", "hat", "gloves" ,"Boys", "Jordan","Sleepwear","Unisex"
    ],
    "books" : [
        "by" , ":", "The" ,"Your" ,"A" ,"Edition" ,"of" ,"Analysis", "Articles",

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