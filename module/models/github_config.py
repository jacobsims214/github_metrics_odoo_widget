# -*- coding: utf-8 -*-
import json
import logging
import requests
from datetime import datetime, timedelta

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

GITHUB_API_BASE = 'https://api.github.com'
GITHUB_GRAPHQL = 'https://api.github.com/graphql'


class GitHubConfig(models.Model):
    """GitHub profile configuration and cached stats."""
    _name = 'simstech.github.config'
    _description = 'GitHub Profile Configuration'
    _rec_name = 'display_name'
    
    # =========================================================================
    # Configuration Fields
    # =========================================================================
    name = fields.Char('Internal Name', required=True, help='Internal reference name')
    display_name = fields.Char('Display Name', help='Name shown on widget (defaults to GitHub name)')
    github_username = fields.Char('GitHub Username', required=True)
    github_token = fields.Char(
        'Personal Access Token',
        help='GitHub PAT for higher rate limits and private stats. '
             'Create at: github.com/settings/tokens (needs: read:user, repo scope)'
    )
    excluded_orgs = fields.Char(
        'Hide These Orgs/Repos',
        help='Comma-separated list of orgs OR specific repos to HIDE from display. '
             'Use org name (e.g., "enterprise-corp") to hide all repos from that org, '
             'or full repo name (e.g., "org/repo-name") to hide a specific repo. '
             'Contribution stats still count from ALL - only the display is filtered.'
    )
    active = fields.Boolean('Active', default=True)
    
    # =========================================================================
    # Display Options
    # =========================================================================
    show_avatar = fields.Boolean('Show Avatar', default=True)
    show_bio = fields.Boolean('Show Bio', default=True)
    show_location = fields.Boolean('Show Location', default=True)
    show_repos = fields.Boolean('Show Repositories', default=True)
    show_stars = fields.Boolean('Show Stars', default=True)
    show_followers = fields.Boolean('Show Followers', default=True)
    show_languages = fields.Boolean('Show Top Languages', default=True)
    show_contributions = fields.Boolean('Show Contribution Graph', default=True)
    max_repos_display = fields.Integer('Max Repos to Show', default=6)
    theme = fields.Selection([
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto (match site)'),
    ], string='Theme', default='auto')
    
    # =========================================================================
    # Cached Data (populated by sync)
    # =========================================================================
    avatar_url = fields.Char('Avatar URL', readonly=True)
    bio = fields.Text('Bio', readonly=True)
    location = fields.Char('Location', readonly=True)
    company = fields.Char('Company', readonly=True)
    blog_url = fields.Char('Blog/Website', readonly=True)
    
    public_repos_count = fields.Integer('Public Repos', readonly=True)
    public_gists_count = fields.Integer('Public Gists', readonly=True)
    followers_count = fields.Integer('Followers', readonly=True)
    following_count = fields.Integer('Following', readonly=True)
    total_stars = fields.Integer('Total Stars Received', readonly=True)
    
    # JSON fields for complex data
    top_repos_json = fields.Text('Top Repositories (JSON)', readonly=True)
    top_languages_json = fields.Text('Top Languages (JSON)', readonly=True)
    contribution_data_json = fields.Text('Contribution Data (JSON)', readonly=True)
    repos_by_org_json = fields.Text('Repos by Org (JSON)', readonly=True)
    
    last_sync = fields.Datetime('Last Synced', readonly=True)
    sync_error = fields.Text('Last Sync Error', readonly=True)
    
    # =========================================================================
    # Computed Fields
    # =========================================================================
    cache_age_hours = fields.Float('Cache Age (hours)', compute='_compute_cache_age')
    is_stale = fields.Boolean('Cache Stale', compute='_compute_cache_age')
    
    @api.depends('last_sync')
    def _compute_cache_age(self):
        for rec in self:
            if rec.last_sync:
                delta = datetime.now() - rec.last_sync.replace(tzinfo=None)
                rec.cache_age_hours = delta.total_seconds() / 3600
                rec.is_stale = rec.cache_age_hours > 1  # Stale after 1 hour
            else:
                rec.cache_age_hours = 999
                rec.is_stale = True
    
    # =========================================================================
    # GitHub API Methods
    # =========================================================================
    def _get_headers(self):
        """Get API headers with optional auth."""
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Odoo-GitHub-Widget/1.0',
        }
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        return headers
    
    def _api_get(self, endpoint):
        """Make authenticated GET request to GitHub API."""
        url = f"{GITHUB_API_BASE}{endpoint}"
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.error(f"GitHub API error: {e}")
            raise UserError(f"GitHub API error: {e}")
    
    def _graphql_query(self, query, variables=None):
        """Execute GraphQL query against GitHub API."""
        if not self.github_token:
            _logger.warning("GraphQL requires authentication token")
            return None
        
        try:
            response = requests.post(
                GITHUB_GRAPHQL,
                headers=self._get_headers(),
                json={'query': query, 'variables': variables or {}},
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            if 'errors' in data:
                _logger.error(f"GraphQL errors: {data['errors']}")
                return None
            return data.get('data')
        except requests.exceptions.RequestException as e:
            _logger.error(f"GitHub GraphQL error: {e}")
            return None
    
    # =========================================================================
    # Sync Methods
    # =========================================================================
    def action_sync_now(self):
        """Manual sync button action."""
        self.ensure_one()
        self._sync_github_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'GitHub Sync',
                'message': f'Successfully synced data for {self.github_username}',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _sync_github_data(self):
        """Fetch and cache all GitHub data including organization repos."""
        self.ensure_one()
        _logger.info(f"Syncing GitHub data for {self.github_username}")
        
        try:
            # 1. Fetch user profile
            user_data = self._api_get(f'/users/{self.github_username}')
            
            # 2. Fetch ALL repos (personal + org) using the authenticated endpoint
            # This gets all repos the user has access to, including org repos
            all_repos = []
            
            if self.github_token:
                # Authenticated: use /user/repos which includes org repos
                # affiliation=owner,collaborator,organization_member gets everything
                page = 1
                while True:
                    repos_page = self._api_get(
                        f'/user/repos?per_page=100&page={page}&affiliation=owner,collaborator,organization_member&sort=updated'
                    )
                    if not repos_page:
                        break
                    all_repos.extend(repos_page)
                    if len(repos_page) < 100:
                        break
                    page += 1
                    if page > 10:  # Safety limit
                        break
            else:
                # Unauthenticated: only personal repos
                all_repos = self._api_get(f'/users/{self.github_username}/repos?per_page=100&sort=updated')
            
            _logger.info(f"Found {len(all_repos)} total accessible repos for {self.github_username}")
            
            # 3. Get organizations the user belongs to (for display)
            orgs = []
            if self.github_token:
                try:
                    orgs = self._api_get(f'/user/orgs')
                    _logger.info(f"User belongs to {len(orgs)} organizations: {[o.get('login') for o in orgs]}")
                except Exception as e:
                    _logger.warning(f"Could not fetch orgs: {e}")
            
            # 4. Fetch contribution data via GraphQL (requires token)
            contribution_data = None
            if self.github_token:
                contribution_data = self._fetch_contribution_data()
            
            # 5. Build repos_by_org from ALL accessible repos (NO FILTERING)
            repos_by_org = {}
            for repo in all_repos:
                owner = repo.get('owner', {}).get('login', 'unknown')
                if owner not in repos_by_org:
                    repos_by_org[owner] = {'count': 0, 'stars': 0}
                repos_by_org[owner]['count'] += 1
                repos_by_org[owner]['stars'] += repo.get('stargazers_count', 0)
            
            repos_by_org_sorted = dict(sorted(repos_by_org.items(), key=lambda x: x[1]['count'], reverse=True))
            
            # 6. Build top repos list from ALL repos (NO FILTERING - filter at display time)
            # Store more than max_repos_display so we can filter later
            top_repos = sorted(all_repos, key=lambda x: x.get('stargazers_count', 0), reverse=True)[:50]
            top_repos_clean = [{
                'name': r['name'],
                'full_name': r['full_name'],
                'description': r.get('description', ''),
                'stars': r.get('stargazers_count', 0),
                'forks': r.get('forks_count', 0),
                'language': r.get('language', ''),
                'url': r.get('html_url', ''),
                'updated_at': r.get('updated_at', ''),
                'owner': r.get('owner', {}).get('login', ''),
            } for r in top_repos]
            
            # Total repos = ALL accessible repos
            total_repo_count = len(all_repos)
            
            # Total stars from ALL repos
            total_stars = sum(repo.get('stargazers_count', 0) for repo in all_repos)
            
            # Aggregate languages from ALL repos
            language_stats = {}
            for repo in all_repos:
                lang = repo.get('language')
                if lang:
                    language_stats[lang] = language_stats.get(lang, 0) + 1
            top_languages = sorted(language_stats.items(), key=lambda x: x[1], reverse=True)[:8]
            
            _logger.info(f"GitHub sync complete: {total_repo_count} contributed repos, {total_stars} stars")
            
            # Update record
            self.write({
                'avatar_url': user_data.get('avatar_url'),
                'bio': user_data.get('bio'),
                'location': user_data.get('location'),
                'company': user_data.get('company'),
                'blog_url': user_data.get('blog'),
                'display_name': self.display_name or user_data.get('name') or self.github_username,
                'public_repos_count': total_repo_count,  # Now includes org repos!
                'public_gists_count': user_data.get('public_gists', 0),
                'followers_count': user_data.get('followers', 0),
                'following_count': user_data.get('following', 0),
                'total_stars': total_stars,
                'top_repos_json': json.dumps(top_repos_clean),
                'top_languages_json': json.dumps(top_languages),
                'contribution_data_json': json.dumps(contribution_data) if contribution_data else None,
                'repos_by_org_json': json.dumps(repos_by_org_sorted),
                'last_sync': fields.Datetime.now(),
                'sync_error': False,
            })
            
            _logger.info(f"GitHub sync complete for {self.github_username}: {total_repo_count} repos, {total_stars} stars")
            
        except Exception as e:
            self.write({
                'sync_error': str(e),
                'last_sync': fields.Datetime.now(),
            })
            _logger.error(f"GitHub sync failed for {self.github_username}: {e}")
            raise
    
    def _fetch_contribution_data(self):
        """Fetch contribution graph data via GraphQL.
        
        Note: GitHub's contributionsCollection only returns last year by default.
        We also fetch restrictedContributionsCount for private repo contributions.
        """
        query = """
        query($username: String!) {
            user(login: $username) {
                contributionsCollection {
                    totalCommitContributions
                    totalPullRequestContributions
                    totalIssueContributions
                    totalPullRequestReviewContributions
                    totalRepositoryContributions
                    restrictedContributionsCount
                    contributionCalendar {
                        totalContributions
                        weeks {
                            contributionDays {
                                date
                                contributionCount
                                contributionLevel
                            }
                        }
                    }
                    commitContributionsByRepository(maxRepositories: 100) {
                        repository {
                            nameWithOwner
                            isPrivate
                        }
                        contributions {
                            totalCount
                        }
                    }
                }
            }
        }
        """
        data = self._graphql_query(query, {'username': self.github_username})
        if data and data.get('user'):
            collection = data['user']['contributionsCollection']
            calendar = collection.get('contributionCalendar', {})
            
            # Flatten the contribution days for easier frontend rendering
            days = []
            for week in calendar.get('weeks', []):
                for day in week.get('contributionDays', []):
                    days.append({
                        'date': day['date'],
                        'count': day['contributionCount'],
                        'level': day['contributionLevel'],
                    })
            
            # Get commits by repository
            commits_by_repo = []
            for repo_contrib in collection.get('commitContributionsByRepository', []):
                repo = repo_contrib.get('repository', {})
                count = repo_contrib.get('contributions', {}).get('totalCount', 0)
                if count > 0:
                    commits_by_repo.append({
                        'repo': repo.get('nameWithOwner', 'Unknown'),
                        'is_private': repo.get('isPrivate', False),
                        'commits': count,
                    })
            
            # Sort by commit count
            commits_by_repo.sort(key=lambda x: x['commits'], reverse=True)
            
            total_commits = collection.get('totalCommitContributions', 0)
            total_prs = collection.get('totalPullRequestContributions', 0)
            total_issues = collection.get('totalIssueContributions', 0)
            total_reviews = collection.get('totalPullRequestReviewContributions', 0)
            restricted = collection.get('restrictedContributionsCount', 0)
            
            _logger.info(f"Contributions for {self.github_username}: "
                        f"commits={total_commits}, PRs={total_prs}, issues={total_issues}, "
                        f"reviews={total_reviews}, restricted={restricted}, "
                        f"repos_contributed_to={len(commits_by_repo)}")
            
            return {
                'total_commits': total_commits,
                'total_prs': total_prs,
                'total_issues': total_issues,
                'total_reviews': total_reviews,
                'total_repo_contributions': collection.get('totalRepositoryContributions', 0),
                'restricted_contributions': restricted,
                'total_contributions': calendar.get('totalContributions', 0),
                'commits_by_repo': commits_by_repo[:20],  # Top 20 repos
                'days': days[-365:],
                'note': 'Data is for the last 12 months (GitHub limitation)',
            }
        return None
    
    # =========================================================================
    # Cron Job
    # =========================================================================
    @api.model
    def _cron_sync_all(self):
        """Scheduled job to refresh all active GitHub configs."""
        configs = self.search([('active', '=', True)])
        for config in configs:
            try:
                config._sync_github_data()
            except Exception as e:
                _logger.error(f"Cron sync failed for {config.github_username}: {e}")
        _logger.info(f"GitHub cron sync complete. Processed {len(configs)} configs.")
    
    # =========================================================================
    # Public API for Frontend
    # =========================================================================
    def get_public_data(self):
        """Return data safe for frontend (excludes token).
        
        Exclusion filtering happens HERE (at display time) so you can
        change excluded_orgs without re-syncing.
        """
        self.ensure_one()
        
        # Auto-sync if stale
        if self.is_stale:
            try:
                self._sync_github_data()
            except Exception:
                pass  # Use cached data if sync fails
        
        # Parse excluded orgs (lowercase for comparison)
        excluded_orgs = set()
        if self.excluded_orgs:
            excluded_orgs = {org.strip().lower() for org in self.excluded_orgs.split(',') if org.strip()}
        
        # Filter repos_by_org (remove excluded orgs)
        repos_by_org_raw = json.loads(self.repos_by_org_json) if self.repos_by_org_json else {}
        repos_by_org_filtered = {
            org: data for org, data in repos_by_org_raw.items()
            if org.lower() not in excluded_orgs
        } if self.show_repos else {}
        
        # Filter top_repos (remove repos from excluded orgs)
        top_repos_raw = json.loads(self.top_repos_json) if self.top_repos_json else []
        top_repos_filtered = [
            repo for repo in top_repos_raw
            if repo.get('owner', '').lower() not in excluded_orgs
        ][:self.max_repos_display] if self.show_repos else []
        
        return {
            'id': self.id,
            'username': self.github_username,
            'display_name': self.display_name or self.github_username,
            'avatar_url': self.avatar_url,
            'bio': self.bio if self.show_bio else None,
            'location': self.location if self.show_location else None,
            'company': self.company,
            'blog_url': self.blog_url,
            'stats': {
                'repos': self.public_repos_count if self.show_repos else None,
                'stars': self.total_stars if self.show_stars else None,
                'followers': self.followers_count if self.show_followers else None,
                'following': self.following_count,
            },
            'repos_by_org': repos_by_org_filtered,
            'top_repos': top_repos_filtered,
            'languages': json.loads(self.top_languages_json) if self.top_languages_json and self.show_languages else [],
            'contributions': json.loads(self.contribution_data_json) if self.contribution_data_json and self.show_contributions else None,
            'theme': self.theme,
            'show': {
                'avatar': self.show_avatar,
                'bio': self.show_bio,
                'location': self.show_location,
                'repos': self.show_repos,
                'stars': self.show_stars,
                'followers': self.show_followers,
                'languages': self.show_languages,
                'contributions': self.show_contributions,
            },
            'excluded_orgs': list(excluded_orgs),  # Send to frontend for debugging
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
        }

