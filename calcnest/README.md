# MoneyMath

Static website of calculators and unit converters. No backend, no database.

## Change the basics
Open `build.py` and edit SITE_NAME, SITE_URL (your real domain) and CONTACT_EMAIL at the top.

## Rebuild
    python3 build.py
This writes the finished website into `site/`.

## Deploy (free)
1. Push this folder to a GitHub repo.
2. Cloudflare Pages -> Create project -> connect the repo.
3. Build command: (none). Build output directory: `site`.
4. Add your domain, then submit https://yourdomain/sitemap.xml in Google Search Console.

## Add a tool
Copy an entry in CALCULATORS or CONVERTERS in `build.py`, change the text, run `python3 build.py`.
New calculator maths goes in `src/assets/app.js` (CALCS). New units go in UNITS in `build.py`.

## Turn on ads (after AdSense approval)
1. Paste your AdSense script into the marked comment in `head()` in `build.py`.
2. Add class="ads" to the <html> tag in `head()`.
3. Put your ad unit code inside the `ad()` function's div.
Ad slots are hidden until step 2, so the site looks clean before approval.

## Before you launch
- Expand the text under each tool to 300-500 words in your own words and add things you know.
- Have the Privacy Policy and Terms reviewed, and check GST rates on the official portal.

## US and India calculators
- US finance tools live in `us_tools.py` (mortgage, auto loan, compound interest, retirement, credit card payoff, take-home pay). The browser maths is in `src/assets/app.js`.
- Tax figures are for tax year 2026 (`TAX2026` in `us_tools.py`). Update them each autumn when the IRS publishes new numbers.
- India tools (EMI, SIP, GST) stay in `build.py`. To add more India tools later, copy an entry in CALCULATORS and add its slug to the MARKET table.
