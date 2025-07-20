"""
Notification service for sending price alerts and other notifications.
"""
import asyncio
import logging
import json
from typing import Dict, Any, Optional
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.models.models import PriceMonitor, PriceAlert

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications via email and webhooks."""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def send_price_alert_email(self, monitor: PriceMonitor, alert: PriceAlert):
        """Send price alert via email."""
        
        try:
            # Get user email from monitor relationship
            user = monitor.user
            if not user or not user.email:
                logger.warning(f"No email found for monitor {monitor.id}")
                return
            
            # Create email content
            subject = f"Price Alert: {monitor.name}"
            
            # HTML email template
            html_content = self._create_price_alert_html(monitor, alert)
            
            # Text version
            text_content = self._create_price_alert_text(monitor, alert)
            
            # Send email (implementation depends on email service)
            await self._send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            logger.info(f"Sent price alert email to {user.email} for monitor {monitor.id}")
            
        except Exception as e:
            logger.error(f"Failed to send price alert email for monitor {monitor.id}: {str(e)}")
            raise
    
    async def send_price_alert_webhook(self, monitor: PriceMonitor, alert: PriceAlert):
        """Send price alert via webhook."""
        
        try:
            if not monitor.webhook_url:
                return
            
            # Create webhook payload
            payload = {
                "event": "price_alert",
                "monitor": {
                    "id": monitor.id,
                    "name": monitor.name,
                    "asin": monitor.asin,
                    "marketplace": monitor.marketplace,
                    "target_price": monitor.target_price,
                    "threshold_percentage": monitor.threshold_percentage
                },
                "alert": {
                    "id": alert.id,
                    "type": alert.alert_type,
                    "message": alert.message,
                    "current_price": alert.current_price,
                    "previous_price": alert.previous_price,
                    "price_change": alert.price_change,
                    "price_change_percentage": alert.price_change_percentage,
                    "timestamp": alert.created_at.isoformat()
                }
            }
            
            # Send webhook
            response = await self.http_client.post(
                monitor.webhook_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Amazon-Product-Intelligence-Platform/1.0"
                }
            )
            
            if response.status_code >= 400:
                raise Exception(f"Webhook failed with status {response.status_code}: {response.text}")
            
            logger.info(f"Sent price alert webhook to {monitor.webhook_url} for monitor {monitor.id}")
            
        except Exception as e:
            logger.error(f"Failed to send price alert webhook for monitor {monitor.id}: {str(e)}")
            raise
    
    def _create_price_alert_html(self, monitor: PriceMonitor, alert: PriceAlert) -> str:
        """Create HTML email content for price alert."""
        
        # Determine color based on alert type
        color = {
            "price_drop": "#28a745",
            "target_reached": "#007bff", 
            "threshold_reached": "#ffc107",
            "back_in_stock": "#17a2b8",
            "out_of_stock": "#dc3545"
        }.get(alert.alert_type, "#6c757d")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Price Alert: {monitor.name}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #f8f9fa; padding: 20px; border-radius: 8px;">
                <div style="background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: {color}; margin: 0; font-size: 24px;">🚨 Price Alert</h1>
                    </div>
                    
                    <div style="background: {color}; color: white; padding: 15px; border-radius: 6px; margin-bottom: 20px;">
                        <h2 style="margin: 0; font-size: 18px;">{alert.message}</h2>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <h3 style="color: #333; margin-bottom: 10px; font-size: 16px;">Product Details</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold;">Product:</td>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{monitor.name}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold;">ASIN:</td>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{monitor.asin}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold;">Current Price:</td>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-size: 18px; font-weight: bold; color: {color};">${alert.current_price:.2f}</td>
                            </tr>
        """
        
        if alert.previous_price:
            html += f"""
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold;">Previous Price:</td>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">${alert.previous_price:.2f}</td>
                            </tr>
            """
        
        if alert.price_change:
            change_color = "#28a745" if alert.price_change < 0 else "#dc3545"
            html += f"""
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold;">Price Change:</td>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee; color: {change_color};">
                                    ${alert.price_change:+.2f} ({alert.price_change_percentage:+.1f}%)
                                </td>
                            </tr>
            """
        
        if monitor.target_price:
            html += f"""
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee; font-weight: bold;">Target Price:</td>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">${monitor.target_price:.2f}</td>
                            </tr>
            """
        
        html += f"""
                        </table>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="https://amazon.com/dp/{monitor.asin}" 
                           style="display: inline-block; background: {color}; color: white; padding: 12px 24px; 
                                  text-decoration: none; border-radius: 6px; font-weight: bold;">
                            View on Amazon
                        </a>
                    </div>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; 
                                text-align: center; color: #666; font-size: 12px;">
                        <p>This alert was sent by Amazon Product Intelligence Platform</p>
                        <p>Alert ID: {alert.id}</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_price_alert_text(self, monitor: PriceMonitor, alert: PriceAlert) -> str:
        """Create text email content for price alert."""
        
        text = f"""
