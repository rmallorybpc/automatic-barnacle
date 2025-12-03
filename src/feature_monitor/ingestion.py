"""Ingestion module for fetching GitHub product updates."""
import os
import json
from datetime import datetime
from typing import List
import yaml

from .models import Feature
from .graphql_diff import GraphQLSchemaDiff
from .utils import setup_logging, safe_request, safe_write_file


logger = setup_logging(__name__)


class FeatureIngestion:
    """Handles ingestion of features from multiple sources."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        if not os.path.exists(config_path):
            logger.error(f"Configuration file not found: {config_path}")
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.sources = self.config.get('sources', {})
        self.features = []
    
    def fetch_changelog(self) -> List[Feature]:
        """Fetch features from GitHub changelog.
        
        Returns:
            List of Feature objects
        """
        features = []
        
        if not self.sources.get('changelog', {}).get('enabled', False):
            logger.info("Changelog source is disabled")
            return features
        
        url = self.sources['changelog'].get('url')
        if not url:
            logger.error("No changelog URL configured")
            return features
        
        logger.info(f"Fetching changelog from {url}")
        response = safe_request(url, logger=logger)
        
        if not response:
            logger.error("Failed to fetch changelog")
            return features
        
        # Parse changelog (simplified - in real implementation would parse HTML)
        # For now, create a sample feature
        feature = Feature(
            id=f"changelog_sample_{datetime.now().strftime('%Y%m%d')}",
            title="GitHub Changelog Update",
            description="Sample changelog entry - implement HTML parsing for real data",
            source_type="changelog",
            source_url=url,
            product_area="Platform",
            tags=["changelog"]
        )
        features.append(feature)
        logger.info(f"Fetched {len(features)} features from changelog")
        
        return features
    
    def fetch_roadmap(self) -> List[Feature]:
        """Fetch features from GitHub roadmap.
        
        Returns:
            List of Feature objects
        """
        features = []
        
        if not self.sources.get('roadmap', {}).get('enabled', False):
            logger.info("Roadmap source is disabled")
            return features
        
        url = self.sources['roadmap'].get('url')
        if not url:
            logger.error("No roadmap URL configured")
            return features
        
        logger.info(f"Fetching roadmap from {url}")
        
        # For GitHub roadmap, we'd use the API
        api_url = "https://api.github.com/repos/github/roadmap/issues?state=all&per_page=10"
        response = safe_request(api_url, logger=logger)
        
        if not response:
            logger.error("Failed to fetch roadmap")
            return features
        
        try:
            issues = response.json()
            logger.info(f"Found {len(issues)} roadmap items")
            
            for issue in issues:
                feature = Feature(
                    id=f"roadmap_{issue['number']}",
                    title=issue['title'],
                    description=issue['body'] or "No description",
                    source_type="roadmap",
                    source_url=issue['html_url'],
                    product_area="GitHub",
                    tags=["roadmap"] + [label['name'] for label in issue.get('labels', [])]
                )
                features.append(feature)
            
            logger.info(f"Fetched {len(features)} features from roadmap")
        except Exception as e:
            logger.error(f"Error parsing roadmap data: {e}")
        
        return features
    
    def fetch_graphql_changes(self) -> List[Feature]:
        """Fetch features from GraphQL schema changes.
        
        Returns:
            List of Feature objects
        """
        try:
            differ = GraphQLSchemaDiff()
            features = differ.run()
            logger.info(f"Fetched {len(features)} features from GraphQL schema diff")
            return features
        except Exception as e:
            logger.error(f"GraphQL diff failed: {e}")
            return []
    
    def ingest_all(self) -> List[Feature]:
        """Ingest features from all configured sources.
        
        Returns:
            List of all Feature objects
        """
        logger.info("Starting feature ingestion from all sources")
        
        all_features = []
        
        # Fetch from each source
        all_features.extend(self.fetch_changelog())
        all_features.extend(self.fetch_roadmap())
        all_features.extend(self.fetch_graphql_changes())
        
        logger.info(f"Total features ingested: {len(all_features)}")
        self.features = all_features
        
        return all_features
    
    def save_features(self, output_path: str = "data/features.json") -> bool:
        """Save ingested features to file.
        
        Args:
            output_path: Path to output file
            
        Returns:
            True on success, False on failure
        """
        if not self.features:
            logger.warning("No features to save")
            return False
        
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            features_data = [f.to_dict() for f in self.features]
            content = json.dumps(features_data, indent=2)
            
            if safe_write_file(output_path, content, logger):
                logger.info(f"Saved {len(self.features)} features to {output_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to save features: {e}")
            return False


def main():
    """Main entry point for ingestion."""
    import sys
    
    try:
        ingestion = FeatureIngestion()
        features = ingestion.ingest_all()
        
        if not features:
            logger.warning("No features were ingested")
            return 1
        
        # Save features
        if not ingestion.save_features():
            logger.error("Failed to save features")
            return 1
        
        print(f"\nSuccessfully ingested {len(features)} features")
        for feature in features[:5]:  # Show first 5
            print(f"  - {feature.title}")
        if len(features) > 5:
            print(f"  ... and {len(features) - 5} more")
        
        return 0
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
