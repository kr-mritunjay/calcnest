#!/usr/bin/env python3
"""
MoneyMath static site generator.

    python3 build.py

Reads src/assets/*, writes the finished website into site/.
Upload (or connect to Cloudflare Pages / Netlify) the site/ folder.

To add a tool: add one entry to CALCULATORS or CONVERTERS below, run the script again.
"""
import html
import json
import shutil
from datetime import date
from pathlib import Path

from us_tools import TAX2026, get_us_calculators

# ----------------------------------------------------------------------------
# Settings — change these first
# ----------------------------------------------------------------------------
SITE_NAME = "MoneyMath"
SITE_URL = "https://moneymathtool.com"
CONTACT_EMAIL = "moneymath.contact@gmail.com"
TAGLINE = "Free online calculators and unit converters"
TODAY = date.today().isoformat()

ROOT = Path(__file__).parent
SRC = ROOT / "src"
OUT = ROOT / "site"

esc = html.escape

# ----------------------------------------------------------------------------
# Unit data (shared with the browser through assets/units.js)
# ----------------------------------------------------------------------------
UNITS = {
    "length": {"label": "Length", "units": [
        {"id": "km", "name": "Kilometres (km)", "f": 1000},
        {"id": "m", "name": "Metres (m)", "f": 1},
        {"id": "cm", "name": "Centimetres (cm)", "f": 0.01},
        {"id": "mm", "name": "Millimetres (mm)", "f": 0.001},
        {"id": "mi", "name": "Miles (mi)", "f": 1609.344},
        {"id": "yd", "name": "Yards (yd)", "f": 0.9144},
        {"id": "ft", "name": "Feet (ft)", "f": 0.3048},
        {"id": "in", "name": "Inches (in)", "f": 0.0254},
    ]},
    "weight": {"label": "Weight", "units": [
        {"id": "kg", "name": "Kilograms (kg)", "f": 1},
        {"id": "g", "name": "Grams (g)", "f": 0.001},
        {"id": "mg", "name": "Milligrams (mg)", "f": 0.000001},
        {"id": "t", "name": "Tonnes (t)", "f": 1000},
        {"id": "lb", "name": "Pounds (lb)", "f": 0.45359237},
        {"id": "oz", "name": "Ounces (oz)", "f": 0.028349523125},
    ]},
    "temperature": {"label": "Temperature", "units": [
        {"id": "c", "name": "Celsius (°C)", "f": 1},
        {"id": "f", "name": "Fahrenheit (°F)", "f": 1},
        {"id": "k", "name": "Kelvin (K)", "f": 1},
    ]},
}


def _factor(cat, uid):
    return next(u["f"] for u in UNITS[cat]["units"] if u["id"] == uid)


def convert(cat, frm, to, x):
    if cat == "temperature":
        base = x if frm == "c" else (x - 32) * 5 / 9 if frm == "f" else x - 273.15
        return base if to == "c" else base * 9 / 5 + 32 if to == "f" else base + 273.15
    return x * _factor(cat, frm) / _factor(cat, to)


def fmt(n, places=4):
    s = f"{n:,.{places}f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


def emi_calc(p, rate, years):
    r, n = rate / 1200, round(years * 12)
    return p * r * (1 + r) ** n / ((1 + r) ** n - 1)


def inr(n):
    """Indian digit grouping: 1245501 -> 12,45,501"""
    s = str(int(round(n)))
    if len(s) <= 3:
        return "₹" + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return "₹" + ",".join(parts) + "," + tail


def sip_calc(monthly, rate, years):
    i, n = rate / 1200, round(years * 12)
    bal = 0.0
    for _ in range(n):
        bal = (bal + monthly) * (1 + i)
    return bal, monthly * n


# ----------------------------------------------------------------------------
# HTML building blocks
# ----------------------------------------------------------------------------
def num_field(fid, label, value, mn, mx, step, prefix="", suffix="", slider=True, presets=None, words=False, of=None):
    pre = f'<span class="pre">{esc(prefix)}</span>' if prefix else ""
    suf = f'<span class="suf">{esc(suffix)}</span>' if suffix else ""
    sl = (f'<input class="slider" type="range" min="{mn}" max="{mx}" step="{step}" value="{value}" '
          f'aria-label="{esc(label)} slider">') if slider else ""
    chips = ""
    if presets:
        chips = '<div class="chips">' + "".join(
            f'<button type="button" class="chip" data-v="{p}" aria-pressed="false">{p}{esc(suffix)}</button>'
            for p in presets) + "</div>"
    hint = '<p class="hint" aria-live="polite"></p>' if (words or of) else ""
    of_attr = f' data-of="{of}"' if of else ""
    return (f'<div class="field" data-field="{fid}"{" data-words" if words else ""}{of_attr}>'
            f'<div class="field-head"><label for="f-{fid}">{esc(label)}</label>'
            f'<div class="input">{pre}<input id="f-{fid}" name="{fid}" type="number" step="any" inputmode="decimal" '
            f'value="{value}">{suf}</div></div>{sl}{hint}{chips}</div>')


def seg_field(fid, label, options, default):
    btns = "".join(
        f'<button type="button" data-v="{v}" aria-pressed="{"true" if v == default else "false"}">{esc(t)}</button>'
        for v, t in options)
    return (f'<div class="field"><div class="field-head"><span class="lbl">{esc(label)}</span></div>'
            f'<div class="seg" data-field="{fid}" role="group" aria-label="{esc(label)}">{btns}</div></div>')


def date_field(fid, label, value=""):
    return (f'<div class="field" data-field="{fid}"><div class="field-head"><label for="f-{fid}">{esc(label)}</label>'
            f'<div class="input"><input id="f-{fid}" name="{fid}" type="date" value="{value}"></div></div></div>')


def calc_panel(key, left, title=""):
    h = f"<h2>{esc(title)}</h2>" if title else ""
    return (f'<form class="panel" data-calc="{key}" novalidate>{h}<div class="calc-grid"><div>{left}</div>'
            f'<div class="out" aria-live="polite"></div></div></form>')


