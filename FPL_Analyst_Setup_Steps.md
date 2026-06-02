# FPL Analyst – Next Setup Steps

## 1. Deploy latest code to Lightsail

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

## 2. Confirm header image exists

```bash
cd /home/ec2-user/fpl-analysis
ls -lh assets/header.png
```

If it does not exist, make sure `assets/header.png` is committed and pushed from local Git.

## 3. Google Search Console

1. Open Google Search Console.
2. Select the property for `fplanalysis.com`.
3. Use **URL Inspection**.
4. Enter `https://fplanalysis.com`.
5. Click **Request indexing**.
6. Check **Performance** over the following days.

Useful Google search checks:

```text
site:fplanalysis.com
site:fplanalysis.com "FPL Analyst"
```

## 4. Add Google Analytics 4 later

Recommended flow:

1. Create a GA4 property.
2. Create a Web data stream for `https://fplanalysis.com`.
3. Copy the Measurement ID, like `G-XXXXXXXXXX`.
4. Add the GA script to Streamlit using `st.components.v1.html()` or move tracking to Nginx/static HTML if preferred.
5. Deploy and verify real-time traffic in GA4.

## 5. Optional: Add Nginx-level sitemap and robots.txt

Create files:

```bash
sudo mkdir -p /var/www/fplanalysis
sudo nano /var/www/fplanalysis/robots.txt
sudo nano /var/www/fplanalysis/sitemap.xml
```

Example `robots.txt`:

```text
User-agent: *
Allow: /

Sitemap: https://fplanalysis.com/sitemap.xml
```

Example `sitemap.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://fplanalysis.com/</loc>
    <priority>1.0</priority>
  </url>
</urlset>
```

Then update Nginx server block:

```nginx
location = /robots.txt {
    root /var/www/fplanalysis;
}

location = /sitemap.xml {
    root /var/www/fplanalysis;
}
```

Reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 6. Quick traffic commands

Unique IP count:

```bash
sudo awk '{print $1}' /var/log/nginx/access.log | sort | uniq | wc -l
```

Top visitor IPs:

```bash
sudo awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -nr | head
```

Most requested paths:

```bash
sudo awk '{print $7}' /var/log/nginx/access.log | sort | uniq -c | sort -nr | head
```

Recent requests:

```bash
sudo tail -f /var/log/nginx/access.log
```
