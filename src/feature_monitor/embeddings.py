"""Embeddings generation for features."""
import os
import json
from typing import List, Optional
import yaml

from .models import Feature
from .utils import setup_logging, validate_file_exists


logger = setup_logging(__name__)


class EmbeddingsGenerator:
    """Generate embeddings for features."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.embeddings_config = self.config.get('embeddings', {})
    
    def load_features(self, features_path: str = "data/features.json") -> List[Feature]:
        """Load features from file.
        
        Args:
            features_path: Path to features JSON file
            
        Returns:
            List of Feature objects
        """
        if not validate_file_exists(features_path, logger):
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
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text.
        
        In a real implementation, this would call OpenAI or another provider.
        For now, we'll create a simple mock embedding.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None on failure
        """
        # Mock embedding - in production, use actual API
        import hashlib
        
        # Create deterministic "embedding" based on text hash
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to list of floats (normalized between -1 and 1)
        embedding = [(b / 255.0 * 2.0 - 1.0) for b in hash_bytes]
        
        # Pad to typical embedding size (e.g., 1536 for text-embedding-ada-002)
        while len(embedding) < 1536:
            embedding.extend(embedding[:min(16, 1536 - len(embedding))])
        
        return embedding[:1536]
    
    def generate_embeddings(self, features: List[Feature]) -> List[Feature]:
        """Generate embeddings for all features.
        
        Args:
            features: List of Feature objects
            
        Returns:
            Features with embeddings added
        """
        logger.info(f"Generating embeddings for {len(features)} features")
        
        for i, feature in enumerate(features):
            # Combine title and description for embedding
            text = f"{feature.title}\n{feature.description}"
            
            embedding = self.generate_embedding(text)
            if embedding:
                feature.embedding = embedding
                logger.info(f"Generated embedding {i+1}/{len(features)}: {feature.title}")
            else:
                logger.warning(f"Failed to generate embedding for: {feature.title}")
        
        return features
    
    def save_features_with_embeddings(
        self,
        features: List[Feature],
        output_path: str = "data/embeddings/features_with_embeddings.json"
    ) -> bool:
        """Save features with embeddings.
        
        Args:
            features: List of Feature objects with embeddings
            output_path: Path to output file
            
        Returns:
            True on success, False on failure
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            features_data = [f.to_dict() for f in features]
            
            with open(output_path, 'w') as f:
                json.dump(features_data, f, indent=2)
            
            logger.info(f"Saved {len(features)} features with embeddings to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save features with embeddings: {e}")
            return False


def main():
    """Main entry point for embeddings generation."""
    import sys
    
    try:
        generator = EmbeddingsGenerator()
        features = generator.load_features()
        
        if not features:
            logger.error("No features to generate embeddings for")
            return 1
        
        features_with_embeddings = generator.generate_embeddings(features)
        
        if not generator.save_features_with_embeddings(features_with_embeddings):
            logger.error("Failed to save features with embeddings")
            return 1
        
        embedded_count = sum(1 for f in features_with_embeddings if f.embedding)
        print(f"\nGenerated embeddings for {embedded_count}/{len(features)} features")
        
        return 0
    except Exception as e:
        logger.error(f"Embeddings generation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
