"""Report generation for feature monitoring."""
import os
import json
from datetime import datetime
from typing import List, Dict
import yaml

from .models import Feature
from .utils import setup_logging, validate_file_exists


logger = setup_logging(__name__)


class ReportGenerator:
    """Generate reports from monitoring data."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.report_config = self.config.get('report', {})
        self.output_dir = self.report_config.get('output_dir', 'data/reports')
    
    def load_features(self, features_path: str = "data/features.json") -> List[Feature]:
        """Load features from file."""
        if not validate_file_exists(features_path, logger):
            return []
        
        try:
            with open(features_path, 'r') as f:
                data = json.load(f)
            
            features = [Feature.from_dict(item) for item in data]
            logger.info(f"Loaded {len(features)} features for reporting")
            return features
        except Exception as e:
            logger.error(f"Failed to load features: {e}")
            return []
    
    def load_coverage(self, coverage_path: str = "data/reports/coverage.json") -> Dict:
        """Load coverage report."""
        if not validate_file_exists(coverage_path, logger):
            logger.warning("Coverage report not found")
            return {}
        
        try:
            with open(coverage_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load coverage report: {e}")
            return {}
    
    def generate_json_report(self, features: List[Feature], coverage: Dict) -> Dict:
        """Generate JSON format report."""
        logger.info("Generating JSON report")
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_features': len(features),
                'by_source': {},
                'by_product_area': {}
            },
            'coverage': coverage.get('metrics', {}),
            'features': [f.to_dict() for f in features]
        }
        
        # Calculate summaries
        for feature in features:
            source = feature.source_type
            area = feature.product_area or "Unknown"
            
            report['summary']['by_source'][source] = report['summary']['by_source'].get(source, 0) + 1
            report['summary']['by_product_area'][area] = report['summary']['by_product_area'].get(area, 0) + 1
        
        return report
    
    def generate_markdown_report(self, features: List[Feature], coverage: Dict) -> str:
        """Generate Markdown format report."""
        logger.info("Generating Markdown report")
        
        md = "# Feature Monitoring Report\n\n"
        md += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Summary
        md += "## Summary\n\n"
        md += f"- **Total Features:** {len(features)}\n"
        
        # By source
        by_source = {}
        for feature in features:
            source = feature.source_type
            by_source[source] = by_source.get(source, 0) + 1
        
        md += "\n### By Source\n\n"
        for source, count in sorted(by_source.items()):
            md += f"- **{source}:** {count}\n"
        
        # By product area
        by_area = {}
        for feature in features:
            area = feature.product_area or "Unknown"
            by_area[area] = by_area.get(area, 0) + 1
        
        md += "\n### By Product Area\n\n"
        for area, count in sorted(by_area.items()):
            md += f"- **{area}:** {count}\n"
        
        # Coverage
        if coverage:
            md += "\n## Coverage\n\n"
            metrics = coverage.get('metrics', {})
            if 'embeddings_coverage' in metrics:
                pct = metrics['embeddings_coverage']['percentage'] * 100
                md += f"- **Embeddings Coverage:** {pct:.1f}%\n"
        
        # Feature list
        md += "\n## Features\n\n"
        for feature in features[:20]:  # Limit to first 20
            md += f"### {feature.title}\n\n"
            md += f"- **Source:** {feature.source_type}\n"
            md += f"- **Product Area:** {feature.product_area}\n"
            if feature.source_url:
                md += f"- **URL:** {feature.source_url}\n"
            md += f"\n{feature.description}\n\n"
        
        if len(features) > 20:
            md += f"\n*... and {len(features) - 20} more features*\n"
        
        return md
    
    def save_reports(self, features: List[Feature], coverage: Dict) -> bool:
        """Generate and save all report formats.
        
        Args:
            features: List of features
            coverage: Coverage data
            
        Returns:
            True on success, False on failure
        """
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            
            formats = self.report_config.get('formats', ['json', 'markdown'])
            
            if 'json' in formats:
                json_report = self.generate_json_report(features, coverage)
                json_path = os.path.join(self.output_dir, 'report.json')
                with open(json_path, 'w') as f:
                    json.dump(json_report, f, indent=2)
                logger.info(f"Saved JSON report to {json_path}")
            
            if 'markdown' in formats:
                md_report = self.generate_markdown_report(features, coverage)
                md_path = os.path.join(self.output_dir, 'report.md')
                with open(md_path, 'w') as f:
                    f.write(md_report)
                logger.info(f"Saved Markdown report to {md_path}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to save reports: {e}")
            return False


def main():
    """Main entry point for report generation."""
    import sys
    
    try:
        generator = ReportGenerator()
        features = generator.load_features()
        
        if not features:
            logger.error("No features to report on")
            return 1
        
        coverage = generator.load_coverage()
        
        if not generator.save_reports(features, coverage):
            logger.error("Failed to save reports")
            return 1
        
        print(f"\nGenerated reports for {len(features)} features")
        print(f"Output directory: {generator.output_dir}")
        
        return 0
    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
