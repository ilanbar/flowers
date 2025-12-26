from pydantic import BaseModel
from collections import namedtuple

FlowerData = namedtuple('FlowerData', ['name', 'color', 'size'])

from attributes import (
    FlowerColor, 
    FlowerSize
)

class Flower(BaseModel):
    name: str
    color: FlowerColor
    size: FlowerSize = FlowerSize.DEFAULT

    def data(self):
        return FlowerData(
            name=self.name,
            color=self.color.value,
            size=self.size.value
        )
    
    