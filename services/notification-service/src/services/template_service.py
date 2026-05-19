"""
Template Service

Handles email template rendering using Jinja2.
"""
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import os
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for rendering email templates"""

    def __init__(self):
        """Initialize Jinja2 environment"""
        # Get the templates directory path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        service_root = os.path.dirname(os.path.dirname(current_dir))
        templates_dir = os.path.join(service_root, 'src', 'templates')

        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=True
        )
        logger.info(f"✅ Template service initialized. Templates dir: {templates_dir}")

    def render_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Render an email template to HTML and plain text.

        Args:
            template_name: Name of the template (e.g., 'invite_user')
            context: Dictionary of variables for the template

        Returns:
            Tuple of (html_content, text_content)

        Raises:
            TemplateNotFound: If template doesn't exist
        """
        try:
            # Load HTML template
            html_template = self.env.get_template(f"{template_name}.html")
            html_content = html_template.render(**context)

            # Try to load text version, fall back to simple HTML stripping
            try:
                text_template = self.env.get_template(f"{template_name}.txt")
                text_content = text_template.render(**context)
            except TemplateNotFound:
                # Simple HTML stripping for plain text
                import re
                text_content = re.sub('<[^<]+?>', '', html_content)
                text_content = re.sub(r'\s+', ' ', text_content).strip()

            logger.info(f"✅ Template '{template_name}' rendered successfully")
            return (html_content, text_content)

        except TemplateNotFound as e:
            logger.error(f"❌ Template not found: {template_name}")
            raise e
        except Exception as e:
            logger.error(f"❌ Error rendering template '{template_name}': {str(e)}")
            raise e


# Singleton instance
template_service = TemplateService()