def mini_panel(key, title, before, a_label, a_val, mid, b_label, b_val, a_suffix="", b_suffix=""):
    sa = f'<span class="suf">{a_suffix}</span>' if a_suffix else ""
    sb = f'<span class="suf">{b_suffix}</span>' if b_suffix else ""
    sentence = (f'<div class="sentence">{before} '
                f'<span class="input" data-field="x"><input type="number" step="any" name="x" value="{a_val}" aria-label="{a_label}">{sa}</span> '
                f'{mid} <span class="input" data-field="y"><input type="number" step="any" name="y" value="{b_val}" aria-label="{b_label}">{sb}</span></div>')
    return (f'<form class="panel" data-calc="{key}" novalidate><h2>{esc(title)}</h2>'
            f'<div class="mini">{sentence}<div class="out" aria-live="polite"></div></div></form>')


def conv_form(cat, frm, to, value=1, hero=False):
    cat_select = ""
    if hero:
        opts = "".join(f'<option value="{k}"{" selected" if k == cat else ""}>{v["label"]}</option>' for k, v in UNITS.items())
        cat_select = f'<div class="cfield cat"><span class="lbl">Convert</span><select name="cat" aria-label="Category">{opts}</select></div>'
    cls = "hero-card" if hero else "panel"
    heading = "<h2>Try a quick conversion</h2>" if hero else ""
    return (f'<form class="{cls}" data-conv data-cat="{cat}" data-from="{frm}" data-to="{to}" novalidate>{heading}{cat_select}'
            f'<div class="conv-grid">'
            f'<div class="cfield"><label class="lbl" for="cv-val{"-h" if hero else ""}">From</label>'
            f'<input id="cv-val{"-h" if hero else ""}" name="val" type="number" step="any" inputmode="decimal" value="{value}">'
            f'<select name="from" aria-label="From unit"></select></div>'
            f'<button type="button" class="swap" aria-label="Swap units">⇄</button>'
            f'<div class="cfield"><span class="lbl">To</span><output class="cout" aria-live="polite"></output>'
            f'<select name="to" aria-label="To unit"></select></div></div>'
            f'<p class="formula"></p></form>')


