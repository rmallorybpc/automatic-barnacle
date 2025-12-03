"""Coverage evaluation for feature monitoring."""
import os
import json
from typing import List, Dict
import yaml

from .models import Feature
from .utils import setup_logging, validate_file_exists


logger = setup_logging(__name__)


class CoverageEvaluator:
    """Evaluate feature coverage across product areas."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.coverage_config = self.config.get('coverage', {})
        self.min_threshold = self.coverage_config.get('min_threshold', 0.7)
        self.warning_threshold = self.coverage_config.get('warning_threshold', 0.85)
    
    def load_features(self, features_path: str = "data/embeddings/features_with_embeddings.json") -> List[Feature]:
        """Load features from file.
        
        Args:
            features_path: Path to features JSON file
            
        Returns:
            List of Feature objects
        """
        if not validate_file_exists(features_path, logger):
            logger.warning("Features file not found, trying alternate path")
            features_path = "data/features.json"
            if not validate_file_exists(features_path, logger):
                return []
        
        try:
            with open(features_path, 'r') as f:
                data = json.load(f)
            
            features = [Feature.from_dict(item) for item in data]
            logger.info(f"Loaded {len(features)} features for coverage evaluation")
            return features
        except Exception as e:
            logger.error(f"Failed to load features: {e}")
            return []
    
    def calculate_coverage(self, features: List[Feature]) -> Dict:
        """Calculate coverage metrics.
        
        Args:
            features: List of Feature objects
            
        Returns:
            Dictionary of coverage metrics
        """
        logger.info("Calculating coverage metrics")
        
        # Group by product area
        by_area = {}
        for feature in features:
            area = feature.product_area or "Unknown"
            if area not in by_area:
                by_area[area] = []
            by_area[area].append(feature)
        
        # Group by source type
        by_source = {}
        for feature in features:
            source = feature.source_type
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(feature)
        
        # Calculate metrics
        total_features = len(features)
        coverage_metrics = {
            'total_features': total_features,
            'by_product_area': {
                area: {
                    'count': len(feats),
                    'percentage': len(feats) / total_features if total_features > 0 else 0
                }
                for area, feats in by_area.items()
            },
            'by_source_type': {
                source: {
                    'count': len(feats),
                    'percentage': len(feats) / total_features if total_features > 0 else 0
                }
                for source, feats in by_source.items()
            },
            'embeddings_coverage': {
                'count': sum(1 for f in features if f.embedding),
                'percentage': sum(1 for f in features if f.embedding) / total_features if total_features > 0 else 0
            }
        }
        
        logger.info(f"Coverage calculated: {total_features} features across {len(by_area)} areas")
        return coverage_metrics
    
    def evaluate_thresholds(self, coverage_metrics: Dict) -> Dict:
        """Evaluate coverage against thresholds.
        
        Args:
            coverage_metrics: Coverage metrics dictionary
            
        Returns:
            Evaluation results
        """
        logger.info("Evaluating coverage thresholds")
        
        evaluation = {
            'status': 'pass',
            'issues': []
        }
        
        # Check embeddings coverage
        embeddings_pct = coverage_metrics['embeddings_coverage']['percentage']
        if embeddings_pct < self.min_threshold:
            evaluation['status'] = 'fail'
            evaluation['issues'].append(
                f"Embeddings coverage ({embeddings_pct:.1%}) below minimum threshold ({self.min_threshold:.1%})"
            )
        elif embeddings_pct < self.warning_threshold:
            if evaluation['status'] != 'fail':
                evaluation['status'] = 'warning'
            evaluation['issues'].append(
                f"Embeddings coverage ({embeddings_pct:.1%}) below warning threshold ({self.warning_threshold:.1%})"
            )
        
        return evaluation
    
    def save_coverage_report(
        self,
        coverage_metrics: Dict,
        evaluation: Dict,
        output_path: str = "data/reports/coverage.json"
    ) -> bool:
        """Save coverage report.
        
        Args:
            coverage_metrics: Coverage metrics
            evaluation: Evaluation results
            output_path: Path to output file
            
        Returns:
            True on success, False on failure
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            report = {
                'metrics': coverage_metrics,
                'evaluation': evaluation,
                'timestamp': __import__('datetime').datetime.now().isoformat()
            }
            
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Saved coverage report to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save coverage report: {e}")
            return False


def main():
    """Main entry point for coverage evaluation."""
    import sys
    
    try:
        evaluator = CoverageEvaluator()
        features = evaluator.load_features()
        
        if not features:
            logger.error("No features to evaluate")
            return 1
        
        coverage_metrics = evaluator.calculate_coverage(features)
        evaluation = evaluator.evaluate_thresholds(coverage_metrics)
        
        if not evaluator.save_coverage_report(coverage_metrics, evaluation):
            logger.error("Failed to save coverage report")
            return 1
        
        print(f"\nCoverage Evaluation: {evaluation['status'].upper()}")
        print(f"Total features: {coverage_metrics['total_features']}")
        print(f"Product areas: {len(coverage_metrics['by_product_area'])}")
        print(f"Embeddings coverage: {coverage_metrics['embeddings_coverage']['percentage']:.1%}")
        
        if evaluation['issues']:
            print("\nIssues:")
            for issue in evaluation['issues']:
                print(f"  - {issue}")
        
        return 0 if evaluation['status'] != 'fail' else 1
    except Exception as e:
        logger.error(f"Coverage evaluation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
