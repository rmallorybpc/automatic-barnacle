"""Module indexing for feature mentions."""
import os
import json
from typing import List, Dict
import yaml

from .models import Feature
from .utils import setup_logging, validate_file_exists


logger = setup_logging(__name__)


class ModulesIndex:
    """Index features by module/product area."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.index = {}
    
    def load_features(self, features_path: str = "data/features.json") -> List[Feature]:
        """Load features from file.
        
        Args:
            features_path: Path to features JSON file
            
        Returns:
            List of Feature objects
        """
        if not validate_file_exists(features_path, logger):
            logger.error(f"Cannot load features: file not found")
            return []
        
        try:
            with open(features_path, 'r') as f:
                data = json.load(f)
            
            features = [Feature.from_dict(item) for item in data]
            logger.info(f"Loaded {len(features)} features")
            return features
        except Exception as e:
            logger.error(f"Failed to load features: {e}")
            return []
    
    def build_index(self, features: List[Feature]) -> Dict[str, List[Feature]]:
        """Build index of features by product area.
        
        Args:
            features: List of Feature objects
            
        Returns:
            Dictionary mapping product areas to features
        """
        logger.info("Building feature index")
        
        index = {}
        for feature in features:
            area = feature.product_area or "Unknown"
            if area not in index:
                index[area] = []
            index[area].append(feature)
        
        logger.info(f"Created index with {len(index)} product areas")
        self.index = index
        return index
    
    def save_index(self, output_path: str = "data/feature_index.json") -> bool:
        """Save index to file.
        
        Args:
            output_path: Path to output file
            
        Returns:
            True on success, False on failure
        """
        if not self.index:
            logger.warning("No index to save")
            return False
        
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Convert to serializable format
            index_data = {
                area: [f.to_dict() for f in features]
                for area, features in self.index.items()
            }
            
            with open(output_path, 'w') as f:
                json.dump(index_data, f, indent=2)
            
            logger.info(f"Saved index to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            return False


def main():
    """Main entry point for indexing."""
    import sys
    
    try:
        indexer = ModulesIndex()
        features = indexer.load_features()
        
        if not features:
            logger.error("No features to index")
            return 1
        
        indexer.build_index(features)
        
        if not indexer.save_index():
            logger.error("Failed to save index")
            return 1
        
        print(f"\nIndexed {len(features)} features into {len(indexer.index)} product areas")
        for area, features in sorted(indexer.index.items()):
            print(f"  - {area}: {len(features)} features")
        
        return 0
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
