"""Service for handling map operations and image storage."""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Callable

import structlog
from PIL import Image

from models.map_model import MapNode, MapMetadata

logger = structlog.get_logger()


class MapService:
    """
    Service for managing maps and their images.

    Args:
        model: Neo4j model instance
        config: Application configuration
        worker_manager: Worker manager service
        error_handler: Error handler instance
    """

    def __init__(
        self,
        model: "Neo4jModel",
        config: "Config",
        worker_manager: "WorkerManagerService",
        error_handler: "ErrorHandler",
    ) -> None:
        self.model = model
        self.config = config
        self.worker_manager = worker_manager
        self.error_handler = error_handler
        self.current_map: Optional[MapNode] = None

        # Ensure image storage directory exists
        self.image_dir = Path(self.config.MAP_IMAGES_PATH)
        self.image_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Map service initialized", image_dir=str(self.image_dir))

    def validate_image(self, image_path: str) -> bool:
        """
        Validate map image size and dimensions.

        Args:
            image_path: Path to image file

        Returns:
            bool: True if image is valid

        Raises:
            ValueError: If image is invalid
        """
        try:
            # Check file size
            if os.path.getsize(image_path) > self.config.MAX_MAP_IMAGE_SIZE_BYTES:
                raise ValueError(
                    f"Image exceeds maximum size of {self.config.MAX_MAP_IMAGE_SIZE_BYTES} bytes"
                )

            # Check dimensions
            with Image.open(image_path) as img:
                width, height = img.size
                if (
                    width > self.config.MAX_MAP_DIMENSION
                    or height > self.config.MAX_MAP_DIMENSION
                ):
                    raise ValueError(
                        f"Image dimensions exceed maximum of {self.config.MAX_MAP_DIMENSION}px"
                    )

                # Verify image can be read
                img.verify()

            return True

        except Exception as e:
            self.error_handler.handle_error(f"Invalid map image: {str(e)}")
            return False

    def _store_image(self, image_path: str, map_name: str) -> str:
        """
        Store map image with optimization.

        Args:
            image_path: Source image path
            map_name: Name of the map

        Returns:
            str: Path to stored image
        """
        # Create map directory
        map_dir = self.image_dir / map_name
        map_dir.mkdir(exist_ok=True)

        # Generate unique filename
        timestamp = int(os.path.getmtime(image_path))
        image_hash = hashlib.md5(f"{map_name}_{timestamp}".encode()).hexdigest()
        stored_path = map_dir / f"{image_hash}.png"

        # Optimize and save image
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Save with optimization
            img.save(stored_path, "PNG", optimize=True)

        logger.info(
            "Stored map image",
            map_name=map_name,
            image_hash=image_hash,
            path=str(stored_path),
        )

        return str(stored_path)

    def _cleanup_old_images(self, map_name: str, current_path: Optional[str]) -> None:
        """
        Remove old images for a map.

        Args:
            map_name: Name of the map
            current_path: Path to current image to preserve
        """
        map_dir = self.image_dir / map_name
        if map_dir.exists():
            for image_file in map_dir.glob("*.png"):
                if str(image_file) != current_path:
                    image_file.unlink()
                    logger.info(
                        "Deleted old map image", map_name=map_name, path=str(image_file)
                    )

    def load_map(self, name: str, callback: Callable) -> None:
        """
        Load a map node and its data.

        Args:
            name: Name of the map to load
            callback: Function to call with loaded map
        """

        def handle_map_data(data: list) -> None:
            if not data:
                self.error_handler.handle_error(f"Map '{name}' not found")
                return

            try:
                record = data[0]
                self.current_map = MapNode.from_neo4j_data(record, self.config)
                callback(self.current_map)

            except Exception as e:
                self.error_handler.handle_error(f"Error loading map: {str(e)}")

        self.model.load_node(name, handle_map_data)

    def save_map(
        self, node_data: Dict[str, Any], image_path: Optional[str], callback: Callable
    ) -> None:
        """
        Save or update a map node.

        Args:
            node_data: Base node data
            image_path: Optional path to new image
            callback: Function to call after save
        """
        try:
            # Create or update map node
            map_node = self.current_map or MapNode(node_data["name"], self.config)

            # Handle new image if provided
            if image_path:
                if not self.validate_image(image_path):
                    return

                # Store and get new path
                stored_path = self._store_image(image_path, map_node.name)

                # Update map metadata and path
                with Image.open(stored_path) as img:
                    width, height = img.size
                    map_node.metadata = MapMetadata(
                        width=width,
                        height=height,
                        scale=(
                            map_node.metadata.scale
                            if map_node.metadata
                            else self.config.DEFAULT_MAP_SCALE
                        ),
                        unit=(
                            map_node.metadata.unit
                            if map_node.metadata
                            else self.config.DEFAULT_MAP_UNIT
                        ),
                    )
                map_node.image_path = stored_path

                # Clean up old images
                self._cleanup_old_images(map_node.name, stored_path)

            # Validate map data
            map_node.validate()

            # Prepare Neo4j data
            neo4j_data = map_node.get_neo4j_properties()
            neo4j_data.update(node_data)

            # Add relationships for POIs
            neo4j_data["relationships"] = map_node.get_neo4j_relationships()

            # Save through Neo4j model
            self.model.save_node(neo4j_data, callback)

        except Exception as e:
            self.error_handler.handle_error(f"Error saving map: {str(e)}")

    def delete_map(self, name: str, callback: Callable) -> None:
        """
        Delete a map and its images.

        Args:
            name: Name of the map to delete
            callback: Function to call after deletion
        """
        try:
            # Delete images
            map_dir = self.image_dir / name
            if map_dir.exists():
                shutil.rmtree(map_dir)
                logger.info("Deleted map images", map_name=name)

            # Delete node
            self.model.delete_node(name, callback)

        except Exception as e:
            self.error_handler.handle_error(f"Error deleting map: {str(e)}")

    def calculate_distance(self, poi1_name: str, poi2_name: str) -> Optional[float]:
        """
        Calculate real-world distance between two POIs.

        Args:
            poi1_name: Name of first POI
            poi2_name: Name of second POI

        Returns:
            float: Distance in map units, or None if calculation failed
        """
        if not self.current_map or not self.current_map.metadata:
            return None

        try:
            # Find POIs
            poi1 = next(
                (p for p in self.current_map.pois if p.node_name == poi1_name), None
            )
            poi2 = next(
                (p for p in self.current_map.pois if p.node_name == poi2_name), None
            )

            if not poi1 or not poi2:
                return None

            # Calculate pixel distance
            pixel_distance = ((poi2.x - poi1.x) ** 2 + (poi2.y - poi1.y) ** 2) ** 0.5

            # Convert to real-world units using scale
            return pixel_distance * self.current_map.metadata.scale

        except Exception as e:
            self.error_handler.handle_error(f"Error calculating distance: {str(e)}")
            return None
