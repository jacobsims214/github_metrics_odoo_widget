/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * GitHub Stats Widget
 * 
 * Renders GitHub profile stats fetched from the backend.
 * The backend caches data from GitHub API, so this is fast.
 */
publicWidget.registry.GitHubStatsWidget = publicWidget.Widget.extend({
    selector: '.github-stats-widget',
    
    start() {
        const configId = this.el.dataset.configId;
        const layout = this.el.dataset.layout || 'card';
        
        if (!configId) {
            // No config selected - show placeholder in edit mode
            return this._super.apply(this, arguments);
        }
        
        return this._loadStats(configId, layout);
    },
    
    async _loadStats(configId, layout) {
        try {
            const response = await fetch(`/github/stats/${configId}`);
            if (!response.ok) throw new Error('Failed to load stats');
            
            const data = await response.json();
            this._render(data, layout);
        } catch (error) {
            console.error('GitHub widget error:', error);
            this.el.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fa fa-exclamation-triangle"></i>
                    Unable to load GitHub stats
                </div>
            `;
        }
    },
    
    _render(data, layout) {
        const theme = data.theme === 'auto' ? '' : `github-theme-${data.theme}`;
        
        // Build stats HTML
        const statsHtml = this._buildStatsHtml(data);
        const reposByOrgHtml = data.show.repos && data.repos_by_org ? this._buildReposByOrgHtml(data.repos_by_org) : '';
        const contributionBreakdownHtml = data.show.contributions && data.contributions ? this._buildContributionBreakdownHtml(data.contributions) : '';
        const reposHtml = data.show.repos && data.top_repos?.length ? this._buildReposHtml(data.top_repos) : '';
        const languagesHtml = data.show.languages && data.languages?.length ? this._buildLanguagesHtml(data.languages) : '';
        const contributionsHtml = data.show.contributions && data.contributions ? this._buildContributionsHtml(data.contributions) : '';
        
        this.el.innerHTML = `
            <div class="github-card ${theme} github-layout-${layout}">
                <!-- Header with avatar and name -->
                <div class="github-header">
                    ${data.show.avatar && data.avatar_url ? `
                        <img src="${data.avatar_url}" alt="${data.display_name}" class="github-avatar"/>
                    ` : ''}
                    <div class="github-header-info">
                        <h3 class="github-name">${data.display_name}</h3>
                        <a href="https://github.com/${data.username}" target="_blank" class="github-username">
                            @${data.username}
                        </a>
                        ${data.bio ? `<p class="github-bio">${data.bio}</p>` : ''}
                        ${data.location ? `
                            <p class="github-location">
                                <i class="fa fa-map-marker"></i> ${data.location}
                            </p>
                        ` : ''}
                    </div>
                </div>
                
                <!-- Stats grid -->
                ${statsHtml}
                
                <!-- Contribution breakdown -->
                ${contributionBreakdownHtml}
                
                <!-- Repos by org -->
                ${reposByOrgHtml}
                
                <!-- Top languages -->
                ${languagesHtml}
                
                <!-- Contribution graph -->
                ${contributionsHtml}
                
                <!-- Top repositories -->
                ${reposHtml}
                
                <!-- Footer -->
                <div class="github-footer">
                    <a href="https://github.com/${data.username}" target="_blank" class="github-profile-link">
                        <i class="fa fa-github"></i> View Full Profile
                    </a>
                </div>
            </div>
        `;
    },
    
    _buildStatsHtml(data) {
        const stats = [];
        
        if (data.show.repos && data.stats.repos !== null) {
            stats.push({ icon: 'fa-book', value: data.stats.repos, label: 'Repositories' });
        }
        if (data.show.stars && data.stats.stars !== null) {
            stats.push({ icon: 'fa-star', value: data.stats.stars, label: 'Stars' });
        }
        if (data.show.followers && data.stats.followers !== null) {
            stats.push({ icon: 'fa-users', value: data.stats.followers, label: 'Followers' });
        }
        if (data.contributions?.total_contributions) {
            stats.push({ icon: 'fa-code', value: data.contributions.total_contributions, label: 'Contributions' });
        }
        
        if (!stats.length) return '';
        
        return `
            <div class="github-stats-grid">
                ${stats.map(s => `
                    <div class="github-stat">
                        <i class="fa ${s.icon}"></i>
                        <span class="github-stat-value">${this._formatNumber(s.value)}</span>
                        <span class="github-stat-label">${s.label}</span>
                    </div>
                `).join('')}
            </div>
        `;
    },
    
    _buildLanguagesHtml(languages) {
        const colors = {
            'JavaScript': '#f1e05a',
            'TypeScript': '#3178c6',
            'Python': '#3572A5',
            'Java': '#b07219',
            'C++': '#f34b7d',
            'C#': '#178600',
            'Ruby': '#701516',
            'Go': '#00ADD8',
            'Rust': '#dea584',
            'PHP': '#4F5D95',
            'Swift': '#F05138',
            'Kotlin': '#A97BFF',
            'HTML': '#e34c26',
            'CSS': '#563d7c',
            'SCSS': '#c6538c',
            'Shell': '#89e051',
            'Vue': '#41b883',
        };
        
        const total = languages.reduce((sum, [_, count]) => sum + count, 0);
        
        return `
            <div class="github-languages">
                <h4 class="github-section-title">Top Languages</h4>
                <div class="github-lang-bar">
                    ${languages.map(([lang, count]) => {
                        const pct = (count / total * 100).toFixed(1);
                        const color = colors[lang] || '#8b8b8b';
                        return `<div class="github-lang-segment" style="width: ${pct}%; background: ${color}" title="${lang}: ${pct}%"></div>`;
                    }).join('')}
                </div>
                <div class="github-lang-legend">
                    ${languages.slice(0, 5).map(([lang, count]) => {
                        const color = colors[lang] || '#8b8b8b';
                        const pct = (count / total * 100).toFixed(1);
                        return `
                            <span class="github-lang-item">
                                <span class="github-lang-dot" style="background: ${color}"></span>
                                ${lang} <span class="github-lang-pct">${pct}%</span>
                            </span>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    },
    
    _buildContributionBreakdownHtml(contributions) {
        if (!contributions) return '';
        
        const items = [
            { icon: 'fa-code', value: contributions.total_commits || 0, label: 'Commits' },
            { icon: 'fa-code-fork', value: contributions.total_prs || 0, label: 'Pull Requests' },
            { icon: 'fa-exclamation-circle', value: contributions.total_issues || 0, label: 'Issues' },
            { icon: 'fa-comments', value: contributions.total_reviews || 0, label: 'Code Reviews' },
        ];
        
        // Add restricted contributions note if any
        const restrictedNote = contributions.restricted_contributions > 0 
            ? `<p class="github-restricted-note"><i class="fa fa-lock"></i> +${contributions.restricted_contributions} private contributions</p>`
            : '';
        
        return `
            <div class="github-contrib-breakdown">
                <h4 class="github-section-title">Activity Breakdown <span class="github-year-note">(last 12 months)</span></h4>
                <div class="github-contrib-types">
                    ${items.map(item => `
                        <div class="github-contrib-type">
                            <i class="fa ${item.icon}"></i>
                            <span class="github-contrib-value">${this._formatNumber(item.value)}</span>
                            <span class="github-contrib-label">${item.label}</span>
                        </div>
                    `).join('')}
                </div>
                ${restrictedNote}
            </div>
        `;
    },
    
    _buildReposByOrgHtml(reposByOrg) {
        if (!reposByOrg || Object.keys(reposByOrg).length === 0) return '';
        
        const orgs = Object.entries(reposByOrg).slice(0, 8); // Top 8 orgs
        
        return `
            <div class="github-repos-by-org">
                <h4 class="github-section-title">Repositories by Organization</h4>
                <div class="github-org-list">
                    ${orgs.map(([org, data]) => `
                        <a href="https://github.com/${org}" target="_blank" class="github-org-item">
                            <span class="github-org-name">${org}</span>
                            <span class="github-org-stats">
                                <span class="github-org-repos">${data.count} repos</span>
                                ${data.stars > 0 ? `<span class="github-org-stars"><i class="fa fa-star"></i> ${this._formatNumber(data.stars)}</span>` : ''}
                            </span>
                        </a>
                    `).join('')}
                </div>
            </div>
        `;
    },
    
    _buildContributionsHtml(contributions) {
        if (!contributions?.days?.length) return '';
        
        // Build a simple contribution graph (last ~12 weeks for compact display)
        const recentDays = contributions.days.slice(-84); // 12 weeks
        
        const levelColors = {
            'NONE': 'var(--github-contrib-0, #ebedf0)',
            'FIRST_QUARTILE': 'var(--github-contrib-1, #9be9a8)',
            'SECOND_QUARTILE': 'var(--github-contrib-2, #40c463)',
            'THIRD_QUARTILE': 'var(--github-contrib-3, #30a14e)',
            'FOURTH_QUARTILE': 'var(--github-contrib-4, #216e39)',
        };
        
        return `
            <div class="github-contributions">
                <h4 class="github-section-title">
                    ${this._formatNumber(contributions.total_contributions)} contributions in the last year
                </h4>
                <div class="github-contrib-grid">
                    ${recentDays.map(day => `
                        <div class="github-contrib-day" 
                             style="background: ${levelColors[day.level] || levelColors.NONE}"
                             title="${day.date}: ${day.count} contributions">
                        </div>
                    `).join('')}
                </div>
                <div class="github-contrib-legend">
                    <span>Less</span>
                    ${Object.values(levelColors).map(color => `
                        <div class="github-contrib-day" style="background: ${color}"></div>
                    `).join('')}
                    <span>More</span>
                </div>
            </div>
        `;
    },
    
    _buildReposHtml(repos) {
        return `
            <div class="github-repos">
                <h4 class="github-section-title">Top Repositories</h4>
                <div class="github-repos-grid">
                    ${repos.map(repo => `
                        <a href="${repo.url}" target="_blank" class="github-repo-card">
                            <div class="github-repo-name">
                                <i class="fa fa-book"></i> ${repo.name}
                            </div>
                            ${repo.description ? `<p class="github-repo-desc">${repo.description}</p>` : ''}
                            <div class="github-repo-meta">
                                ${repo.language ? `
                                    <span class="github-repo-lang">${repo.language}</span>
                                ` : ''}
                                <span class="github-repo-stars">
                                    <i class="fa fa-star"></i> ${repo.stars}
                                </span>
                                <span class="github-repo-forks">
                                    <i class="fa fa-code-fork"></i> ${repo.forks}
                                </span>
                            </div>
                        </a>
                    `).join('')}
                </div>
            </div>
        `;
    },
    
    _formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    },
});

export default publicWidget.registry.GitHubStatsWidget;

