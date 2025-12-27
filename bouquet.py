from flower import (
    FlowerData, 
    FlowersTypes,
    FlowerColors,
    FlowerSizes,
)
from collections import defaultdict
import json

class Bouquet:
    def __init__(self, name:str, based_on:str|None=None, load_existing:bool=False):
        self.name = name
        self.based_on = based_on
        self.flowers = []

        try:
            with open("Bouquets.json", "r", encoding="utf-8") as b:
                all_bouquets = json.load(b)
        except (FileNotFoundError, json.JSONDecodeError):
            all_bouquets = {}
            
        if name in all_bouquets:
            if not load_existing:
                raise ValueError(f"Bouquet '{name}' already exists in Bouquets.json")
            else:
                self.flowers = [FlowerData(*f) for f in all_bouquets[name]]
                return
        
        if based_on:
            self.name = f"{name} (based on {based_on})"
            # find the based_on bouquet and copy its flowers
            if based_on in all_bouquets:
                self.flowers = all_bouquets[based_on]
            else:
                raise ValueError(f"Bouquet '{based_on}' not found in Bouquets.json")
    
    @staticmethod
    def delete_bouquet(name):
        with open("Bouquets.json", "r", encoding="utf-8") as b:
            all_bouquets = json.load(b)
        
        if name in all_bouquets:
            del all_bouquets[name]
            with open("Bouquets.json", "w", encoding="utf-8") as b:
                json.dump(all_bouquets, b, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"Bouquet '{name}' not found in Bouquets.json")
    
    @staticmethod
    def rename_bouquet(old_name, new_name):
        try:
            with open("Bouquets.json", "r", encoding="utf-8") as b:
                all_bouquets = json.load(b)
        except (FileNotFoundError, json.JSONDecodeError):
            raise ValueError("Database not found.")

        if old_name not in all_bouquets:
            raise ValueError(f"Bouquet '{old_name}' not found.")
        
        if new_name in all_bouquets:
            raise ValueError(f"Bouquet '{new_name}' already exists.")

        all_bouquets[new_name] = all_bouquets.pop(old_name)
        
        with open("Bouquets.json", "w", encoding="utf-8") as b:
            json.dump(all_bouquets, b, ensure_ascii=False, indent=2)

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
        try:
            with open("Bouquets.json", "r", encoding="utf-8") as b:
                all_bouquets = json.load(b)
        except (FileNotFoundError, json.JSONDecodeError):
            all_bouquets = {}

        all_bouquets[self.name] = self.flowers

        with open("Bouquets.json", "w", encoding="utf-8") as b:
            json.dump(all_bouquets, b, ensure_ascii=False, indent=2)

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
    
    
    