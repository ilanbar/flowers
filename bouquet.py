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
    data = []
    for b_name, flowers in all_bouquets.items():
        # Count flowers
        counts = defaultdict(int)
        for f in flowers:
            counts[f] += 1
        
        for f, count in counts.items():
            data.append({
                "Bouquet Name": b_name,
                "Flower Name": f.name,
                "Color": f.color,
                "Size": f.size,
                "Count": count
            })
    
    df = pd.DataFrame(data, columns=["Bouquet Name", "Flower Name", "Color", "Size", "Count"])
    try:
        df.to_excel("Bouquets.xlsx", index=False)
    except Exception as e:
        print(f"Error saving Bouquets.xlsx: {e}")

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
    
    
    