"""Monthly report generation module."""
import os
import json
from datetime import datetime
from typing import List, Dict
from calendar import monthrange
import yaml

from .models import Feature
from .utils import setup_logging, validate_file_exists


logger = setup_logging(__name__)


class MonthlyReportGenerator:
    """Generate monthly summary reports."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.monthly_config = self.config.get('monthly_report', {})
        self.output_dir = self.monthly_config.get('output_dir', 'data/reports/monthly')
    
    def load_features(self, features_path: str = "data/features.json") -> List[Feature]:
        """Load features from file."""
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
    
    def filter_features_by_month(
        self,
        features: List[Feature],
        year: int,
        month: int
    ) -> List[Feature]:
        """Filter features discovered in a specific month.
        
        Args:
            features: List of Feature objects
            year: Year
            month: Month (1-12)
            
        Returns:
            Filtered list of features
        """
        logger.info(f"Filtering features for {year}-{month:02d}")
        
        filtered = []
        target_prefix = f"{year}-{month:02d}"
        
        for feature in features:
            try:
                if feature.date_discovered.startswith(target_prefix):
                    filtered.append(feature)
            except Exception as e:
                logger.warning(f"Could not parse date for feature {feature.id}: {e}")
        
        logger.info(f"Found {len(filtered)} features for the month")
        return filtered
    
    def generate_monthly_summary(
        self,
        features: List[Feature],
        year: int,
        month: int
    ) -> Dict:
        """Generate monthly summary.
        
        Args:
            features: List of Feature objects for the month
            year: Year
            month: Month
            
        Returns:
            Summary dictionary
        """
        logger.info("Generating monthly summary")
        
        # Group by source
        by_source = {}
        for feature in features:
            source = feature.source_type
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(feature)
        
        # Group by product area
        by_area = {}
        for feature in features:
            area = feature.product_area or "Unknown"
            if area not in by_area:
                by_area[area] = []
            by_area[area].append(feature)
        
        summary = {
            'year': year,
            'month': month,
            'month_name': datetime(year, month, 1).strftime('%B'),
            'total_features': len(features),
            'by_source': {
                source: len(feats)
                for source, feats in by_source.items()
            },
            'by_product_area': {
                area: len(feats)
                for area, feats in by_area.items()
            },
            'top_features': [
                {
                    'id': f.id,
                    'title': f.title,
                    'source': f.source_type,
                    'product_area': f.product_area
                }
                for f in features[:10]  # Top 10
            ]
        }
        
        return summary
    
    def generate_markdown_report(self, summary: Dict, features: List[Feature]) -> str:
        """Generate Markdown format monthly report.
        
        Args:
            summary: Summary dictionary
            features: List of features for the month
            
        Returns:
            Markdown formatted report
        """
        logger.info("Generating Markdown monthly report")
        
        md = f"# Monthly Feature Report - {summary['month_name']} {summary['year']}\n\n"
        md += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Summary
        md += "## Summary\n\n"
        md += f"- **Total Features:** {summary['total_features']}\n\n"
        
        # By source
        if summary['by_source']:
            md += "### By Source\n\n"
            for source, count in sorted(summary['by_source'].items()):
                md += f"- **{source}:** {count}\n"
            md += "\n"
        
        # By product area
        if summary['by_product_area']:
            md += "### By Product Area\n\n"
            sorted_areas = sorted(
                summary['by_product_area'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            for area, count in sorted_areas[:10]:  # Top 10
                md += f"- **{area}:** {count}\n"
            md += "\n"
        
        # Top features
        if summary['top_features']:
            md += "## Notable Features\n\n"
            for feat in summary['top_features']:
                md += f"### {feat['title']}\n\n"
                md += f"- **Source:** {feat['source']}\n"
                md += f"- **Product Area:** {feat['product_area']}\n\n"
        
        return md
    
    def save_monthly_report(
        self,
        summary: Dict,
        features: List[Feature],
        year: int,
        month: int
    ) -> bool:
        """Save monthly report.
        
        Args:
            summary: Summary dictionary
            features: List of features
            year: Year
            month: Month
            
        Returns:
            True on success, False on failure
        """
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Save JSON
            json_filename = f"{year}-{month:02d}_report.json"
            json_path = os.path.join(self.output_dir, json_filename)
            
            report_data = {
                'summary': summary,
                'features': [f.to_dict() for f in features]
            }
            
            with open(json_path, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            logger.info(f"Saved JSON report to {json_path}")
            
            # Save Markdown
            md_filename = f"{year}-{month:02d}_report.md"
            md_path = os.path.join(self.output_dir, md_filename)
            
            md_content = self.generate_markdown_report(summary, features)
            
            with open(md_path, 'w') as f:
                f.write(md_content)
            
            logger.info(f"Saved Markdown report to {md_path}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to save monthly report: {e}")
            return False
    
    def generate_report(self, year: int = None, month: int = None) -> bool:
        """Generate monthly report for specified or current month.
        
        Args:
            year: Year (default: current year)
            month: Month (default: current month)
            
        Returns:
            True on success, False on failure
        """
        if year is None or month is None:
            now = datetime.now()
            year = year or now.year
            month = month or now.month
        
        logger.info(f"Generating monthly report for {year}-{month:02d}")
        
        # Load all features
        all_features = self.load_features()
        if not all_features:
            logger.warning("No features found")
            return False
        
        # Filter for the month
        month_features = self.filter_features_by_month(all_features, year, month)
        
        # Generate summary
        summary = self.generate_monthly_summary(month_features, year, month)
        
        # Save report
        return self.save_monthly_report(summary, month_features, year, month)


def main():
    """Main entry point for monthly report generation."""
    import sys
    
    try:
        generator = MonthlyReportGenerator()
        
        # Generate for current month
        now = datetime.now()
        
        if not generator.generate_report(now.year, now.month):
            logger.error("Failed to generate monthly report")
            return 1
        
        print(f"\nMonthly report generated successfully")
        print(f"Month: {now.strftime('%B %Y')}")
        print(f"Output directory: {generator.output_dir}")
        
        return 0
    except Exception as e:
        logger.error(f"Monthly report generation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
