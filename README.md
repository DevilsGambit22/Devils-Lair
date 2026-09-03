# Devil's Lair Daily Sidebar

Upload the **contents** of this ZIP to the root of a GitHub repository and enable GitHub Pages from the main branch/root.

## Automatic boards

- **Daily Battle Board** reads current/registered Devil's Lair Daily team matches from the Chess.com PubAPI.
- **Fresh Souls** reads the newest club members and their current Daily ratings.
- **Infernal Ascent** uses `.github/workflows/snapshot-ratings.yml` to store weekly Daily-rating snapshots and compare rating progress.
- **Daily Match Champs is fully automatic.** `.github/workflows/update-daily-champs.yml` runs after the initial upload and every 6 hours. It reads the most recent **10 completed Devil's Lair Daily team matches**, awards 1 point for a win, 0.5 for a draw, and 0 for a loss, then writes the top three players to `data/daily-champs.json`.

The champions board also displays each leader's W-D-L record for the matches counted. Players listed by Chess.com as fair-play removals are excluded from the calculation.

## Character assets

Only these two mascot assets are used:

- `assets/devil-around-board.png`
- `assets/devil-pointing-winners.png`

No bat GIF is included.

## First deployment

GitHub Actions must be enabled for the repository. The Daily Match Champs workflow includes a manual **Run workflow** option as well as automatic scheduling. If GitHub does not run the workflow immediately after the initial upload, open **Actions → Update Daily Match Champs → Run workflow** once to seed the leaderboard.
