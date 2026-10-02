"""Immutable metric parameters and stable USD paths for the workcell walls."""

from dataclasses import dataclass

FURNITURE_PATH = "/World/Furniture"
ROOM_PATH = FURNITURE_PATH + "/Room"
PARTITION_PATH = FURNITURE_PATH + "/ChairSideGlass"
RED_WALL_PATH = FURNITURE_PATH + "/RedWall"
PAINT_PATH = FURNITURE_PATH + "/Paint"
GLASS_PATH = ROOM_PATH + "/Glass"


@dataclass(frozen=True)
class FurnitureLayout:
    """Boards and their adjoining painted L wall, in meters."""

    board_widths: tuple[float, ...] = (2.0, 1.4)
    board_height: float = 2.5
    board_thickness: float = 0.018
    wall_height: float = 3.0
    wall_thickness: float = 0.14605
    short_wall_length: float = 0.642

    @property
    def board_run_length(self) -> float:
        """Total width of the adjoining boards."""
        return sum(self.board_widths)


# One cohesive dimensional specification, without artificial nested groups.
@dataclass(frozen=True)
class RoomLayout:  # pylint: disable=too-many-instance-attributes
    """Far-end wall with two framed clear glass openings, in meters."""

    height: float = 3.0
    thickness: float = 0.08
    far_wall_length: float = 0.3
    end_width: float = 0.3556
    end_depth: float = 0.1524
    glass_widths: tuple[float, ...] = (2.3749, 1.2192)
    glass_height: float = 2.4
    glass_bottom: float = 0.4064
    border: float = 0.0381
    glass_thickness: float = 0.02

    @property
    def frame_bottom(self) -> float:
        """Bottom of the glass's outer border."""
        return self.glass_bottom - self.border

    @property
    def frame_top(self) -> float:
        """Top of the glass's outer border."""
        return self.glass_bottom + self.glass_height + self.border

    @property
    def openings_length(self) -> float:
        """Total width of both complete framed openings."""
        return sum(self.glass_widths) + 4 * self.border

    @property
    def length(self) -> float:
        """Openings plus the remaining solid wall."""
        return self.openings_length + self.far_wall_length


# Pane and skirting dimensions belong to the same repeated unit.
@dataclass(frozen=True)
class PartitionLayout:  # pylint: disable=too-many-instance-attributes
    """Straight and turning glass units with metal skirting, in meters."""

    straight_count: int = 3
    bend_count: int = 5
    turn_deg: float = 18
    clear_width: float = 0.8128
    edge_width: float = 0.005
    height: float = 3.0
    glass_thickness: float = 0.02
    skirt_height: float = 0.10
    skirt_thickness: float = 0.03

    @property
    def count(self) -> int:
        """Number of panels in the complete run."""
        return self.straight_count + self.bend_count

    @property
    def pitch(self) -> float:
        """One clear pane and its two edge strips."""
        return self.clear_width + 2 * self.edge_width

    @property
    def length(self) -> float:
        """Complete centerline path length."""
        return self.count * self.pitch


@dataclass(frozen=True)
class RedWallLayout:
    """Exterior matte wall and reference pane index."""

    length: float = 3.0
    height: float = 3.0
    thickness: float = 0.10
    gap: float = 3.0
    turning_panel: int = 3


FURNITURE = FurnitureLayout()
ROOM = RoomLayout()
PARTITION = PartitionLayout()
RED_WALL = RedWallLayout()
RED_WALL_REFERENCE = (
    PARTITION_PATH + "/Unit" + str(PARTITION.straight_count + RED_WALL.turning_panel)
)
