from flower import (
    FlowerData, 
    FlowersTypes,
    FlowerColors,
    FlowerSizes,
)
from collections import defaultdict
import json
import pandas as pd
import os

def load_all_bouquets():
    all_bouquets = {}
    if os.path.exists("Bouquets.xlsx"):
        try:
            df = pd.read_excel("Bouquets.xlsx")
            # Expected columns: Bouquet Name, Flower Name, Color, Size, Count
            # Group by Bouquet Name
            if not df.empty:
                grouped = df.groupby("Bouquet Name")
                for name, group in grouped:
                    flowers = []
                    for _, row in group.iterrows():
                        f_name = row["Flower Name"]
                        if pd.isna(f_name):
                            continue
                        f_color = row["Color"]
                        f_size = row["Size"]
                        count = int(row["Count"])
                        flower = FlowerData(f_name, f_color, f_size)
                        flowers.extend([flower] * count)
                    all_bouquets[name] = flowers
        except Exception as e:
            print(f"Error loading Bouquets.xlsx: {e}")
    elif os.path.exists("Bouquets.json"):
        try:
            with open("Bouquets.json", "r", encoding="utf-8") as b:
                data = json.load(b)
                # Convert list of lists to list of FlowerData
                for name, flist in data.items():
                    all_bouquets[name] = [FlowerData(*f) for f in flist]
            save_all_bouquets(all_bouquets) # Migrate
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    return all_bouquets

def save_all_bouquets(all_bouquets):
    # Try to preserve extra columns (like Wix ID) from existing file
    existing_extra_data = {} # Map bouquet_name -> {col: val}
    if os.path.exists("Bouquets.xlsx"):
        try:
            old_df = pd.read_excel("Bouquets.xlsx")
            if "Wix ID" in old_df.columns:
                 # Group by bouquet name and take the first value (assuming same ID for whole bouquet)
                 for name, group in old_df.groupby("Bouquet Name"):
                     first_valid = group["Wix ID"].dropna().first()
                     if pd.notna(first_valid):
                         existing_extra_data[name] = {"Wix ID": str(first_valid)}
        except Exception:
            pass

    data = []
    for b_name, flowers in all_bouquets.items():
        # Get extra data
        extra = existing_extra_data.get(b_name, {})
        wix_id = extra.get("Wix ID", None)

        if not flowers:
            # Save empty bouquet
            row = {
                "Bouquet Name": b_name,
                "Flower Name": None,
                "Color": None,
                "Size": None,
                "Count": 0
            }
            if wix_id:
                row["Wix ID"] = wix_id
            data.append(row)
            continue

        # Count flowers
        counts = defaultdict(int)
        for f in flowers:
            counts[f] += 1
        
        for f, count in counts.items():
            row = {
                "Bouquet Name": b_name,
                "Flower Name": f.name,
                "Color": f.color,
                "Size": f.size,
                "Count": count
            }
            if wix_id:
                row["Wix ID"] = wix_id
            data.append(row)
    
    # columns order
    cols = ["Bouquet Name", "Flower Name", "Color", "Size", "Count"]
    if any("Wix ID" in d for d in data):
        cols.append("Wix ID")

    df = pd.DataFrame(data, columns=cols)
    try:
        df.to_excel("Bouquets.xlsx", index=False)
    except Exception as e:
        print(f"Error saving Bouquets.xlsx: {e}")

def get_wix_id_map():
    """Returns a dict mapping Wix ID -> Local Bouquet Name"""
    mapping = {}
    if os.path.exists("Bouquets.xlsx"):
        try:
            df = pd.read_excel("Bouquets.xlsx")
            if "Wix ID" in df.columns:
                # Filter rows with Wix ID
                valid = df[df["Wix ID"].notna()]
                for _, row in valid.iterrows():
                    wix_id = str(row["Wix ID"]).strip()
                    b_name = row["Bouquet Name"]
                    if wix_id and b_name:
                        mapping[wix_id] = b_name
        except Exception:
            pass
    return mapping