PRICE ALERT: {monitor.name}

{alert.message}

Product Details:
- Product: {monitor.name}
- ASIN: {monitor.asin}
- Current Price: ${alert.current_price:.2f}
"""
        
        if alert.previous_price:
            text += f"- Previous Price: ${alert.previous_price:.2f}\n"
        
        if alert.price_change:
            text += f"- Price Change: ${alert.price_change:+.2f} ({alert.price_change_percentage:+.1f}%)\n"
        
        if monitor.target_price:
            text += f"- Target Price: ${monitor.target_price:.2f}\n"
        
        text += f"""
View on Amazon: https://amazon.com/dp/{monitor.asin}

---
This alert was sent by Amazon Product Intelligence Platform
Alert ID: {alert.id}
        """
        
        return text.strip()
    
    async def _send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str, 
        text_content: str
    ):
        """Send email using configured email service."""
        
        # For now, just log the email (in production, integrate with SendGrid, SES, etc.)
        logger.info(f"EMAIL TO: {to_email}")
        logger.info(f"SUBJECT: {subject}")
        logger.info(f"CONTENT: {text_content[:200]}...")
        
        # TODO: Implement actual email sending
        # Example integrations:
        # - AWS SES
        # - SendGrid
        # - Mailgun
        # - SMTP
        
        await asyncio.sleep(0.1)  # Simulate email sending delay
    
    async def send_welcome_email(self, user_email: str, user_name: str):
        """Send welcome email to new users."""
        
        try:
            subject = "Welcome to Amazon Product Intelligence Platform"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #007bff;">Welcome to Amazon Product Intelligence Platform!</h1>
                    
                    <p>Hi {user_name},</p>
                    
                    <p>Thanks for joining our platform! You now have access to:</p>
                    
                    <ul>
                        <li>🔍 Real-time Amazon product data</li>
                        <li>📊 FNSKU to ASIN conversion</li>
                        <li>📈 Price monitoring and alerts</li>
                        <li>💳 Credit-based billing system</li>
                    </ul>
                    
                    <p>You've been credited with <strong>10 free trial credits</strong> to get started!</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{settings.app_url}/docs" 
                           style="display: inline-block; background: #007bff; color: white; 
                                  padding: 12px 24px; text-decoration: none; border-radius: 6px;">
                            Explore API Documentation
                        </a>
                    </div>
                    
                    <p>Happy monitoring!</p>
                    <p>The Amazon Product Intelligence Platform Team</p>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            Welcome to Amazon Product Intelligence Platform!
            
            Hi {user_name},
            
            Thanks for joining our platform! You now have access to:
            
            - Real-time Amazon product data
            - FNSKU to ASIN conversion  
            - Price monitoring and alerts
            - Credit-based billing system
            
            You've been credited with 10 free trial credits to get started!
            
            Explore our API documentation at: {settings.app_url}/docs
            
            Happy monitoring!
            The Amazon Product Intelligence Platform Team
            """
            
            await self._send_email(user_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user_email}: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()


# Global service instance
notification_service = NotificationService()