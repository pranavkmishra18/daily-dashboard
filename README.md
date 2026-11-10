# Daily Dashboard — GitHub Pages (manual refresh)

This project runs your existing `daily.py`, wraps its terminal output in a responsive professional webpage, and publishes it with GitHub Pages.

## Refresh behaviour

**Manual only:** there is no daily schedule and no automatic run when you push changes. To refresh the website, go to the repository's **Actions** tab → **Build and publish daily dashboard** → **Run workflow** → **Run workflow**. Wait for the run and deployment to finish.

## Important privacy warning

GitHub Pages websites are public by default. Anyone with the URL can view the published page. The dashboard displays stock names, purchase prices and percentage performance. Holding quantities, total holding values and profit/loss amounts are not included in the current source or generated display. Purchase prices and stock names are still visible publicly. A private source repository does not automatically make its Pages website private.

If you need the dashboard to remain private, do not enable this public Pages deployment; use an authenticated hosting service instead.

## Setup

1. Create a GitHub repository named `daily-dashboard`.
2. Upload the contents of this project folder to the repository's `main` branch. Keep `.github/workflows/daily-dashboard.yml` in that exact path.
3. Open repository **Settings → Pages**.
4. Under **Build and deployment → Source**, select **GitHub Actions**.
5. Open **Actions → Build and publish daily dashboard**.
6. Click **Run workflow**, choose `main` if prompted, then click the green **Run workflow** button.
7. Wait for a green check mark. Find the website URL under **Settings → Pages**. It will usually look like `https://YOUR-USERNAME.github.io/daily-dashboard/`.

## Files

- `daily.py` — your Python dashboard.
- `generate_site.py` — runs `daily.py` and generates `docs/index.html`.
- `.github/workflows/daily-dashboard.yml` — manually triggered build and deployment.
- `requirements.txt` — Python dependency.

## Later updates

Commit your revised `daily.py`, then manually run the workflow again from the Actions tab to refresh the published snapshot.

## Troubleshooting

- Workflow missing: check that the YAML file is under `.github/workflows/` on `main`.
- Pages deployment denied: check **Settings → Pages → Source = GitHub Actions** and ensure Actions are enabled.
- Build failed: open the failed run and expand the failed step. The workflow will not deploy if `daily.py` fails.
- Old page: rerun the workflow, wait for deployment to finish, then hard-refresh the browser.

Market data comes from external providers and may be delayed or unavailable. Verify prices with your broker before trading.
