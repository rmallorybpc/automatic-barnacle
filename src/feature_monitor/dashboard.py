"""Dashboard generation module."""
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict
import yaml

from .models import Feature
from .utils import setup_logging, validate_file_exists


logger = setup_logging(__name__)


class DashboardGenerator:
    """Generate dashboard artifacts for visualization."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.dashboard_config = self.config.get('dashboard', {})
        self.output_dir = self.dashboard_config.get('output_dir', 'data/dashboard')
        self.retention_days = self.dashboard_config.get('retention_days', 90)
    
    def load_features(self, features_path: str = "data/features.json") -> List[Feature]:
        """Load features from file."""
        if not validate_file_exists(features_path, logger):
            return []

        try:
            with open(features_path, 'r') as f:
                data = json.load(f)

            features = [Feature.from_dict(item) for item in data]
            logger.info(f"Loaded {len(features)} features for dashboard")
            return features
        except Exception as e:
            logger.error(f"Failed to load features: {e}")
            return []

    def load_content_checks(self) -> List[Dict]:
        """Load latest content check results (if configured and present on disk)."""
        checks_cfg = self.config.get("content_checks")
        if not isinstance(checks_cfg, list) or not checks_cfg:
            return []

        results: List[Dict] = []
        for item in checks_cfg:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or item.get("name") or "").strip()
            name = str(item.get("name") or key).strip()
            url = str(item.get("url") or "").strip()
            if not key:
                continue

            path = os.path.join("data", "content_checks", f"{key}.json")
            record: Dict = {}
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        record = json.load(f) or {}
                except Exception as e:
                    logger.warning(f"Failed to read content check {path}: {e}")

            status_code = record.get("status_code")
            ok = record.get("ok")
            if ok is None:
                try:
                    ok = (status_code is not None) and (200 <= int(status_code) < 400)
                except Exception:
                    ok = False

            results.append({
                "key": record.get("key") or key,
                "name": record.get("name") or name,
                "url": record.get("url") or url,
                "checked_at": record.get("checked_at"),
                "status_code": status_code,
                "ok": bool(ok),
                "changed": record.get("changed"),
            })

        return results
    
    def generate_time_series_data(self, features: List[Feature]) -> Dict:
        """Generate time series data for dashboard.
        
        Args:
            features: List of Feature objects
            
        Returns:
            Time series data structure
        """
        logger.info("Generating time series data")
        
        # Group by date
        by_date = {}
        for feature in features:
            try:
                date_str = feature.date_discovered.split('T')[0]
                if date_str not in by_date:
                    by_date[date_str] = []
                by_date[date_str].append(feature)
            except Exception as e:
                logger.warning(f"Could not parse date for feature {feature.id}: {e}")
        
        # Create cumulative counts
        sorted_dates = sorted(by_date.keys())
        cumulative = 0
        time_series = []
        
        for date in sorted_dates:
            cumulative += len(by_date[date])
            time_series.append({
                'date': date,
                'count': len(by_date[date]),
                'cumulative': cumulative
            })
        
        return {
            'time_series': time_series,
            'total': cumulative
        }
    
    def generate_source_breakdown(self, features: List[Feature]) -> Dict:
        """Generate source type breakdown.
        
        Args:
            features: List of Feature objects
            
        Returns:
            Source breakdown data
        """
        logger.info("Generating source breakdown")
        
        breakdown = {}
        for feature in features:
            source = feature.source_type
            if source not in breakdown:
                breakdown[source] = 0
            breakdown[source] += 1
        
        return {
            'sources': [
                {'name': source, 'count': count}
                for source, count in sorted(breakdown.items())
            ]
        }
    
    def generate_product_area_breakdown(self, features: List[Feature]) -> Dict:
        """Generate product area breakdown.
        
        Args:
            features: List of Feature objects
            
        Returns:
            Product area breakdown data
        """
        logger.info("Generating product area breakdown")
        
        breakdown = {}
        for feature in features:
            area = feature.product_area or "Unknown"
            if area not in breakdown:
                breakdown[area] = 0
            breakdown[area] += 1
        
        # Sort by count descending
        sorted_areas = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'product_areas': [
                {'name': area, 'count': count}
                for area, count in sorted_areas
            ]
        }
    
    def generate_dashboard_data(self, features: List[Feature]) -> Dict:
        """Generate complete dashboard data structure.
        
        Args:
            features: List of Feature objects
            
        Returns:
            Dashboard data dictionary
        """
        logger.info("Generating dashboard data")

        def _feature_summary(f: Feature) -> Dict:
            # Keep the published dashboard payload small and stable.
            return {
                'id': f.id,
                'title': f.title,
                'source_type': f.source_type,
                'product_area': f.product_area,
                'source_url': f.source_url,
                'date_discovered': f.date_discovered,
            }
        
        dashboard_data = {
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_features': len(features),
            },
            'time_series': self.generate_time_series_data(features),
            'source_breakdown': self.generate_source_breakdown(features),
            'product_area_breakdown': self.generate_product_area_breakdown(features),
            'features': [_feature_summary(f) for f in features],
            'content_checks': self.load_content_checks(),
        }
        
        return dashboard_data
    
    def save_dashboard_data(self, dashboard_data: Dict) -> bool:
        """Save dashboard data to file.
        
        Args:
            dashboard_data: Dashboard data dictionary
            
        Returns:
            True on success, False on failure
        """
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Save timestamped version
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            timestamped_path = os.path.join(self.output_dir, f'dashboard_{timestamp}.json')
            
            with open(timestamped_path, 'w') as f:
                json.dump(dashboard_data, f, indent=2)
            
            logger.info(f"Saved dashboard data to {timestamped_path}")
            
            # Save as latest
            latest_path = os.path.join(self.output_dir, 'dashboard_latest.json')
            with open(latest_path, 'w') as f:
                json.dump(dashboard_data, f, indent=2)
            
            logger.info(f"Saved latest dashboard data to {latest_path}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to save dashboard data: {e}")
            return False
    
    def cleanup_old_dashboards(self) -> None:
        """Remove dashboard files older than retention period."""
        logger.info(f"Cleaning up dashboards older than {self.retention_days} days")
        
        if not os.path.exists(self.output_dir):
            return
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        for filename in os.listdir(self.output_dir):
            if not filename.startswith('dashboard_') or filename == 'dashboard_latest.json':
                continue
            
            filepath = os.path.join(self.output_dir, filename)
            
            try:
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                if file_time < cutoff_date:
                    os.remove(filepath)
                    logger.info(f"Removed old dashboard: {filename}")
            except Exception as e:
                logger.warning(f"Could not process {filename}: {e}")


def main():
    """Main entry point for dashboard generation."""
    import sys
    
    try:
        generator = DashboardGenerator()
        features = generator.load_features()

        if not features:
            # In CI or on quiet days, ingestion may legitimately produce no features.
            # Still emit a valid dashboard payload so downstream publish steps can run.
            logger.warning("No features to generate dashboard from; generating empty dashboard")
            features = []
        
        dashboard_data = generator.generate_dashboard_data(features)
        
        if not generator.save_dashboard_data(dashboard_data):
            logger.error("Failed to save dashboard data")
            return 1
        
        generator.cleanup_old_dashboards()
        
        print(f"\nDashboard generated successfully")
        print(f"Total features: {dashboard_data['summary']['total_features']}")
        print(f"Output directory: {generator.output_dir}")
        
        return 0
    except Exception as e:
        logger.error(f"Dashboard generation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
