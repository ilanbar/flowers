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
import numpy as np # Added for NaN handling

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
            has_wix_id = "Wix ID" in old_df.columns
            has_wix_cat = "Wix Category" in old_df.columns
            
            if has_wix_id or has_wix_cat:
                 # Group by bouquet name and take the first value (assuming same ID for whole bouquet)
                 for name, group in old_df.groupby("Bouquet Name"):
                     extra = {}
                     if has_wix_id:
                         valid_ids = group["Wix ID"].dropna()
                         if not valid_ids.empty:
                             first_valid = valid_ids.iloc[0]
                             extra["Wix ID"] = str(first_valid)
                     if has_wix_cat:
                         valid_cats = group["Wix Category"].dropna()
                         if not valid_cats.empty:
                             first_cat = valid_cats.iloc[0]
                             extra["Wix Category"] = str(first_cat)
                             
                     if extra:
                         existing_extra_data[name] = extra
        except Exception:
            pass

    data = []
    for b_name, flowers in all_bouquets.items():
        # Get extra data
        extra = existing_extra_data.get(b_name, {})
        wix_id = extra.get("Wix ID", None)
        wix_cat = extra.get("Wix Category", None)

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
            if wix_cat:
                row["Wix Category"] = wix_cat
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
            if wix_cat:
                row["Wix Category"] = wix_cat
            data.append(row)
    
    # columns order
    cols = ["Bouquet Name", "Flower Name", "Color", "Size", "Count"]
    if any("Wix ID" in d for d in data):
        cols.append("Wix ID")
    if any("Wix Category" in d for d in data):
        cols.append("Wix Category")

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

def get_bouquet_wix_data():
    """Returns a dict mapping Bouquet Name -> {'id': ..., 'category': ...}"""
    mapping = {}
    if os.path.exists("Bouquets.xlsx"):
        try:
            df = pd.read_excel("Bouquets.xlsx")
            required_cols = {"Bouquet Name"}
            if not required_cols.issubset(df.columns):
                return mapping
            
            # Check existing columns
            has_wix_id = "Wix ID" in df.columns
            has_wix_cat = "Wix Category" in df.columns
            
            if has_wix_id:
                grouped = df.groupby("Bouquet Name")
                for name, group in grouped:
                    # Get first non-null Wix ID
                    valid_ids = group["Wix ID"].dropna()
                    if not valid_ids.empty:
                        first_valid = valid_ids.iloc[0]
                        data = {"id": str(first_valid)}
                        if has_wix_cat:
                             valid_cats = group["Wix Category"].dropna()
                             if not valid_cats.empty:
                                 cat = valid_cats.iloc[0]
                                 data["category"] = str(cat)
                        mapping[name] = data
        except Exception as e:
            print(f"Error loading bouquet WIX data: {e}")
            pass
    return mapping

def set_bouquet_wix_id(bouquet_name, wix_id, wix_category=None):
    """Updates the Wix ID for a specific bouquet in Bouquets.xlsx"""
    # Simply load, update internal map, save
    # all_bouquets = load_all_bouquets() # Not needed if we edit DF directly
    
    if os.path.exists("Bouquets.xlsx"):
        try:
            df = pd.read_excel("Bouquets.xlsx")
            if "Wix ID" not in df.columns:
                df["Wix ID"] = None
            if "Wix Category" not in df.columns:
                df["Wix Category"] = None
            
            # Ensure column is object/string
            df["Wix ID"] = df["Wix ID"].astype(object)
            df["Wix Category"] = df["Wix Category"].astype(object)
            
            # Update rows for this bouquet
            # Note: wix_id should be string
            if wix_id is None:
                # Need to use None or np.nan, but usually None works for object column
                # However, simple assignment might not work if it's considered scalar vs series
                df.loc[df["Bouquet Name"] == bouquet_name, "Wix ID"] = np.nan
                df.loc[df["Bouquet Name"] == bouquet_name, "Wix Category"] = np.nan
            else:
                df.loc[df["Bouquet Name"] == bouquet_name, "Wix ID"] = str(wix_id)
                if wix_category:
                    df.loc[df["Bouquet Name"] == bouquet_name, "Wix Category"] = str(wix_category)
                else:
                    # Keep existing category if not provided? Or clear it? 
                    # If we set ID, usually meaningful to set Category or clear it if it's a new link.
                    # But if we just update ID without category info, we might want to keep it?
                    # Let's assume passed None means "unknown", so maybe keep existing if any, or clear?
                    # Safer to clear if we don't know, to avoid mismatch.
                    # But the caller might not know category.
                    # Let's leave it as is if None.
                    pass
            
            # Optional: Clear this Wix ID from other bouquets to enforce 1-to-1?
            if wix_id is not None:
                mask = (df["Wix ID"] == str(wix_id)) & (df["Bouquet Name"] != bouquet_name)
                df.loc[mask, "Wix ID"] = np.nan
                df.loc[mask, "Wix Category"] = np.nan

            df.to_excel("Bouquets.xlsx", index=False)
            return True
        except Exception as e:
            print(f"Error updating Wix ID: {e}")
            return False
    return False

def update_wix_categories_batch(updates):
    """
    Updates Wix categories for multiple bouquets at once.
    updates: dict {bouquet_name: (wix_id, category_name)}
    """
    if not updates or not os.path.exists("Bouquets.xlsx"):
        return False

    try:
        df = pd.read_excel("Bouquets.xlsx")
        if "Wix ID" not in df.columns:
            df["Wix ID"] = None
        if "Wix Category" not in df.columns:
            df["Wix Category"] = None
        
        df["Wix ID"] = df["Wix ID"].astype(object)
        df["Wix Category"] = df["Wix Category"].astype(object)
        
        changed = False
        for name, (wix_id, category) in updates.items():
            if not category:
                continue
                
            # Filter rows for this bouquet
            mask = df["Bouquet Name"] == name
            if not df.loc[mask].empty:
                # Only update if the Wix ID matches (double check validity)
                # Or just force update if we trust the caller
                current_id_series = df.loc[mask, "Wix ID"]
                
                # Check if we are updating the correct link
                # Logic: If Wix ID matches the one we want to update category for
                # Using str() for comparison
                
                # Let's simplify: Update category for all rows of this bouquet 
                # where Wix ID matches the provided ID
                
                # Iterate indices to be safe
                for idx in df.index[mask]:
                    current_id = df.at[idx, "Wix ID"]
                    if pd.isna(current_id):
                        continue
                        
                    if str(current_id) == str(wix_id):
                        df.at[idx, "Wix Category"] = str(category)
                        changed = True
        
        if changed:
            df.to_excel("Bouquets.xlsx", index=False)
            return True
            
    except Exception as e:
        print(f"Error executing batch update: {e}")
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
    
    
    