# -*- coding: utf-8 -*-
{
    'name': 'GitHub Stats Widget',
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': 'Display GitHub profile stats as a website snippet',
    'description': """
        A website widget that displays GitHub profile metrics including:
        - Profile information (avatar, bio, location)
        - Repository count and stars
        - Top programming languages
        - Recent activity
        
        Configure your GitHub credentials securely in the backend,
        then drag the widget onto any website page.
    """,
    'author': 'SimsTech',
    'website': 'https://simstech.dev',
    'license': 'LGPL-3',
    'depends': ['website'],
    'data': [
        'security/ir.model.access.csv',
        'security/github_security.xml',
        'views/github_config_views.xml',
        'views/snippets.xml',
        'data/github_cron.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'widget_github_stats/static/src/scss/github_stats.scss',
            'widget_github_stats/static/src/js/github_stats_widget.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}

