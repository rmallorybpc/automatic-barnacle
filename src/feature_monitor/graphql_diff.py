"""GraphQL schema diff module for detecting API changes."""
import os
import re
from datetime import datetime
from typing import List, Optional, Set, Tuple
import yaml

from .models import Feature
from .utils import setup_logging, safe_request, safe_write_file


logger = setup_logging(__name__)


class GraphQLSchemaDiff:
    """Handles fetching and diffing GitHub GraphQL schemas."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.graphql_config = self.config.get('sources', {}).get('graphql_schema', {})
        self.data_dir = "data/graphql"
        os.makedirs(self.data_dir, exist_ok=True)
    
    def fetch_current_schema(self) -> Optional[str]:
        """Fetch the current GitHub GraphQL schema.
        
        Returns:
            Schema SDL as string or None on failure
        """
        if not self.graphql_config.get('enabled', False):
            logger.info("GraphQL schema source is disabled")
            return None
        
        schema_url = self.graphql_config.get('docs_url')
        if not schema_url:
            logger.error("No GraphQL schema URL configured")
            return None
        
        logger.info(f"Fetching GraphQL schema from {schema_url}")
        response = safe_request(schema_url, logger=logger)
        
        if response and response.status_code == 200:
            return response.text
        
        logger.error("Failed to fetch GraphQL schema")
        return None
    
    def save_schema_snapshot(self, schema: str) -> str:
        """Save schema snapshot with timestamp.
        
        Args:
            schema: Schema SDL content
            
        Returns:
            Path to saved file
        """
        today = datetime.now().strftime("%Y-%m-%d")
        filepath = os.path.join(self.data_dir, f"schema-{today}.graphql")
        
        if safe_write_file(filepath, schema, logger):
            logger.info(f"Saved schema snapshot: {filepath}")
            return filepath
        else:
            raise RuntimeError(f"Failed to save schema snapshot: {filepath}")
    
    def get_latest_snapshot(self) -> Optional[Tuple[str, str]]:
        """Get the most recent schema snapshot.
        
        Returns:
            Tuple of (filepath, content) or None if no snapshots exist
        """
        if not os.path.exists(self.data_dir):
            return None
        
        snapshots = sorted([
            f for f in os.listdir(self.data_dir)
            if f.startswith('schema-') and f.endswith('.graphql')
        ], reverse=True)
        
        if len(snapshots) < 2:
            logger.info("Not enough snapshots for diff (need at least 2)")
            return None
        
        # Get second-most recent (most recent is today's)
        prev_snapshot = snapshots[1]
        filepath = os.path.join(self.data_dir, prev_snapshot)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return filepath, content
        except Exception as e:
            logger.error(f"Failed to read snapshot {filepath}: {e}")
            return None
    
    def parse_schema_types(self, schema: str) -> Set[str]:
        """Extract type names from schema SDL.
        
        Args:
            schema: GraphQL schema SDL
            
        Returns:
            Set of type names
        """
        types = set()
        # Match type definitions: type Name, interface Name, input Name, enum Name
        type_pattern = r'^\s*(type|interface|input|enum)\s+([A-Z]\w+)'
        
        for line in schema.split('\n'):
            match = re.match(type_pattern, line)
            if match:
                types.add(match.group(2))
        
        return types
    
    def parse_schema_fields(self, schema: str, type_name: str) -> Set[str]:
        """Extract field names for a given type.
        
        Args:
            schema: GraphQL schema SDL
            type_name: Name of the type
            
        Returns:
            Set of field names
        """
        fields = set()
        in_type = False
        
        for line in schema.split('\n'):
            # Check if entering the type definition
            if re.match(rf'^\s*type\s+{type_name}\s*{{', line):
                in_type = True
                continue
            
            # Check if exiting the type definition
            if in_type and '}' in line:
                break
            
            # Extract field name
            if in_type:
                field_match = re.match(r'^\s+(\w+)\s*[:(]', line)
                if field_match:
                    fields.add(field_match.group(1))
        
        return fields
    
    def detect_changes(self, old_schema: str, new_schema: str) -> List[Feature]:
        """Detect changes between two schemas.
        
        Args:
            old_schema: Previous schema SDL
            new_schema: Current schema SDL
            
        Returns:
            List of Feature objects representing changes
        """
        features = []
        
        old_types = self.parse_schema_types(old_schema)
        new_types = self.parse_schema_types(new_schema)
        
        # Detect new types
        added_types = new_types - old_types
        logger.info(f"Found {len(added_types)} new types")
        
        for type_name in added_types:
            # Check if it's a mutation or query type (more significant)
            is_significant = any(keyword in type_name.lower() 
                               for keyword in ['mutation', 'query', 'input', 'payload'])
            
            if is_significant or len(added_types) <= 10:  # Limit noise
                feature = Feature(
                    id=f"graphql_{type_name}_{datetime.now().strftime('%Y%m%d')}",
                    title=f"New GraphQL Type: {type_name}",
                    description=f"A new GraphQL type '{type_name}' has been added to the GitHub API schema.",
                    source_type="graphql_schema_diff",
                    source_url="https://docs.github.com/graphql",
                    product_area="API",
                    tags=["graphql", "api", "schema-change", type_name.lower()]
                )
                features.append(feature)
        
        # Detect new fields in existing types (sample a few important types)
        important_types = ['Mutation', 'Query', 'Repository', 'PullRequest', 'Issue']
        for type_name in important_types:
            if type_name in old_types and type_name in new_types:
                old_fields = self.parse_schema_fields(old_schema, type_name)
                new_fields = self.parse_schema_fields(new_schema, type_name)
                added_fields = new_fields - old_fields
                
                if added_fields:
                    logger.info(f"Found {len(added_fields)} new fields in {type_name}")
                    
                    for field_name in list(added_fields)[:5]:  # Limit to 5 per type
                        feature = Feature(
                            id=f"graphql_{type_name}_{field_name}_{datetime.now().strftime('%Y%m%d')}",
                            title=f"New GraphQL Field: {type_name}.{field_name}",
                            description=f"A new field '{field_name}' has been added to the '{type_name}' type in the GitHub GraphQL API.",
                            source_type="graphql_schema_diff",
                            source_url="https://docs.github.com/graphql",
                            product_area="API",
                            tags=["graphql", "api", "field-addition", type_name.lower()]
                        )
                        features.append(feature)
        
        return features
    
    def run(self) -> List[Feature]:
        """Run the GraphQL schema diff process.
        
        Returns:
            List of Feature objects for detected changes
        """
        logger.info("Starting GraphQL schema diff process")
        
        # Fetch current schema
        current_schema = self.fetch_current_schema()
        if not current_schema:
            logger.error("Could not fetch current schema, aborting")
            return []
        
        # Save current snapshot
        try:
            self.save_schema_snapshot(current_schema)
        except Exception as e:
            logger.error(f"Failed to save schema snapshot: {e}")
            return []
        
        # Get previous snapshot
        prev_snapshot = self.get_latest_snapshot()
        if not prev_snapshot:
            logger.info("No previous snapshot available, no diff to perform")
            return []
        
        prev_filepath, prev_schema = prev_snapshot
        logger.info(f"Comparing with previous snapshot: {prev_filepath}")
        
        # Detect changes
        features = self.detect_changes(prev_schema, current_schema)
        logger.info(f"Detected {len(features)} feature changes")
        
        return features


def main():
    """Main entry point for GraphQL schema diff."""
    import sys
    
    try:
        differ = GraphQLSchemaDiff()
        features = differ.run()
        
        print(f"\nDetected {len(features)} GraphQL schema changes:")
        for feature in features:
            print(f"  - {feature.title}")
        
        # Save features to file
        if features:
            import json
            output_file = "data/graphql/detected_changes.json"
            with open(output_file, 'w') as f:
                json.dump([f.to_dict() for f in features], f, indent=2)
            print(f"\nSaved changes to {output_file}")
        
        return 0
    except Exception as e:
        logger.error(f"GraphQL schema diff failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
