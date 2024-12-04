"""Map model classes for handling map nodes and POIs."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any

import structlog

logger = structlog.get_logger()


@dataclass
class MapMetadata:
    """
    Stores metadata for map dimensions and scale.

    Args:
        width (int): Width of the map in pixels
        height (int): Height of the map in pixels
        scale (float): Map scale (units per pixel)
        unit (str): Unit of measurement (e.g., 'm', 'km')
    """

    width: int
    height: int
    scale: float
    unit: str

    def validate_scale(self, config: "Config") -> None:
        """
        Validate scale is within configured limits.

        Args:
            config: Application configuration

        Raises:
            ValueError: If scale is invalid
        """
        if not config.MIN_MAP_SCALE <= self.scale <= config.MAX_MAP_SCALE:
            raise ValueError(
                f"Map scale must be between {config.MIN_MAP_SCALE} and {config.MAX_MAP_SCALE}"
            )
        if self.unit not in config.SUPPORTED_MAP_UNITS:
            raise ValueError(f"Map unit must be one of {config.SUPPORTED_MAP_UNITS}")


@dataclass
class POICoordinate:
    """
    Represents a Point of Interest on the map.

    Args:
        x (float): X coordinate in pixels
        y (float): Y coordinate in pixels
        node_name (str): Name of the referenced node
        icon (Optional[str]): Optional icon identifier
    """

    x: float
    y: float
    node_name: str
    icon: Optional[str] = None

    def validate_position(self, width: int, height: int) -> bool:
        """
        Check if POI coordinates are within map bounds.

        Args:
            width (int): Map width in pixels
            height (int): Map height in pixels

        Returns:
            bool: True if position is valid
        """
        return 0 <= self.x <= width and 0 <= self.y <= height


class MapNode:
    """
    Handles map data and operations.

    Args:
        name (str): Name of the map node
        config (Config): Application configuration
    """

    def __init__(self, name: str, config: "Config") -> None:
        """Initialize map node."""
        self.name = name
        self.config = config
        self.metadata: Optional[MapMetadata] = None
        self.pois: List[POICoordinate] = []
        self.image_path: Optional[str] = None

    def validate(self) -> None:
        """
        Validate map node data.

        Raises:
            ValueError: If validation fails
        """
        if len(self.name) > self.config.MAX_MAP_NAME_LENGTH:
            raise ValueError(
                f"Map name exceeds maximum length of {self.config.MAX_MAP_NAME_LENGTH}"
            )

        if len(self.pois) > self.config.MAX_POI_COUNT:
            raise ValueError(
                f"POI count exceeds maximum of {self.config.MAX_POI_COUNT}"
            )

        if self.metadata:
            self.metadata.validate_scale(self.config)

            # Validate POI positions
            invalid_pois = [
                poi
                for poi in self.pois
                if not poi.validate_position(self.metadata.width, self.metadata.height)
            ]
            if invalid_pois:
                raise ValueError(
                    f"Invalid POI positions for: {[poi.node_name for poi in invalid_pois]}"
                )

    def add_poi(
        self, node_name: str, x: float, y: float, icon: Optional[str] = None
    ) -> None:
        """
        Add a POI to the map.

        Args:
            node_name (str): Name of the referenced node
            x (float): X coordinate
            y (float): Y coordinate
            icon (Optional[str]): Optional icon identifier

        Raises:
            ValueError: If POI cannot be added
        """
        if not self.metadata:
            raise ValueError("Map metadata not set. Set map dimensions first.")

        if len(self.pois) >= self.config.MAX_POI_COUNT:
            raise ValueError(
                f"Maximum POI count ({self.config.MAX_POI_COUNT}) exceeded"
            )

        poi = POICoordinate(x=x, y=y, node_name=node_name, icon=icon)
        if not poi.validate_position(self.metadata.width, self.metadata.height):
            raise ValueError(f"Coordinates ({x}, {y}) out of map bounds")

        # Check for duplicate node reference
        if node_name in (p.node_name for p in self.pois):
            raise ValueError(f"POI for node '{node_name}' already exists")

        self.pois.append(poi)
        logger.info(
            "Added POI to map", map_name=self.name, node_name=node_name, x=x, y=y
        )

    def move_poi(self, node_name: str, new_x: float, new_y: float) -> None:
        """
        Move an existing POI to a new position.

        Args:
            node_name (str): Name of the POI's node
            new_x (float): New X coordinate
            new_y (float): New Y coordinate

        Raises:
            ValueError: If move is invalid
        """
        if not self.metadata:
            raise ValueError("Map metadata not set")

        # Validate new position
        if not (
            0 <= new_x <= self.metadata.width and 0 <= new_y <= self.metadata.height
        ):
            raise ValueError(f"Coordinates ({new_x}, {new_y}) out of map bounds")

        # Find and update POI
        for poi in self.pois:
            if poi.node_name == node_name:
                poi.x = new_x
                poi.y = new_y
                logger.info(
                    "Moved POI",
                    map_name=self.name,
                    node_name=node_name,
                    new_x=new_x,
                    new_y=new_y,
                )
                return

        raise ValueError(f"POI '{node_name}' not found on map")

    def remove_poi(self, node_name: str) -> None:
        """
        Remove a POI from the map.

        Args:
            node_name (str): Name of the POI to remove

        Raises:
            ValueError: If POI not found
        """
        original_count = len(self.pois)
        self.pois = [poi for poi in self.pois if poi.node_name != node_name]

        if len(self.pois) == original_count:
            raise ValueError(f"POI '{node_name}' not found on map")

        logger.info("Removed POI from map", map_name=self.name, node_name=node_name)

    def get_neo4j_properties(self) -> Dict[str, Any]:
        """
        Get map properties for Neo4j storage.

        Returns:
            Dict[str, Any]: Properties for Neo4j node
        """
        properties = {
            "name": self.name,
            "labels": ["Node", "Map"],
            "additional_properties": {},
        }

        if self.metadata:
            properties["additional_properties"].update(
                {
                    "map_width": self.metadata.width,
                    "map_height": self.metadata.height,
                    "map_scale": self.metadata.scale,
                    "map_unit": self.metadata.unit,
                }
            )

        if self.image_path:
            properties["additional_properties"]["map_image_path"] = str(self.image_path)

        return properties

    def get_neo4j_relationships(self) -> List[tuple]:
        """
        Get POI relationships for Neo4j storage.

        Returns:
            List[tuple]: List of relationship tuples (type, target, direction, props)
        """
        relationships = []
        for poi in self.pois:
            props = {"x": poi.x, "y": poi.y}
            if poi.icon:
                props["icon"] = poi.icon

            relationships.append(("CONTAINS", poi.node_name, ">", props))

        return relationships

    @classmethod
    def from_neo4j_data(cls, data: Dict[str, Any], config: "Config") -> "MapNode":
        """
        Create MapNode from Neo4j data.

        Args:
            data (Dict[str, Any]): Neo4j node data
            config (Config): Application configuration

        Returns:
            MapNode: Created map node instance
        """
        map_node = cls(data["n"]["name"], config)

        # Extract metadata
        props = data.get("additional_properties", {})
        if all(
            k in props for k in ["map_width", "map_height", "map_scale", "map_unit"]
        ):
            map_node.metadata = MapMetadata(
                width=props["map_width"],
                height=props["map_height"],
                scale=props["map_scale"],
                unit=props["map_unit"],
            )

        # Set image path if exists
        if "map_image_path" in props:
            map_node.image_path = props["map_image_path"]

        # Load POIs from relationships
        for rel in data.get("relationships", []):
            if rel[0] == "CONTAINS" and "x" in rel[3] and "y" in rel[3]:
                map_node.pois.append(
                    POICoordinate(
                        x=rel[3]["x"],
                        y=rel[3]["y"],
                        node_name=rel[1],
                        icon=rel[3].get("icon"),
                    )
                )

        return map_node
