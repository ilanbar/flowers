
from flower import FlowerData
from collections import defaultdict

class Bouquet:
    def __init__(self):
        self.flowers = []

    def add_flower(self, flower: FlowerData, count=1):
        for _ in range(count):
            self.flowers.append(flower)

    def remove_flower(self, flower: FlowerData, count=1):
        for _ in range(count):
            self.flowers.remove(flower)
        
    def flower_count(self):
        _flower_count = defaultdict(int)
        for flower in self.flowers:
            _flower_count[flower.data()] += 1
        return _flower_count
    
