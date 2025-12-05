# GitHub Stats Widget for Odoo 17

A website snippet that displays your GitHub profile stats, repositories, and contribution activity.

## Features

- 📊 **Profile Stats**: Repos, stars, followers, contributions
- 📈 **Contribution Graph**: GitHub-style heatmap (requires token)
- 🔤 **Top Languages**: Visual breakdown of your tech stack
- 📦 **Top Repositories**: Showcase your best work
- 🎨 **Themes**: Light, dark, or auto (matches site theme)
- 🔄 **Auto-sync**: Hourly cron job keeps data fresh
- 🔒 **Secure**: GitHub token stored server-side, never exposed

## Installation

1. Place this module in your Odoo addons directory
2. Update the apps list: `Apps → Update Apps List`
3. Install "GitHub Stats Widget"

## Configuration

### 1. Create a GitHub Personal Access Token

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Name: `Odoo Portfolio Widget`
4. Scopes needed:
   - `read:user` - Read your profile info
   - `repo` (optional) - For private repo stats
5. Copy the token

### 2. Configure in Odoo

1. Go to **GitHub Widget → Profiles**
2. Create a new profile:
   - **GitHub Username**: Your username (e.g., `octocat`)
   - **Personal Access Token**: Paste your token
3. Click **Sync Now** to fetch your data
4. Configure display options as needed

### 3. Add to Your Website

1. Go to **Website → Edit** any page
2. In the snippet panel, find "GitHub Stats"
3. Drag it onto your page
4. Select your profile in the snippet options
5. Save and publish

## API Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `/github/stats/<id>` | Public | Get stats for a config |
| `/github/configs` | Public | List available configs |

## Rate Limits

- **Without token**: 60 requests/hour (shared across users)
- **With token**: 5,000 requests/hour

The module caches data in the database and syncs hourly, so you won't hit rate limits.

## Customization

### SCSS Variables

Override these CSS variables to match your site:

```scss
:root {
    --github-bg: #ffffff;
    --github-text: #24292f;
    --github-accent: #1f6feb;
    // ... see github_stats.scss for all variables
}
```

## Security

- GitHub tokens are stored encrypted in the database
- Tokens are never exposed to the frontend
- Only system administrators can view/edit tokens
- Public API only returns cached, non-sensitive data

## License

LGPL-3

## Author

SimsTech - [simstech.dev](https://simstech.dev)

