from dataclasses import dataclass


@dataclass
class Coords:
    x: float
    y: float


@dataclass
class Boundaries:
    top_right: Coords
    bottom_right: Coords
    top_left: Coords
    bottom_left: Coords

    @staticmethod
    def from_dict(d: dict):
        return Boundaries(
            top_right=Coords(**d["top_right"]),
            bottom_right=Coords(**d["bottom_right"]),
            top_left=Coords(**d["top_left"]),
            bottom_left=Coords(**d["bottom_left"]),
        )


def to_dict(b: Boundaries):
    return {
        "top_right": vars(b.top_right),
        "bottom_right": vars(b.bottom_right),
        "top_left": vars(b.top_left),
        "bottom_left": vars(b.bottom_left),
    }