def ref_table(cat, frm, to, values):
    def lab(u):
        n = next(x["name"] for x in UNITS[cat]["units"] if x["id"] == u)
        return n
    rows = "".join(f"<tr><td>{fmt(v)}</td><td>{fmt(convert(cat, frm, to, v), 4)}</td></tr>" for v in values)
    return (f'<div class="table-scroll"><table class="ref"><thead><tr><th>{esc(lab(frm))}</th><th>{esc(lab(to))}</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div>")


# ----------------------------------------------------------------------------
# Tools
# ----------------------------------------------------------------------------
_emi = emi_calc(1000000, 9, 5)
_sip, _sip_inv = sip_calc(5000, 12, 10)

CALCULATORS = [
    {
        "slug": "emi-calculator", "name": "EMI Calculator", "glyph": "₹",
        "short": "Monthly loan EMI, interest and total cost",
        "title": "EMI Calculator – Calculate Loan EMI Online (Free)",
        "desc": "Free EMI calculator for home, car and personal loans. Enter amount, interest rate and tenure to see your monthly EMI, total interest and total payment instantly.",
        "lead": "Work out your monthly loan payment, total interest and total cost in seconds. Works for home, car, personal and education loans.",
        "keywords": "emi loan home car personal interest monthly payment",
        "related": ["sip-calculator", "gst-calculator", "percentage-calculator"],
        "panels": lambda: calc_panel(
            "emi",
            num_field("amount", "Loan amount", 1000000, 50000, 20000000, 10000, prefix="₹", words=True)
            + num_field("rate", "Interest rate (per year)", 9, 1, 30, 0.1, suffix="%")
            + num_field("years", "Loan tenure", 5, 1, 30, 0.5, suffix="yrs")),
        "body": f"""
<h2>How the EMI calculator works</h2>
<p>An EMI (equated monthly instalment) is the fixed amount you pay your lender every month until the loan is cleared. Each payment covers some interest and some of the principal. Early on most of it is interest; towards the end most of it is principal.</p>
<p>The calculator uses the standard reducing-balance formula:</p>
<p class="formula-box">EMI = P × r × (1 + r)ⁿ ÷ [(1 + r)ⁿ − 1]</p>
<ul>
<li><strong>P</strong> is the loan amount (principal).</li>
<li><strong>r</strong> is the monthly interest rate: the yearly rate divided by 12, then by 100.</li>
<li><strong>n</strong> is the number of monthly instalments.</li>
</ul>
<h2>Example</h2>
<p>On a loan of ₹10,00,000 at 9% a year for 5 years, r is 0.0075 and n is 60. The EMI works out to about <strong>{inr(_emi)}</strong>. Over 60 months you would pay {inr(_emi * 60)} in total, of which {inr(_emi * 60 - 1000000)} is interest.</p>
<h2>Ways to lower your EMI</h2>
<ul>
<li>Choose a longer tenure. The EMI drops, but you pay more interest overall.</li>
<li>Make a larger down payment so you borrow less.</li>
<li>Compare rates from several lenders before you sign.</li>
<li>Prepay part of the loan when you have spare cash. This shortens the tenure or reduces the EMI.</li>
</ul>
<p class="notice">This calculator gives an estimate for a fixed-rate loan. Processing fees, insurance and rate changes on floating-rate loans are not included, so check the final figures with your lender.</p>
""",
        "faqs": [
            ("Is my EMI the same every month?", "On a fixed-rate loan, yes. On a floating-rate loan the lender can change the rate, which changes either your EMI or your tenure."),
            ("Does the calculator include processing fees?", "No. It only covers principal and interest. Processing fees, GST on fees and insurance are charged separately by the lender."),
            ("What is better, a shorter or a longer tenure?", "A shorter tenure means a higher EMI but much less interest. A longer tenure keeps the EMI small but costs more overall. Pick the shortest tenure whose EMI you can pay comfortably."),
        ],
    },
    {
        "slug": "sip-calculator", "name": "SIP Calculator", "glyph": "↗",
        "short": "Estimate mutual fund SIP returns, with step-up",
        "title": "SIP Calculator – Estimate Mutual Fund Returns with Step-Up",
        "desc": "Free SIP calculator. Enter your monthly investment, expected return and period to see the estimated maturity value. Includes an optional yearly step-up.",
        "lead": "See what a monthly SIP could grow to over time. Add a yearly step-up to model investing more as your income grows.",
        "keywords": "sip mutual fund investment returns step-up monthly invest",
        "related": ["emi-calculator", "percentage-calculator", "gst-calculator"],
        "panels": lambda: calc_panel(
            "sip",
            num_field("monthly", "Monthly investment", 5000, 500, 100000, 500, prefix="₹", words=True)
            + num_field("rate", "Expected return (per year)", 12, 1, 30, 0.5, suffix="%")
            + num_field("years", "Time period", 10, 1, 40, 1, suffix="yrs")
            + num_field("step", "Yearly step-up (optional)", 0, 0, 25, 1, suffix="%")),
        "body": f"""
<h2>How the SIP calculator works</h2>
<p>A SIP (systematic investment plan) invests a fixed amount in a mutual fund every month. Each instalment earns returns that are added back to the pot, so growth compounds over time.</p>
<p>The calculator assumes your money is invested at the start of every month and grows at a steady monthly rate (the yearly rate divided by 12). Without a step-up, the result matches the standard formula:</p>
<p class="formula-box">Future value = P × [((1 + i)ⁿ − 1) ÷ i] × (1 + i)</p>
<ul>
<li><strong>P</strong> is the monthly investment.</li>
<li><strong>i</strong> is the monthly rate of return.</li>
<li><strong>n</strong> is the number of months.</li>
</ul>
<h2>Example</h2>
<p>Investing ₹5,000 a month for 10 years at an assumed 12% a year puts in {inr(_sip_inv)} and grows to roughly <strong>{inr(_sip)}</strong>. Most of the gain comes in the later years, which is why staying invested for longer matters more than the exact return figure.</p>
<h2>What is a step-up SIP?</h2>
<p>A step-up SIP raises your monthly amount by a fixed percentage every year, for example 10%. If your income grows, a step-up can build a much larger corpus than a flat SIP, without you having to start big.</p>
<p class="notice">Mutual fund returns are not guaranteed and change with the market. The return rate here is an assumption, not a forecast. Taxes, expense ratios and exit loads are not included.</p>
""",
        "faqs": [
            ("What return rate should I enter?", "Use a conservative figure. Equity funds have historically varied a lot from year to year, so many people test 8%, 10% and 12% to see a range instead of one number."),
            ("Will my actual returns match this?", "Unlikely to match exactly. Real SIP returns depend on the NAV on each investment date and on fund charges, and they can be negative in some periods. Treat the result as a planning estimate."),
            ("How is the step-up applied?", "Your monthly amount stays the same for the first 12 months, then rises by the step-up percentage at the start of each following year."),
        ],
    },
    {
        "slug": "percentage-calculator", "name": "Percentage Calculator", "glyph": "%",
        "short": "Find a percentage, a share or a percentage change",
        "title": "Percentage Calculator – Find % of a Number, % Change & More",
        "desc": "Free percentage calculator. Find X% of a number, work out what percent one number is of another, or calculate the percentage increase or decrease.",
        "lead": "Three common percentage questions in one place. Type in the numbers and the answer updates as you go.",
        "keywords": "percentage percent % increase decrease change discount marks",
        "related": ["gst-calculator", "emi-calculator", "sip-calculator"],
        "panels": lambda: (
            mini_panel("pct-of", "Percentage of a number", "What is", "Percentage", 15, "of", "Number", 2400, a_suffix="%")
            + mini_panel("pct-is", "One number as a percentage of another", "", "First number", 45, "is what % of", "Second number", 60)
            + mini_panel("pct-change", "Percentage increase or decrease", "From", "Starting value", 200, "to", "New value", 250)),
        "body": """
<h2>The three formulas</h2>
<p>Percentage means "out of 100". These are the formulas behind the three calculators above.</p>
<p><strong>Percentage of a number</strong></p>
<p class="formula-box">Result = (percentage ÷ 100) × number</p>
<p>15% of 2,400 is 0.15 × 2,400 = 360.</p>
<p><strong>One number as a percentage of another</strong></p>
<p class="formula-box">Percentage = (part ÷ whole) × 100</p>
<p>45 out of 60 is 45 ÷ 60 × 100 = 75%.</p>
<p><strong>Percentage change</strong></p>
<p class="formula-box">Change = ((new − old) ÷ old) × 100</p>
<p>A price moving from 200 to 250 is a 25% increase. Going back from 250 to 200 is a 20% decrease. The two are not equal because the starting value differs.</p>
<h2>Where people use it</h2>
<ul>
<li>Working out a discount or the sale price of something</li>
<li>Checking exam marks as a percentage</li>
<li>Seeing how much a salary, price or investment has grown</li>
<li>Splitting a bill or calculating a tip</li>
</ul>
""",
        "faqs": [
            ("How do I calculate a discount?", "Use the first calculator to find the discount amount (discount % of the price), then subtract it from the price. A 20% discount on 1,500 saves 300, so you pay 1,200."),
            ("Why is a 25% increase not reversed by a 25% decrease?", "Because the second percentage applies to a bigger number. After going up 25% from 200 to 250, you need a 20% drop, not 25%, to get back to 200."),
            ("Can the result be more than 100%?", "Yes. If the part is larger than the whole, or a value more than doubles, the percentage goes past 100."),
        ],
    },
    {
        "slug": "age-calculator", "name": "Age Calculator", "glyph": "yr",
        "short": "Exact age in years, months and days",
        "title": "Age Calculator – Find Your Exact Age in Years, Months & Days",
        "desc": "Free age calculator. Enter a date of birth to get your exact age in years, months and days, plus total days lived and days to your next birthday.",
        "lead": "Enter a date of birth and get an exact age, down to the day. You can also change the 'Age on' date to find an age on any day.",
        "keywords": "age date of birth dob birthday years months days",
        "related": ["percentage-calculator", "emi-calculator", "sip-calculator"],
        "glyph_small": True,
        "panels": lambda: calc_panel(
            "age",
            date_field("dob", "Date of birth", "2000-01-01") + date_field("on", "Age on (today by default)")),
        "body": """
<h2>How age is calculated</h2>
<p>The calculator counts full years first, then the remaining full months, then the leftover days, the same way you would count on a calendar. If your birthday has not come around yet this year, the year count stays one lower until it does.</p>
<h2>Handy uses</h2>
<ul>
<li>Checking age eligibility for an exam, job or form as of a cut-off date. Change the "Age on" date to that cut-off.</li>
<li>Finding out how many days or weeks old someone is.</li>
<li>Seeing how many days are left until the next birthday.</li>
</ul>
<h2>Leap-day birthdays</h2>
<p>If you were born on 29 February, your birthday in non-leap years is counted on 1 March in this calculator. Rules for legal purposes can differ, so check the official rule if it matters.</p>
""",
        "faqs": [
            ("Can I find my age on a past or future date?", "Yes. Change the 'Age on' date. It defaults to today, but any date works as long as it is after the date of birth."),
            ("Is my date of birth stored anywhere?", "No. The calculation runs in your browser and nothing is sent to a server."),
            ("How is 'total months' counted?", "It is the number of complete months since the date of birth, not counting the extra days."),
        ],
    },
    {
        "slug": "gst-calculator", "name": "GST Calculator", "glyph": "GST",
        "short": "Add or remove GST, with CGST and SGST split",
        "title": "GST Calculator – Add or Remove GST Online (India)",
        "desc": "Free GST calculator for India. Add GST to a price or remove it from a GST-inclusive amount. Shows CGST, SGST and the total.",
        "lead": "Add GST to a price, or take it out of a GST-inclusive amount. The result shows the CGST and SGST split too.",
        "keywords": "gst tax india cgst sgst igst invoice inclusive exclusive",
        "related": ["percentage-calculator", "emi-calculator", "sip-calculator"],
        "glyph_small": True,
        "panels": lambda: calc_panel(
            "gst",
            seg_field("mode", "What do you want to do?", [("add", "Add GST"), ("remove", "Remove GST")], "add")
            + num_field("amount", "Amount", 1000, 0, 0, 1, prefix="₹", slider=False, words=True)
            + num_field("rate", "GST rate", 18, 0, 0, 0.5, suffix="%", slider=False, presets=[3, 5, 18, 40])),
        "body": """
<h2>The formulas</h2>
<p><strong>To add GST</strong> to a price:</p>
<p class="formula-box">GST = price × rate ÷ 100<br>Total = price + GST</p>
<p><strong>To remove GST</strong> from a GST-inclusive amount:</p>
<p class="formula-box">Price before GST = total ÷ (1 + rate ÷ 100)<br>GST = total − price before GST</p>
<p>Removing GST is not the same as subtracting the rate from the total. For example, ₹1,180 with 18% GST included is ₹1,000 plus ₹180 of tax, not ₹1,180 − 18% = ₹967.60.</p>
<h2>CGST, SGST and IGST</h2>
<p>When a sale happens within one state, the GST is split equally between the Central government (CGST) and the State government (SGST). When goods or services move between states, the full amount is charged as IGST. The total tax is the same either way, so the "Total GST" line applies to both cases.</p>
<p class="notice">GST rates and slabs are revised from time to time and different goods and services fall under different rates. The preset buttons are common rates. Always confirm the rate for your item on the official GST portal or with your accountant.</p>
""",
        "faqs": [
            ("How do I find the GST-exclusive price?", "Choose 'Remove GST', enter the amount that already includes GST, and pick the rate. The calculator divides by (1 + rate) to give the price before tax."),
            ("What is the difference between CGST and SGST?", "They are the two halves of GST on a sale within the same state. At 18% GST, 9% goes to the Centre as CGST and 9% to the state as SGST."),
            ("Can I enter a rate that is not in the buttons?", "Yes. Type any rate in the box, for example 0.25 or 12, and the result updates."),
        ],
    },
]

CONVERTERS = [
    {
        "slug": "km-to-miles", "name": "Kilometres to Miles", "glyph": "km", "cat": "length", "from": "km", "to": "mi",
        "short": "Convert km to miles and back",
        "title": "Km to Miles Converter – Convert Kilometres to Miles",
        "desc": "Convert kilometres to miles instantly. 1 km = 0.621371 miles. Free converter with a swap button, formula and quick reference table.",
        "lead": "Type a distance in kilometres to see it in miles. Hit the swap button to go the other way.",
        "keywords": "km kilometres kilometers miles distance length",
        "related": ["cm-to-inches", "kg-to-lbs", "celsius-to-fahrenheit"],
        "table": [1, 2, 5, 10, 20, 25, 50, 100, 500],
        "body": f"""
<h2>How to convert kilometres to miles</h2>
<p>Multiply the number of kilometres by 0.621371, or divide it by 1.609344.</p>
<p class="formula-box">miles = kilometres × 0.621371</p>
<p>For example, a marathon is 42.195 km, which is {fmt(convert("length", "km", "mi", 42.195), 3)} miles.</p>
<p><strong>Mental shortcut:</strong> multiply by 0.6 for a quick estimate. 50 km × 0.6 = 30 miles, close to the exact 31.07.</p>
<h2>Km to miles reference table</h2>
""",
        "after_table": "<p>To convert miles to kilometres, use the swap button, or multiply the miles by 1.609344.</p>",
        "faqs": [
            ("How many miles are in 1 kilometre?", "1 km is 0.621371 miles."),
            ("How many kilometres are in a mile?", "1 mile is exactly 1.609344 km."),
            ("Does this work for km/h to mph?", "Yes. Speed uses the same factor, so 100 km/h is about 62.14 mph."),
        ],
    },
    {
        "slug": "kg-to-lbs", "name": "Kilograms to Pounds", "glyph": "kg", "cat": "weight", "from": "kg", "to": "lb",
        "short": "Convert kg to lbs and back",
        "title": "Kg to Lbs Converter – Convert Kilograms to Pounds",
        "desc": "Convert kilograms to pounds instantly. 1 kg = 2.20462 lbs. Free converter with a swap button, formula and quick reference table.",
        "lead": "Enter a weight in kilograms to see it in pounds. Use the swap button to convert pounds back to kilograms.",
        "keywords": "kg kilograms kilogram pounds lbs lb weight",
        "related": ["km-to-miles", "cm-to-inches", "celsius-to-fahrenheit"],
        "table": [1, 2, 5, 10, 25, 50, 60, 70, 80, 100],
        "body": f"""
<h2>How to convert kg to lbs</h2>
<p>Multiply the weight in kilograms by 2.20462.</p>
<p class="formula-box">pounds = kilograms × 2.20462</p>
<p>For example, 70 kg is {fmt(convert("weight", "kg", "lb", 70), 2)} lbs.</p>
<p><strong>Mental shortcut:</strong> double the kilograms, then add 10% of that. For 50 kg: 100 + 10 = 110 lbs (exact: 110.23).</p>
<h2>Kg to lbs reference table</h2>
""",
        "after_table": "<p>To go from pounds to kilograms, use the swap button, or divide the pounds by 2.20462.</p>",
        "faqs": [
            ("How many pounds are in 1 kg?", "1 kg is about 2.20462 pounds."),
            ("Why is pounds written as lb?", "The abbreviation comes from the Latin word libra. 'lbs' is the plural form commonly used in writing."),
            ("How do I convert pounds to kg?", "Divide by 2.20462, or multiply by 0.453592. Use the swap button to do it automatically."),
        ],
    },
    {
        "slug": "cm-to-inches", "name": "Centimetres to Inches", "glyph": "cm", "cat": "length", "from": "cm", "to": "in",
        "short": "Convert cm to inches and back",
        "title": "Cm to Inches Converter – Convert Centimetres to Inches",
        "desc": "Convert centimetres to inches instantly. 1 inch = 2.54 cm. Free converter with a swap button, formula and quick reference table.",
        "lead": "Enter a length in centimetres to see it in inches. Handy for heights, screen sizes and clothing.",
        "keywords": "cm centimetres centimeters inches inch height length",
        "related": ["km-to-miles", "kg-to-lbs", "celsius-to-fahrenheit"],
        "table": [1, 5, 10, 25, 50, 100, 150, 160, 170, 180],
        "body": f"""
<h2>How to convert cm to inches</h2>
<p>Divide the number of centimetres by 2.54. One inch is defined as exactly 2.54 cm.</p>
<p class="formula-box">inches = centimetres ÷ 2.54</p>
<p>For example, a height of 170 cm is {fmt(convert("length", "cm", "in", 170), 2)} inches, which is 5 feet 6.9 inches, or about 5 ft 7 in.</p>
<h2>Converting height to feet and inches</h2>
<p>Divide the inches by 12 to get whole feet. The remainder is the extra inches. So 66.93 inches is 5 feet (60 inches) plus 6.93 inches.</p>
<h2>Cm to inches reference table</h2>
""",
        "after_table": "<p>To convert inches to centimetres, use the swap button, or multiply the inches by 2.54.</p>",
        "faqs": [
            ("How many cm are in an inch?", "Exactly 2.54 cm."),
            ("How many inches are in 100 cm?", "100 cm is 39.3701 inches, a little over 3 feet 3 inches."),
            ("Is there a faster way to estimate?", "Multiply centimetres by 0.4. For 50 cm, 50 × 0.4 = 20 inches, near the exact 19.69."),
        ],
    },
    {
        "slug": "celsius-to-fahrenheit", "name": "Celsius to Fahrenheit", "glyph": "°C", "cat": "temperature", "from": "c", "to": "f",
        "short": "Convert °C to °F and back",
        "title": "Celsius to Fahrenheit Converter – Convert °C to °F",
        "desc": "Convert Celsius to Fahrenheit instantly. Formula: °F = °C × 9/5 + 32. Free converter with a swap button and quick reference table.",
        "lead": "Enter a temperature in Celsius to see it in Fahrenheit. Swap the units, or pick Kelvin, to convert the other way.",
        "keywords": "celsius fahrenheit kelvin temperature degrees c f weather",
        "related": ["km-to-miles", "kg-to-lbs", "cm-to-inches"],
        "table": [-40, 0, 10, 20, 25, 30, 37, 100],
        "body": f"""
<h2>How to convert Celsius to Fahrenheit</h2>
<p>Multiply the Celsius temperature by 9/5 (1.8), then add 32.</p>
<p class="formula-box">°F = °C × 9/5 + 32</p>
<p>For example, normal body temperature of 37°C is {fmt(convert("temperature", "c", "f", 37), 1)}°F, and the boiling point of water, 100°C, is 212°F.</p>
<p><strong>Mental shortcut:</strong> double the Celsius value and add 30. For 20°C: 40 + 30 = 70°F (exact: 68°F). It gets less accurate at extreme temperatures.</p>
<h2>Celsius to Fahrenheit reference table</h2>
""",
        "after_table": "<p>To go from Fahrenheit to Celsius, use the swap button, or subtract 32 and multiply by 5/9.</p>",
        "faqs": [
            ("At what temperature are Celsius and Fahrenheit equal?", "At −40. That is the only point where both scales show the same number."),
            ("What is room temperature in Fahrenheit?", "Around 20 to 25°C, which is 68 to 77°F."),
            ("How do I convert Fahrenheit to Celsius?", "Subtract 32, then multiply by 5/9. For 98.6°F: (98.6 − 32) × 5/9 = 37°C."),
        ],
    },
]

MARKET = {"emi-calculator": "in", "sip-calculator": "in", "gst-calculator": "in",
          "percentage-calculator": "gen", "age-calculator": "gen"}
for t in CALCULATORS:
    t["market"] = MARKET[t["slug"]]
US_CALCULATORS = get_us_calculators(num_field, seg_field, calc_panel)
for t in US_CALCULATORS:
    t["market"] = "us"
CALCULATORS = US_CALCULATORS + CALCULATORS

ALL_TOOLS = CALCULATORS + CONVERTERS
for t in CALCULATORS:
    t["kind"] = "calc"
for t in CONVERTERS:
    t["kind"] = "conv"
BY_SLUG = {t["slug"]: t for t in ALL_TOOLS}

MARKETS = [("us", "US finance calculators", "Loans, savings and take-home pay"),
           ("in", "India finance calculators", "EMI, SIP and GST"),
           ("gen", "Everyday calculators", "Percentages and dates")]


def by_market(m):
    return [t for t in CALCULATORS if t["market"] == m]

# ----------------------------------------------------------------------------
# Page shell
# ----------------------------------------------------------------------------
def url(path):
    return SITE_URL + path


def glyph_html(t, small=False):
    cls = "glyph" + (" conv-glyph" if t["kind"] == "conv" else "")
    if len(t["glyph"]) >= 2 and t["glyph"] not in ("°C",):
        cls += " small"
    return f'<span class="{cls}" aria-hidden="true">{esc(t["glyph"])}</span>'


def head(title, desc, path, schema=None, noindex=False):
    s = ""
    for block in schema or []:
        s += f'<script type="application/ld+json">{json.dumps(block, ensure_ascii=False)}</script>\n'
    robots = '<meta name="robots" content="noindex">\n' if noindex else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{robots}<link rel="canonical" href="{url(path)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url(path)}">
<meta name="theme-color" content="#0e1a30">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="preload" href="/assets/fonts/bricolage-grotesque-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/style.css">
<!-- ADSENSE: after approval, paste your AdSense <script> tag here, and add class="ads" to the <html> tag. -->
{s}</head>
"""


def header(section=""):
    def cur(name):
        return ' aria-current="page"' if section == name else ""
    return f"""<body>
<header class="site-header">
<div class="wrap">
<a class="logo" href="/"><span class="logo-mark" aria-hidden="true"><i></i><i></i></span>{SITE_NAME}</a>
<nav class="nav" aria-label="Main">
<a href="/calculators/"{cur("calculators")}>Calculators</a>
<a href="/converters/"{cur("converters")}>Converters</a>
</nav>
</div>
</header>
"""


def footer(scripts=""):
    def links(ts):
        return "".join(f'<li><a href="/{t["slug"]}/">{esc(t["name"])}</a></li>' for t in ts)
    us_links = links(by_market("us"))
    in_links = links(by_market("in"))
    ev_links = links(by_market("gen") + CONVERTERS)
    return f"""<footer class="site-footer">
<div class="wrap">
<div class="footer-grid">
<div><h2>{SITE_NAME}</h2><p>{TAGLINE}. Everything runs in your browser, so what you type stays on your device.</p></div>
<div><h2>US finance</h2><ul>{us_links}</ul></div>
<div><h2>India finance</h2><ul>{in_links}</ul></div>
<div><h2>Everyday tools</h2><ul>{ev_links}</ul></div>
<div><h2>Company</h2><ul>
<li><a href="/about/">About</a></li>
<li><a href="/contact/">Contact</a></li>
<li><a href="/privacy-policy/">Privacy Policy</a></li>
<li><a href="/terms/">Terms of Use</a></li>
</ul></div>
</div>
<p class="footer-note">© {date.today().year} {SITE_NAME}. Results are estimates for general guidance and are not financial, tax or legal advice.</p>
</div>
</footer>
{scripts}</body>
</html>
"""


def tile(t):
    return (f'<li data-k="{esc(t["name"].lower() + " " + t["keywords"])}"><a class="tile" href="/{t["slug"]}/">'
            f'{glyph_html(t)}<span><strong>{esc(t["name"])}</strong><span class="d">{esc(t["short"])}</span></span></a></li>')


def ad(kind):
    return f'<div class="ad ad-{kind}" aria-label="Advertisement"><!-- ad unit: {kind} --></div>'


# ----------------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------------
def page_home():
    us_tiles = "".join(tile(t) for t in by_market("us"))
    in_tiles = "".join(tile(t) for t in by_market("in"))
    ev_tiles = "".join(tile(t) for t in by_market("gen") + CONVERTERS)
    schema = [{"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/"}]
    title = f"{SITE_NAME} – Free Online Calculators & Unit Converters"
    desc = "Free online calculators: mortgage, auto loan, compound interest, retirement, credit card payoff and take-home pay, plus EMI, SIP, GST and unit converters. Fast, private and works on any phone."
    body = f"""<main>
<section class="hero">
<div class="wrap hero-grid">
<div>
<h1>Calculate it. Convert it. Done.</h1>
<p class="lead">Mortgage, auto loan, retirement and take-home pay calculators, plus everyday unit converters. Free, instant and nothing to sign up for.</p>
<div class="search" role="search">
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
<label class="sr-only" for="tool-search">Search tools</label>
<input id="tool-search" type="search" placeholder="Search tools, e.g. mortgage or km to miles" autocomplete="off">
</div>
<div class="quick"><a href="/mortgage-calculator/">Mortgage</a><a href="/auto-loan-calculator/">Auto loan</a><a href="/take-home-pay-calculator/">Take-home pay</a><a href="/retirement-calculator/">Retirement</a><a href="/km-to-miles/">km to miles</a></div>
</div>
{conv_form("length", "km", "mi", 10, hero=True)}
</div>
</section>
<div class="wrap">
<section class="section" data-section="us" aria-labelledby="h-us">
<div class="section-head"><h2 id="h-us">US finance calculators</h2><p>Loans, savings and take-home pay</p></div>
<ul class="tiles">{us_tiles}</ul>
</section>
<section class="section" data-section="in" aria-labelledby="h-in">
<div class="section-head"><h2 id="h-in">India finance calculators</h2><p>EMI, SIP and GST</p></div>
<ul class="tiles">{in_tiles}</ul>
</section>
<section class="section" data-section="ev" aria-labelledby="h-ev">
<div class="section-head"><h2 id="h-ev">Everyday tools</h2><p>Percentages, age and unit converters</p></div>
<ul class="tiles">{ev_tiles}</ul>
</section>
<p class="no-results">No tool matches that search yet. Try a shorter word such as "loan" or "weight".</p>
<section class="points">
<div><h3>Runs on your device</h3><p>Every calculation happens in your browser. The numbers you enter are never uploaded.</p></div>
<div><h3>No signup, no clutter</h3><p>Open a tool, type your numbers and read the answer. No accounts and no pop-ups in the way.</p></div>
<div><h3>Built for phones</h3><p>Large inputs, sliders you can drag with a thumb and pages that load quickly on a slow connection.</p></div>
</section>
</div>
</main>
"""
    scripts = '<script src="/assets/units.js"></script>\n<script src="/assets/app.js" defer></script>\n'
    return head(title, desc, "/", schema) + header() + body + footer(scripts)


def page_category(kind):
    tools = CALCULATORS if kind == "calc" else CONVERTERS
    name = "Calculators" if kind == "calc" else "Converters"
    path = "/calculators/" if kind == "calc" else "/converters/"
    intro = ("Free calculators for loans, investments, tax, dates and percentages. Pick one to get started."
             if kind == "calc" else
             "Quick unit converters for length, weight and temperature, each with the formula and a reference table.")
    title = f"Free Online {name} | {SITE_NAME}"
    desc = intro
    if kind == "calc":
        listing = "".join(
            f'<section class="group"><h2>{h}</h2><p>{d}</p><ul class="tiles">{"".join(tile(t) for t in by_market(m))}</ul></section>'
            for m, h, d in MARKETS)
    else:
        listing = f'<ul class="tiles" style="margin-top:28px">{"".join(tile(t) for t in tools)}</ul>'
    schema = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
        {"@type": "ListItem", "position": 2, "name": name, "item": url(path)}]}]
    body = f"""<main class="wrap cat-list">
<nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a> / {name}</nav>
<h1 style="margin:8px 0 12px">{name}</h1>
<p>{intro}</p>
{listing}
{ad("top")}
</main>
"""
    return head(title, desc, path, schema) + header(name.lower()) + body + footer()


def page_tool(t):
    is_conv = t["kind"] == "conv"
    section = "Converters" if is_conv else "Calculators"
    section_path = "/converters/" if is_conv else "/calculators/"
    path = f'/{t["slug"]}/'

    if is_conv:
        panel = conv_form(t["cat"], t["from"], t["to"], 1)
        content = t["body"] + ref_table(t["cat"], t["from"], t["to"], t["table"]) + t.get("after_table", "")
    else:
        panel = t["panels"]()
        content = t["body"]

    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in t["faqs"])

    related = "".join(
        f'<li><a href="/{r}/">{glyph_html(BY_SLUG[r])}<span>{esc(BY_SLUG[r]["name"])}</span></a></li>' for r in t["related"])

    schema = [
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in t["faqs"]]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": section, "item": url(section_path)},
            {"@type": "ListItem", "position": 3, "name": t["name"], "item": url(path)}]},
        {"@context": "https://schema.org", "@type": "WebApplication", "name": t["name"], "url": url(path),
         "applicationCategory": "UtilitiesApplication", "operatingSystem": "Any",
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD" if t.get("market") == "us" else "INR"}},
    ]

    body = f"""<main class="wrap">
<nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a> / <a href="{section_path}">{section}</a> / {esc(t["name"])}</nav>
<div class="tool-layout">
<article>
<header class="tool-head">
<span class="badge{" conv" if is_conv else ""}">{"Converter" if is_conv else "Calculator"}</span>
<h1>{esc(t["name"] if is_conv else t["name"])}</h1>
<p class="lead">{esc(t["lead"])}</p>
</header>
{ad("top")}
{panel}
{ad("mid")}
<section class="prose">
{content}
</section>
<section class="prose faq" style="margin-top:20px" aria-labelledby="faq-h">
<h2 id="faq-h">Frequently asked questions</h2>
{faq_html}
</section>
</article>
<aside class="side">
<div class="side-box"><h2>More tools</h2><ul>{related}</ul></div>
{ad("side")}
</aside>
</div>
</main>
"""
    scripts = '<script src="/assets/units.js"></script>\n<script src="/assets/app.js" defer></script>\n'
    return head(t["title"], t["desc"], path, schema) + header(section.lower()) + body + footer(scripts)


def simple_page(title, desc, path, inner, noindex=False):
    body = f'<main class="wrap"><div class="page">{inner}</div></main>\n'
    return head(f"{title} | {SITE_NAME}", desc, path, noindex=noindex) + header() + body + footer()


def page_about():
    return simple_page("About", f"About {SITE_NAME}, a set of free, fast calculators and converters.", "/about/", f"""
<h1>About {SITE_NAME}</h1>
<p>{SITE_NAME} is a collection of free online calculators and unit converters. The aim is simple: give you a quick, correct answer without sign-ups, pop-ups or a cluttered page.</p>
<h2>How it works</h2>
<p>Every tool runs in your web browser. The numbers you type are processed on your own device and are not sent to our servers.</p>
<h2>How we keep results accurate</h2>
<p>Each tool uses a standard, published formula, and the page explains that formula with a worked example so you can check the answer yourself. If you ever spot a result that looks wrong, please <a href="/contact/">tell us</a> and we will look into it.</p>
<h2>How the site is funded</h2>
<p>The site is supported by advertising, which lets us keep every tool free. Ads are kept away from the calculators so they do not get in your way.</p>
<p>Results are estimates for general guidance. They are not financial, tax or legal advice.</p>
""")


def page_contact():
    return simple_page("Contact", f"Contact {SITE_NAME} with questions, corrections or tool suggestions.", "/contact/", f"""
<h1>Contact us</h1>
<p>Found a mistake, want a tool added, or have a question? Send us an email at <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>.</p>
<p>When you report a problem with a result, please include the tool name and the numbers you entered. It helps us reproduce it quickly.</p>
<p>We read every message, though replies can take a few days.</p>
""")


def page_privacy():
    return simple_page("Privacy Policy", f"How {SITE_NAME} handles your data, cookies and advertising.", "/privacy-policy/", f"""
<h1>Privacy Policy</h1>
<p><em>Last updated: {date.today().strftime("%d %B %Y")}</em></p>
<p>This policy explains what information {SITE_NAME} ("we", "us") collects when you use {SITE_URL.replace("https://", "")} and how it is used.</p>
<h2>What you enter in the tools</h2>
<p>The calculators and converters run entirely in your browser. The numbers and dates you enter are not uploaded to or stored on our servers.</p>
<h2>Information collected automatically</h2>
<p>Like most websites, our hosting provider and analytics tools may record standard technical data such as your IP address, browser type, device type, pages visited and the time of your visit. We use this to keep the site running, understand which tools are useful and improve them.</p>
<h2>Cookies and advertising</h2>
<p>We may show ads served by Google AdSense or other advertising partners. Third-party vendors, including Google, use cookies to serve ads based on your prior visits to this and other websites. Google's use of advertising cookies enables it and its partners to serve ads to you based on your visit to our site and other sites on the internet.</p>
<p>You can opt out of personalised advertising by visiting <a href="https://www.google.com/settings/ads" rel="noopener">Google Ads Settings</a>. You can also manage or delete cookies through your browser settings.</p>
<h2>Third-party links</h2>
<p>Our pages may link to other websites. We are not responsible for the content or privacy practices of those sites.</p>
<h2>Children</h2>
<p>This site is a general-audience utility and is not directed at children under 13. We do not knowingly collect personal information from children.</p>
<h2>Changes to this policy</h2>
<p>We may update this policy from time to time. The date at the top shows when it was last changed.</p>
<h2>Contact</h2>
<p>Questions about this policy? Email <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>.</p>
""")


def page_terms():
    return simple_page("Terms of Use", f"Terms of use for {SITE_NAME}.", "/terms/", f"""
<h1>Terms of Use</h1>
<p><em>Last updated: {date.today().strftime("%d %B %Y")}</em></p>
<p>By using {SITE_NAME} you agree to these terms.</p>
<h2>Use of the tools</h2>
<p>The calculators and converters are provided free of charge for personal and informational use. You may not misuse the site, attempt to disrupt it, or copy it in bulk.</p>
<h2>No professional advice</h2>
<p>Results are estimates based on the numbers you enter and standard formulas. They are for general guidance only and are not financial, investment, tax, legal or medical advice. Actual loan, investment and tax outcomes depend on factors the tools cannot know. Please check important figures with your lender, adviser or the relevant authority before acting on them.</p>
<h2>No warranty</h2>
<p>We work to keep the tools accurate, but we provide them "as is" without warranties of any kind. We are not liable for any loss arising from the use of, or inability to use, the site or its results.</p>
<h2>Intellectual property</h2>
<p>The design, text and code of this site belong to {SITE_NAME}. You may link to any page freely.</p>
<h2>Changes</h2>
<p>We may change these terms or the site at any time. Continued use means you accept the updated terms.</p>
<h2>Contact</h2>
<p>Email <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> with any questions.</p>
""")


def page_404():
    return simple_page("Page not found", "The page you were looking for could not be found.", "/404.html", """
<h1>Page not found</h1>
<p>That page does not exist or has moved. Try the <a href="/">home page</a>, or browse the <a href="/calculators/">calculators</a> and <a href="/converters/">converters</a>.</p>
""", noindex=True)


# ----------------------------------------------------------------------------
# Build
# ----------------------------------------------------------------------------
def write(rel, content):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(SRC / "assets", OUT / "assets")

    units_js = ("window.UNITS=" + json.dumps(UNITS, ensure_ascii=False, separators=(",", ":")) + ";\n"
                "window.TAX2026=" + json.dumps(TAX2026, separators=(",", ":")) + ";")
    write("assets/units.js", units_js)
    write("assets/favicon.svg",
          '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="9" fill="#0e1a30"/>'
          '<rect x="8" y="10" width="16" height="3.5" rx="1.75" fill="#ffc83d"/><rect x="8" y="18.5" width="16" height="3.5" rx="1.75" fill="#ffc83d"/></svg>')

    write("index.html", page_home())
    write("calculators/index.html", page_category("calc"))
    write("converters/index.html", page_category("conv"))
    for t in ALL_TOOLS:
        write(f'{t["slug"]}/index.html', page_tool(t))
    write("about/index.html", page_about())
    write("contact/index.html", page_contact())
    write("privacy-policy/index.html", page_privacy())
    write("terms/index.html", page_terms())
    write("404.html", page_404())

    urls = ["/", "/calculators/", "/converters/"] + [f'/{t["slug"]}/' for t in ALL_TOOLS] + [
        "/about/", "/contact/", "/privacy-policy/", "/terms/"]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append(f"<url><loc>{url(u)}</loc><lastmod>{TODAY}</lastmod></url>")
    sm.append("</urlset>")
    write("sitemap.xml", "\n".join(sm))
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")

    print(f"Built {len(urls)} pages into {OUT}")


if __name__ == "__main__":
    main()