def set_bouquet_wix_id(bouquet_name, wix_id):
    """Updates the Wix ID for a specific bouquet in Bouquets.xlsx"""
    # Simply load, update internal map, save
    all_bouquets = load_all_bouquets()
    
    # We need to inject the ID into the save process. 
    # Since save_all_bouquets reads from file to preserve ID, 
    # but we want to CHANGE it, we can't rely on it reading the OLD value.
    # We need to temporarily force the new value.
    # Actually, save_all_bouquets relies on reading the file to get 'existing_extra_data'.
    # So if we want to update it, we should modify the file directly or 
    # pass the override to save_all_bouquets?
    # Modifying save_all_bouquets signature is cleaner but affects callers.
    # Let's read, modify DF, and write.
    
    if os.path.exists("Bouquets.xlsx"):
        try:
            df = pd.read_excel("Bouquets.xlsx")
            if "Wix ID" not in df.columns:
                df["Wix ID"] = None
            
            # Ensure column is object/string
            df["Wix ID"] = df["Wix ID"].astype(object)
            
            # Update rows for this bouquet
            # Note: wix_id should be string
            if wix_id is None:
                df.loc[df["Bouquet Name"] == bouquet_name, "Wix ID"] = None
            else:
                df.loc[df["Bouquet Name"] == bouquet_name, "Wix ID"] = str(wix_id)
            
            # Optional: Clear this Wix ID from other bouquets to enforce 1-to-1?
            # Creating ambiguity if 1-to-many is allowed. Let's allow 1-to-many (multiple bouquets to one ID? No, one ID to multiple bouquets? No, wix_id is unique per product)
            # If wix_id maps to "Summer", and we set "Winter" to wix_id, then wix_id maps to "Winter". "Summer" keeps wix_id?
            # If "Summer" has "123", and "Winter" has "123". get_wix_id_map will return one or the other (last one iterated).
            # So we should probably clear "123" from other bouquets.
            if wix_id is not None:
                df.loc[(df["Wix ID"] == str(wix_id)) & (df["Bouquet Name"] != bouquet_name), "Wix ID"] = None

            df.to_excel("Bouquets.xlsx", index=False)
            return True
        except Exception as e:
            print(f"Error updating Wix ID: {e}")
            return False
    return False


class Bouquet:
    def __init__(self, name:str, based_on:str|None=None, load_existing:bool=False):
        self.name = name
        self.based_on = based_on
        self.flowers = []

        all_bouquets = load_all_bouquets()
            
        if name in all_bouquets:
            if not load_existing:
                raise ValueError(f"Bouquet '{name}' already exists")
            else:
                self.flowers = all_bouquets[name]
                return
        
        if based_on:
            self.name = f"{name} (based on {based_on})"
            # find the based_on bouquet and copy its flowers
            if based_on in all_bouquets:
                self.flowers = list(all_bouquets[based_on]) # Copy list
            else:
                raise ValueError(f"Bouquet '{based_on}' not found")
    
    @staticmethod
    def delete_bouquet(name):
        all_bouquets = load_all_bouquets()
        
        if name in all_bouquets:
            del all_bouquets[name]
            save_all_bouquets(all_bouquets)
        else:
            raise ValueError(f"Bouquet '{name}' not found")
    
    @staticmethod
    def rename_bouquet(old_name, new_name):
        all_bouquets = load_all_bouquets()

        if old_name not in all_bouquets:
            raise ValueError(f"Bouquet '{old_name}' not found.")
        
        if new_name in all_bouquets:
            raise ValueError(f"Bouquet '{new_name}' already exists.")

        all_bouquets[new_name] = all_bouquets.pop(old_name)
        save_all_bouquets(all_bouquets)

    def select_flower(self, flower: FlowerData, count=1):
        for _ in range(count):
            self.flowers.append(flower)

    def remove_flower(self, flower: FlowerData, count=1):
        for _ in range(count):
            for f in self.flowers:
                if f == flower:
                    self.flowers.remove(f)
                    break
        
    def flower_count(self):
        _flower_count = defaultdict(int)
        for flower in self.flowers:
            _flower_count[flower] += 1
        return _flower_count
    
    def save(self):
        all_bouquets = load_all_bouquets()
        all_bouquets[self.name] = self.flowers
        save_all_bouquets(all_bouquets)

if __name__ == "__main__":
    color = FlowerColors()
    size = FlowerSizes()
    types = FlowersTypes()
    
    Bouquet.delete_bouquet("צבעוני ורד")
    bouquet = Bouquet("צבעוני ורד")
    bouquet.select_flower(FlowerData(name="ורד", color="אדום", size="בינוני"), count=3)
    bouquet.select_flower(FlowerData(name="צבעוני", color="צהוב", size="בינוני"), count=4)
    bouquet.remove_flower(FlowerData(name="צבעוני", color="צהוב", size="בינוני"), count=2)
    print(bouquet.flower_count())
    bouquet.save()
    
    
    