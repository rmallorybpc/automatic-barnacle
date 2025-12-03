"""Notifications module for Slack and Teams."""
import os
import json
from typing import Dict, Optional
import yaml

from .utils import setup_logging, safe_request


logger = setup_logging(__name__)


class NotificationManager:
    """Manage notifications to Slack and Teams."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.notifications_config = self.config.get('notifications', {})
    
    def format_slack_message(self, summary: Dict) -> Dict:
        """Format message for Slack.
        
        Args:
            summary: Summary data to send
            
        Returns:
            Slack message payload
        """
        text = "*Feature Monitoring Report*\n\n"
        
        if 'total_features' in summary:
            text += f"📊 Total Features: {summary['total_features']}\n"
        
        if 'by_source' in summary:
            text += "\n*By Source:*\n"
            for source, count in summary['by_source'].items():
                text += f"  • {source}: {count}\n"
        
        if 'by_product_area' in summary:
            text += "\n*By Product Area:*\n"
            for area, count in list(summary['by_product_area'].items())[:5]:
                text += f"  • {area}: {count}\n"
        
        if 'issues_created' in summary:
            text += f"\n🔧 Issues Created: {summary['issues_created']}\n"
        
        return {
            "text": text,
            "unfurl_links": False
        }
    
    def format_teams_message(self, summary: Dict) -> Dict:
        """Format message for Teams.
        
        Args:
            summary: Summary data to send
            
        Returns:
            Teams message payload
        """
        facts = []
        
        if 'total_features' in summary:
            facts.append({
                "name": "Total Features",
                "value": str(summary['total_features'])
            })
        
        if 'issues_created' in summary:
            facts.append({
                "name": "Issues Created",
                "value": str(summary['issues_created'])
            })
        
        sections = []
        
        if 'by_source' in summary:
            source_text = "\n".join(
                f"- {source}: {count}"
                for source, count in summary['by_source'].items()
            )
            sections.append({
                "activityTitle": "By Source",
                "text": source_text
            })
        
        return {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": "Feature Monitoring Report",
            "themeColor": "0078D7",
            "title": "Feature Monitoring Report",
            "sections": sections,
            "potentialAction": []
        }
    
    def send_slack_notification(self, summary: Dict) -> bool:
        """Send notification to Slack.
        
        Args:
            summary: Summary data to send
            
        Returns:
            True on success, False on failure
        """
        slack_config = self.notifications_config.get('slack', {})
        
        if not slack_config.get('enabled', False):
            logger.info("Slack notifications are disabled")
            return True
        
        webhook_env = slack_config.get('webhook_url_env', 'SLACK_WEBHOOK_URL')
        webhook_url = os.environ.get(webhook_env)
        
        if not webhook_url:
            logger.warning(f"Slack webhook URL not found in environment variable: {webhook_env}")
            return False
        
        message = self.format_slack_message(summary)
        
        logger.info("Sending Slack notification")
        response = safe_request(
            webhook_url,
            method="POST",
            logger=logger,
            json=message,
            headers={'Content-Type': 'application/json'}
        )
        
        if response and response.status_code == 200:
            logger.info("Slack notification sent successfully")
            return True
        else:
            logger.error("Failed to send Slack notification")
            return False
    
    def send_teams_notification(self, summary: Dict) -> bool:
        """Send notification to Teams.
        
        Args:
            summary: Summary data to send
            
        Returns:
            True on success, False on failure
        """
        teams_config = self.notifications_config.get('teams', {})
        
        if not teams_config.get('enabled', False):
            logger.info("Teams notifications are disabled")
            return True
        
        webhook_env = teams_config.get('webhook_url_env', 'TEAMS_WEBHOOK_URL')
        webhook_url = os.environ.get(webhook_env)
        
        if not webhook_url:
            logger.warning(f"Teams webhook URL not found in environment variable: {webhook_env}")
            return False
        
        message = self.format_teams_message(summary)
        
        logger.info("Sending Teams notification")
        response = safe_request(
            webhook_url,
            method="POST",
            logger=logger,
            json=message,
            headers={'Content-Type': 'application/json'}
        )
        
        if response and response.status_code == 200:
            logger.info("Teams notification sent successfully")
            return True
        else:
            logger.error("Failed to send Teams notification")
            return False
    
    def send_all(self, summary: Dict) -> Dict[str, bool]:
        """Send notifications to all enabled channels.
        
        Args:
            summary: Summary data to send
            
        Returns:
            Dictionary of results per channel
        """
        logger.info("Sending notifications to all enabled channels")
        
        results = {
            'slack': self.send_slack_notification(summary),
            'teams': self.send_teams_notification(summary)
        }
        
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Notifications sent: {success_count}/{len(results)} successful")
        
        return results


def main():
    """Main entry point for notifications."""
    import sys
    
    try:
        manager = NotificationManager()
        
        # Load summary data
        report_path = "data/reports/report.json"
        if not os.path.exists(report_path):
            logger.error("Report not found")
            return 1
        
        with open(report_path, 'r') as f:
            report = json.load(f)
        
        summary = report.get('summary', {})
        
        # Add issues summary if available
        issues_path = "data/issues/summary.json"
        if os.path.exists(issues_path):
            with open(issues_path, 'r') as f:
                issues = json.load(f)
                summary['issues_created'] = issues.get('created', 0)
        
        results = manager.send_all(summary)
        
        print("\nNotification Results:")
        for channel, success in results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {channel.capitalize()}")
        
        return 0 if all(results.values()) else 1
    except Exception as e:
        logger.error(f"Notifications failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
