from typing import Dict, Any, List

from models.property_model import PropertyItem
from utils.property_utils import validate_property_key, transform_property_value


class PropertyService:
    def __init__(self, config):
        self.reserved_keys = set(config.RESERVED_PROPERTY_KEYS)

    def process_properties(self, properties: List[PropertyItem]) -> Dict[str, Any]:
        """
        Process a list of property items into a final properties dictionary.

        Args:
            properties: List of PropertyItem objects

        Returns:
            Dict[str, Any]: Processed properties
        """
        result = {}

        for prop in properties:
            if not prop:
                continue

            validate_property_key(prop.key, self.reserved_keys)
            result[prop.key] = transform_property_value(prop.value)

        return result