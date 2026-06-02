# FPL Analyst

**FPL Analyst** is a Streamlit-based Fantasy Premier League analytics dashboard.

Live app: https://fplanalysis.com

The dashboard helps FPL managers explore player value, selection trends, team dependency, consistency, fixture difficulty and Premier League table data using publicly available football APIs.

## Features

- Player value analysis: points per price
- Selection rate vs total points analysis
- Scout assistant for filtering players by position, price, minutes, points and ownership
- Team Dependency Ratio (TDR)
- Player consistency index based on weekly points
- Fixture difficulty analysis
- Premier League table view
- Dynamic player statistics ranking
- Chip suggestion panel

## Tech Stack

- Python
- Streamlit
- pandas
- requests
- matplotlib
- Altair
- Nginx
- systemd
- Amazon Lightsail

## Project Structure

```text
fpl-analysis/
├── assets/
│   └── header.png
├── data/
│   ├── league_table.csv
│   ├── player_stats.csv
│   └── weekly_points.csv
├── weekly_exec/
│   └── weekly_execution.py
├── analytics.py
├── paths.py
├── streamlit_app.py
├── visuals.py
├── requirements.txt
└── README.md
```

## Local Setup

Create or activate your Python environment:

```bash
conda activate temizveri
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app locally:

```bash
streamlit run streamlit_app.py
```

The app should open at:

```text
http://localhost:8501
```

## Data Refresh

Weekly/static CSV data can be refreshed with:

```bash
python weekly_exec/weekly_execution.py
```

If module imports fail when running the weekly script, run it from the project root and set `PYTHONPATH` first:

```powershell
$env:PYTHONPATH="."
python weekly_exec\weekly_execution.py
```

## Deployment

The production deployment runs on an Amazon Lightsail Linux instance.

Current deployment summary:

```text
Project directory: /home/ec2-user/fpl-analysis
Virtual environment: /home/ec2-user/fpl-analysis/venv
Streamlit file: streamlit_app.py
Streamlit port: 127.0.0.1:8501
Reverse proxy: Nginx
SSL: Let's Encrypt / Certbot
```

Deploy latest code from GitHub:

```bash
cd /home/ec2-user/fpl-analysis
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart streamlit
sudo systemctl status streamlit --no-pager
```

Check logs:

```bash
sudo journalctl -u streamlit -n 100 --no-pager
```

## SEO Notes

The app includes:

- Google Search Console verification meta tag
- SEO-focused page title
- Basic in-page description
- Branded H1 title: `FPL Analyst`

For better discovery, use Google Search Console to request indexing after major changes.

## Traffic Monitoring

Quick Nginx access log checks:

```bash
sudo tail -n 100 /var/log/nginx/access.log
sudo awk '{print $1}' /var/log/nginx/access.log | sort | uniq | wc -l
sudo awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -nr | head
```

For detailed traffic analysis, add Google Analytics 4 or a privacy-friendly analytics tool such as Plausible.
