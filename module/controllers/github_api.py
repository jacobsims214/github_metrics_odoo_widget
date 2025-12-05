# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class GitHubWidgetController(http.Controller):
    """Public API for GitHub stats widget."""
    
    @http.route('/github/stats/<int:config_id>', type='http', auth='public', website=True, csrf=False)
    def get_github_stats(self, config_id, **kwargs):
        """
        Public endpoint to fetch GitHub stats for a widget.
        
        This is called by the frontend widget to get the latest data.
        Data is cached in the database, so this is fast.
        """
        try:
            config = request.env['simstech.github.config'].sudo().browse(config_id)
            
            if not config.exists() or not config.active:
                return request.make_json_response(
                    {'error': 'Configuration not found'},
                    status=404
                )
            
            data = config.get_public_data()
            
            return request.make_json_response(data)
            
        except Exception as e:
            _logger.error(f"Error fetching GitHub stats: {e}")
            return request.make_json_response(
                {'error': 'Internal server error'},
                status=500
            )
    
    @http.route('/github/configs', type='http', auth='public', website=True, csrf=False)
    def list_configs(self, **kwargs):
        """
        List available GitHub configs for the snippet selector.
        Returns minimal info (id, name) for active configs.
        """
        try:
            configs = request.env['simstech.github.config'].sudo().search([
                ('active', '=', True)
            ])
            
            data = [{
                'id': c.id,
                'name': c.display_name or c.github_username,
                'username': c.github_username,
            } for c in configs]
            
            return request.make_json_response(data)
            
        except Exception as e:
            _logger.error(f"Error listing GitHub configs: {e}")
            return request.make_json_response(
                {'error': 'Internal server error'},
                status=500
            )

