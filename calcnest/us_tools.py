"""
US finance calculators for MoneyMath. Imported by build.py.

The browser maths lives in src/assets/app.js (CALCS). The Python below mirrors it
only to put correct worked examples into the page text.

Tax figures are for tax year 2026 (IRS inflation adjustments, Rev. Proc. 2025-32;
Social Security wage base from SSA). Update TAX2026 each autumn when the IRS
publishes the next year's numbers.
"""

# ----------------------------------------------------------------------------
# Tax data (also written to assets/units.js for the browser)
# ----------------------------------------------------------------------------
TAX2026 = {
    "single": {
        "std": 16100,
        "medThreshold": 200000,
        "brackets": [[0, 0.10], [12400, 0.12], [50400, 0.22], [105700, 0.24],
                     [201775, 0.32], [256225, 0.35], [640600, 0.37]],
    },
    "married": {
        "std": 32200,
        "medThreshold": 250000,
        "brackets": [[0, 0.10], [24800, 0.12], [100800, 0.22], [211400, 0.24],
                     [403550, 0.32], [512450, 0.35], [768700, 0.37]],
    },
    "ssBase": 184500,
    "ssRate": 0.062,
    "medRate": 0.0145,
    "addMed": 0.009,
}


# ----------------------------------------------------------------------------
# Small maths helpers (mirror app.js, used for worked examples in the text)
# ----------------------------------------------------------------------------
def usd0(n):
    return "${:,.0f}".format(n)


def usd2(n):
    return "${:,.2f}".format(n)


def pmt(principal, annual_pct, n):
    i = annual_pct / 1200
    return principal / n if i == 0 else principal * i * (1 + i) ** n / ((1 + i) ** n - 1)


def amortize(principal, annual_pct, n, extra=0.0):
    i = annual_pct / 1200
    pay = pmt(principal, annual_pct, n)
    bal, interest, m = principal, 0.0, 0
    while m < n and bal > 0.005:
        it = bal * i
        bal -= min(bal, pay + extra - it)
        interest += it
        m += 1
    return m, interest


def years_months(m):
    y, mo = divmod(m, 12)
    parts = []
    if y:
        parts.append(f"{y} year{'s' if y != 1 else ''}")
    if mo or not y:
        parts.append(f"{mo} month{'s' if mo != 1 else ''}")
    return ", ".join(parts)


def bracket_tax(income, brackets):
    tax = 0.0
    for k, (lo, rate) in enumerate(brackets):
        hi = brackets[k + 1][0] if k + 1 < len(brackets) else float("inf")
        if income > lo:
            tax += (min(income, hi) - lo) * rate
    return tax


def take_home(gross, status="single", k401=0.0, state_pct=0.0):
    fs = TAX2026[status]
    taxable = max(0.0, gross - k401 - fs["std"])
    fed = bracket_tax(taxable, fs["brackets"])
    ss = min(gross, TAX2026["ssBase"]) * TAX2026["ssRate"]
    med = gross * TAX2026["medRate"] + max(0.0, gross - fs["medThreshold"]) * TAX2026["addMed"]
    state = max(0.0, gross - k401) * state_pct / 100
    net = gross - k401 - fed - ss - med - state
    return {"taxable": taxable, "fed": fed, "ss": ss, "med": med, "state": state, "net": net}


def card_payoff(balance, apr, payment):
    r, bal, interest, m = apr / 1200, balance, 0.0, 0
    while bal > 0.005 and m < 1200:
        it = bal * r
        interest += it
        bal = bal + it - payment
        m += 1
    return m, interest


def bracket_table(status):
    b = TAX2026[status]["brackets"]
    rows = ""
    for k, (lo, rate) in enumerate(b):
        hi = b[k + 1][0] if k + 1 < len(b) else None
        span = f"{usd0(lo)} to {usd0(hi)}" if hi else f"Over {usd0(lo)}"
        rows += f"<tr><td>{int(round(rate * 100))}%</td><td>{span}</td></tr>"
    return ('<div class="table-scroll"><table class="ref"><thead><tr><th>Rate</th><th>Taxable income</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div>")


# ----------------------------------------------------------------------------
# Worked examples (they match the default values on each page)
# ----------------------------------------------------------------------------
# Mortgage: $400,000 home, 20% down, 6.5%, 30 years, 1% property tax, $1,800 insurance
M_PRICE, M_DOWN, M_RATE, M_YEARS = 400000, 20, 6.5, 30
M_LOAN = M_PRICE * (1 - M_DOWN / 100)
M_PI = pmt(M_LOAN, M_RATE, M_YEARS * 12)
M_TAX = M_PRICE * 0.01 / 12
M_INS = 1800 / 12
M_TOTAL = M_PI + M_TAX + M_INS
_, M_INT = amortize(M_LOAN, M_RATE, M_YEARS * 12, 0)
M_FAST_MONTHS, M_FAST_INT = amortize(M_LOAN, M_RATE, M_YEARS * 12, 200)

# Auto loan: $35,000 car, $3,000 down, 6% tax, 7% APR, 60 months
A_PRICE, A_DOWN, A_TAX, A_RATE, A_N = 35000, 3000, 0.06, 7, 60
A_TAXAMT = A_PRICE * A_TAX
A_LOAN = A_PRICE + A_TAXAMT - A_DOWN
A_PAY = pmt(A_LOAN, A_RATE, A_N)
A_INT = A_PAY * A_N - A_LOAN

# Compound interest: $10,000 start, $500/month, 7%, 20 years, monthly
def _compound(p, c, rate, years, freq):
    g = (1 + rate / 100 / freq) ** (freq / 12)
    bal = p
    for _ in range(round(years * 12)):
        bal = bal * g + c
    return bal


C_BAL = _compound(10000, 500, 7, 20, 12)
C_PUT = 500 * 240
C_INT = C_BAL - 10000 - C_PUT

# Retirement: 35 -> 67, $50,000 saved, $700 + $300 employer a month, 7%, 2.5% inflation
def _retire(age, ret, saved, mo, er, rate, infl):
    months = round((ret - age) * 12)
    g = (1 + rate / 100) ** (1 / 12)
    bal = saved
    for _ in range(months):
        bal = bal * g + mo + er
    return bal, bal / (1 + infl / 100) ** (months / 12)


R_BAL, R_REAL = _retire(35, 67, 50000, 700, 300, 7, 2.5)

# Credit card: $5,000 at 22% APR, $200 a month
K_MONTHS, K_INT = card_payoff(5000, 22, 200)
K_MONTHS_B, K_INT_B = card_payoff(5000, 22, 250)

# Take-home: $75,000 single, 5% state tax
T = take_home(75000, "single", 0, 5)


def get_us_calculators(num_field, seg_field, calc_panel):
    return [
        # ------------------------------------------------------------------ mortgage
        {
            "slug": "mortgage-calculator", "name": "Mortgage Calculator", "glyph": "home",
            "short": "Monthly payment with taxes, insurance and PMI",
            "title": "Mortgage Calculator – Monthly Payment with Taxes, Insurance & PMI",
            "desc": "Free mortgage calculator. Enter home price, down payment, rate and term to see your monthly payment including property tax, insurance and PMI, plus the effect of extra payments.",
            "lead": "See your full monthly payment, not just principal and interest. Add property tax, insurance, PMI and HOA dues, then test how extra payments shorten the loan.",
            "keywords": "mortgage home loan payment house piti pmi property tax down payment extra payments",
            "related": ["auto-loan-calculator", "take-home-pay-calculator", "compound-interest-calculator"],
            "panels": lambda: calc_panel(
                "mortgage",
                num_field("price", "Home price", 400000, 50000, 2000000, 5000, prefix="$")
                + num_field("down", "Down payment", 20, 0, 60, 1, suffix="%", presets=[5, 10, 20], of="price")
                + num_field("rate", "Interest rate", 6.5, 2, 12, 0.125, suffix="%")
                + seg_field("years", "Loan term", [("30", "30 years"), ("20", "20 years"), ("15", "15 years"), ("10", "10 years")], "30")
                + num_field("tax", "Property tax (per year)", 1, 0, 0, 0.1, suffix="%", slider=False)
                + num_field("ins", "Home insurance (per year)", 1800, 0, 0, 50, prefix="$", slider=False)
                + num_field("hoa", "HOA dues (per month)", 0, 0, 0, 10, prefix="$", slider=False)
                + num_field("pmi", "PMI rate (if under 20% down)", 0.5, 0, 0, 0.1, suffix="%", slider=False)
                + num_field("extra", "Extra payment (per month)", 0, 0, 0, 50, prefix="$", slider=False)),
            "body": f"""
<h2>How the mortgage calculator works</h2>
<p>Your monthly mortgage payment has two parts. The first is principal and interest, which pays down the loan. The second is the cost of owning the home that most lenders collect with each payment: property tax, homeowners insurance and, when your down payment is small, mortgage insurance. Lenders call the total PITI, short for principal, interest, taxes and insurance.</p>
<p>Principal and interest use the standard loan formula:</p>
<p class="formula-box">Payment = L × r × (1 + r)ⁿ ÷ [(1 + r)ⁿ − 1]</p>
<ul>
<li><strong>L</strong> is the loan amount: the home price minus your down payment.</li>
<li><strong>r</strong> is the monthly interest rate, which is the yearly rate divided by 12.</li>
<li><strong>n</strong> is the number of monthly payments, such as 360 for a 30-year loan.</li>
</ul>
<h2>Example</h2>
<p>Take a {usd0(M_PRICE)} home with {M_DOWN}% down. The loan is {usd0(M_LOAN)}. At {M_RATE}% for {M_YEARS} years, principal and interest come to {usd2(M_PI)} a month. Add property tax at 1% of the home price a year ({usd2(M_TAX)} a month) and {usd0(1800)} a year of insurance ({usd2(M_INS)} a month), and the total is about <strong>{usd2(M_TOTAL)}</strong> a month.</p>
<p>Over the full {M_YEARS} years you would pay about {usd0(M_INT)} in interest, which is more than the original loan. Interest is front-loaded: in the first years most of each payment goes to interest, and only later does the balance fall quickly.</p>
<h2>What extra payments do</h2>
<p>An extra payment goes straight to principal, so you stop paying interest on that part of the balance. Adding $200 a month to the loan above pays it off in {years_months(M_FAST_MONTHS)} instead of 30 years and saves about {usd0(M_INT - M_FAST_INT)} in interest. Enter an amount in the extra payment box to try your own number. Check with your loan servicer that extra money is applied to principal and that your loan has no prepayment penalty.</p>
<h2>Down payment and PMI</h2>
<p>If you put down less than 20% on a conventional loan, lenders usually charge private mortgage insurance (PMI). It often costs roughly 0.3% to 1.5% of the loan a year, depending on your credit score and down payment. On most conventional loans PMI can be removed once you reach 20% equity, and it ends automatically at 22% equity if you are current on payments. FHA loans use a different type of mortgage insurance with its own rules, so treat the PMI line as a rough guide for those.</p>
<h2>Property tax and insurance vary by location</h2>
<p>Property tax rates differ a lot between states and even between neighboring counties, and insurance costs depend on the home, its location and your coverage. Use the figures from the listing, your county assessor or an insurance quote for the most accurate result.</p>
<p class="notice">This is an estimate. Your lender's loan estimate will show your exact rate, fees and closing costs. Closing costs, changes in tax or insurance over time and adjustable rates are not included.</p>
""",
            "faqs": [
                ("What is included in a monthly mortgage payment?", "Principal and interest on the loan, plus property tax and homeowners insurance. Mortgage insurance (PMI) and HOA dues are added when they apply. This calculator shows each part separately."),
                ("How much should I put down on a house?", "Putting down 20% avoids PMI on most conventional loans, but many buyers put down less. A smaller down payment means a larger loan and a higher monthly cost, so weigh it against keeping cash for repairs and emergencies."),
                ("Is a 15-year or a 30-year mortgage better?", "A 15-year loan has a higher monthly payment but usually a lower rate and far less total interest. A 30-year loan has a lower payment and more flexibility. Choose the shortest term whose payment you can pay comfortably."),
                ("Do extra mortgage payments really save money?", "Yes. Extra money reduces the balance that interest is charged on, which shortens the loan and cuts total interest. The earlier in the loan you make extra payments, the more they save."),
            ],
        },
        # ------------------------------------------------------------------ auto loan
        {
            "slug": "auto-loan-calculator", "name": "Auto Loan Calculator", "glyph": "auto",
            "short": "Monthly car payment with sales tax and trade-in",
            "title": "Auto Loan Calculator – Monthly Car Payment with Sales Tax",
            "desc": "Free auto loan calculator. Enter the car price, down payment, trade-in, sales tax, rate and term to see your monthly car payment and total interest.",
            "lead": "Work out what a car will really cost each month and in total, including sales tax, your down payment and any trade-in.",
            "keywords": "auto car loan vehicle payment financing apr trade-in sales tax",
            "related": ["mortgage-calculator", "credit-card-payoff-calculator", "take-home-pay-calculator"],
            "panels": lambda: calc_panel(
                "auto",
                num_field("price", "Vehicle price", 35000, 5000, 150000, 500, prefix="$")
                + num_field("down", "Down payment", 3000, 0, 0, 500, prefix="$", slider=False)
                + num_field("trade", "Trade-in value", 0, 0, 0, 500, prefix="$", slider=False)
                + num_field("tax", "Sales tax", 6, 0, 0, 0.25, suffix="%", slider=False)
                + num_field("rate", "Interest rate (APR)", 7, 0, 20, 0.1, suffix="%")
                + seg_field("months", "Loan term", [("36", "36 mo"), ("48", "48 mo"), ("60", "60 mo"), ("72", "72 mo"), ("84", "84 mo")], "60")),
            "body": f"""
<h2>How the auto loan calculator works</h2>
<p>A car loan works like any fixed-rate installment loan. You borrow an amount, pay a fixed monthly payment, and each payment covers that month's interest plus a slice of the balance. The calculator first works out how much you need to borrow, then applies the standard payment formula:</p>
<p class="formula-box">Amount financed = price − trade-in + sales tax − down payment<br>Payment = L × r × (1 + r)ⁿ ÷ [(1 + r)ⁿ − 1]</p>
<p>Here L is the amount financed, r is the monthly rate (the APR divided by 12) and n is the number of months.</p>
<h2>Example</h2>
<p>A {usd0(A_PRICE)} car with {usd0(A_DOWN)} down and 6% sales tax ({usd0(A_TAXAMT)}) means you finance {usd0(A_LOAN)}. At {A_RATE}% APR over {A_N} months the payment is about <strong>{usd2(A_PAY)}</strong>, and you pay roughly {usd0(A_INT)} in interest.</p>
<h2>Choosing the loan term</h2>
<p>A longer term lowers the monthly payment but raises the total interest. It also keeps you owing money for longer, and cars lose value quickly, so on a long loan you can owe more than the car is worth for a while. Compare 48, 60 and 72 months above to see the trade-off.</p>
<p>A common rule of thumb is the 20/4/10 guideline: put at least 20% down, finance for no more than four years, and keep total car costs, including insurance and fuel, under about 10% of your gross income. It is a starting point rather than a rule.</p>
<h2>What is not included</h2>
<p>Sales tax rules differ by state. This calculator applies the tax rate to the price minus your trade-in, which some states do and some do not. Title, registration and dealer fees, add-ons such as extended warranties, and insurance are not included. Ask the dealer for an out-the-door price and use that figure to get a closer result.</p>
<p class="notice">Estimates only. Your lender's actual terms depend on your credit, the vehicle and the loan offer.</p>
""",
            "faqs": [
                ("How is a car loan payment calculated?", "From the amount you finance, the interest rate and the number of months, using the standard installment-loan formula shown above. Sales tax and fees can be rolled into the loan, which raises the amount financed."),
                ("Should I choose a 60-month or a 72-month car loan?", "A 72-month loan has a lower payment but costs more in interest and leaves you owing for longer. If you can afford the 60-month payment comfortably, it usually costs less overall."),
                ("Does a bigger down payment help?", "Yes. It reduces the amount you borrow, which lowers both the monthly payment and the total interest, and it helps you avoid owing more than the car is worth."),
            ],
        },
        # ------------------------------------------------------------------ compound interest
        {
            "slug": "compound-interest-calculator", "name": "Compound Interest Calculator", "glyph": "1+r",
            "short": "Grow savings with monthly contributions",
            "title": "Compound Interest Calculator – With Monthly Contributions",
            "desc": "Free compound interest calculator. Enter a starting balance, monthly contribution, interest rate and time to see your future value and how much is interest.",
            "lead": "See how a starting balance and regular contributions grow over time when interest earns interest.",
            "keywords": "compound interest savings investment growth future value contributions rule of 72",
            "related": ["retirement-calculator", "mortgage-calculator", "credit-card-payoff-calculator"],
            "panels": lambda: calc_panel(
                "compound",
                num_field("initial", "Starting balance", 10000, 0, 500000, 1000, prefix="$")
                + num_field("monthly", "Monthly contribution", 500, 0, 5000, 50, prefix="$")
                + num_field("rate", "Annual interest rate", 7, 0, 20, 0.1, suffix="%")
                + num_field("years", "Time", 20, 1, 50, 1, suffix="yrs")
                + seg_field("freq", "Compounded", [("12", "Monthly"), ("4", "Quarterly"), ("1", "Yearly"), ("365", "Daily")], "12")),
            "body": f"""
<h2>How compound interest works</h2>
<p>With simple interest you earn only on your original deposit. With compound interest you also earn on the interest you have already earned, so growth speeds up over time. The formula for a single deposit is:</p>
<p class="formula-box">A = P × (1 + r ÷ n)ⁿᵗ</p>
<ul>
<li><strong>P</strong> is the starting balance.</li>
<li><strong>r</strong> is the annual interest rate as a decimal (7% is 0.07).</li>
<li><strong>n</strong> is how many times a year interest is added.</li>
<li><strong>t</strong> is the number of years.</li>
</ul>
<p>This calculator also adds your monthly contribution at the end of each month, and the contribution earns interest from the following month.</p>
<h2>Example</h2>
<p>Start with {usd0(10000)} and add $500 a month at 7% a year, compounded monthly, for 20 years. You put in {usd0(10000 + C_PUT)} in total, and the balance grows to about <strong>{usd0(C_BAL)}</strong>. Roughly {usd0(C_INT)} of that is interest you did not have to deposit.</p>
<h2>Why time matters more than the exact rate</h2>
<p>Most of the growth arrives in the later years, when the balance is large. Starting ten years earlier usually does more than finding a slightly higher rate. A quick check is the rule of 72: divide 72 by the annual rate to estimate how many years it takes to double. At 7%, that is about 10 years.</p>
<h2>Does compounding frequency matter?</h2>
<p>Only a little. Monthly compounding earns slightly more than yearly, and daily slightly more than monthly, but the gap is small compared with the effect of the rate, the contributions and the time.</p>
<p class="notice">Returns on savings accounts and investments are not guaranteed, and investment returns vary from year to year. Taxes and fees are not included. Treat the result as an illustration, not a forecast.</p>
""",
            "faqs": [
                ("What is the difference between simple and compound interest?", "Simple interest is calculated only on the original amount. Compound interest is calculated on the original amount plus the interest already added, so it grows faster."),
                ("What interest rate should I use?", "For a savings account, use the account's stated rate. For investments, many people try a few cautious figures, such as 5%, 7% and 9%, to see a range instead of relying on a single number."),
                ("Are contributions added at the start or end of the month?", "At the end of each month in this calculator. Adding them at the start would give a slightly higher result."),
            ],
        },
        # ------------------------------------------------------------------ retirement
        {
            "slug": "retirement-calculator", "name": "Retirement Calculator", "glyph": "401k",
            "short": "Project 401(k) savings and retirement income",
            "title": "Retirement Calculator – Will Your 401(k) Savings Be Enough?",
            "desc": "Free retirement calculator. Enter your age, savings, monthly contributions and employer match to project your balance at retirement in today's dollars.",
            "lead": "Project your savings at retirement, adjust for inflation, and see a rough yearly income your balance could support.",
            "keywords": "retirement 401k savings employer match inflation 4% rule nest egg",
            "related": ["compound-interest-calculator", "take-home-pay-calculator", "mortgage-calculator"],
            "panels": lambda: calc_panel(
                "retire",
                num_field("age", "Current age", 35, 18, 75, 1)
                + num_field("retire", "Retirement age", 67, 40, 80, 1)
                + num_field("saved", "Current retirement savings", 50000, 0, 1000000, 5000, prefix="$")
                + num_field("monthly", "Your contribution (per month)", 700, 0, 5000, 50, prefix="$")
                + num_field("employer", "Employer contribution (per month)", 300, 0, 0, 50, prefix="$", slider=False)
                + num_field("rate", "Expected annual return", 7, 0, 12, 0.1, suffix="%")
                + num_field("inflation", "Inflation", 2.5, 0, 0, 0.1, suffix="%", slider=False)),
            "body": f"""
<h2>How the retirement calculator works</h2>
<p>The calculator starts with your current savings and adds your contribution and your employer's contribution every month until your retirement age. The balance grows at the annual return you enter, applied evenly across the months. It then shows two numbers: the balance in future dollars, and the same balance in today's dollars after adjusting for inflation, which is the more useful figure for planning.</p>
<h2>Example</h2>
<p>A 35-year-old retiring at 67 with {usd0(50000)} saved, who contributes $700 a month with a $300 employer contribution, earning 7% a year, reaches about <strong>{usd0(R_BAL)}</strong> at 67. With 2.5% yearly inflation that is worth about {usd0(R_REAL)} in today's money.</p>
<h2>A rough income from your savings</h2>
<p>The calculator shows what a 4% withdrawal would give you each year. The 4% rule comes from historical research on US stocks and bonds. It suggests that withdrawing about 4% of your balance in the first year, then adjusting for inflation, has generally lasted around 30 years. It is a rough guide, not a guarantee, and your own spending, investments and retirement length will differ. Withdrawals from a traditional 401(k) are also taxed as ordinary income, so the amount you can spend is lower than the figure shown.</p>
<h2>2026 401(k) limits</h2>
<p>For 2026 the limit on your own 401(k) contributions is $24,500. People aged 50 and older can add a catch-up contribution of $8,000. Employer contributions do not count toward your personal limit. If you save in other accounts as well, the calculator does not require you to stay under this limit.</p>
<h2>What is not included</h2>
<p>Social Security, pensions, taxes on withdrawals, fees and the order of returns are not modeled. Markets do not return a steady 7% each year, so real results will be higher in some years and lower in others.</p>
<p class="notice">This calculator is for general planning and is not investment or tax advice. A financial professional can help with your full situation.</p>
""",
            "faqs": [
                ("How much do I need to retire?", "It depends on your spending. A common starting point is to estimate yearly spending in retirement, subtract expected Social Security or pension income, and divide the rest by 0.04 to see a rough target balance."),
                ("What return should I assume?", "Use a cautious figure. Many planners test 5% to 7% a year, then check the result at a lower number to see how much it changes."),
                ("Why show the result in today's dollars?", "Prices rise over time, so a large number decades from now buys less than it does today. The inflation-adjusted figure shows what the money could buy at current prices."),
                ("Does the employer contribution count toward the 401(k) limit?", "Not toward your personal limit. Your own deferrals have their own limit, and a separate overall limit covers employee and employer contributions together."),
            ],
        },
        # ------------------------------------------------------------------ credit card payoff
        {
            "slug": "credit-card-payoff-calculator", "name": "Credit Card Payoff Calculator", "glyph": "card",
            "short": "How long to pay off a balance and what it costs",
            "title": "Credit Card Payoff Calculator – How Long Until You're Debt-Free",
            "desc": "Free credit card payoff calculator. Enter your balance, APR and monthly payment to see how long it takes to pay off and how much interest you will pay.",
            "lead": "Find out when your card will be paid off at your current payment, and how much interest you will pay on the way.",
            "keywords": "credit card payoff debt balance apr interest minimum payment debt free",
            "related": ["auto-loan-calculator", "compound-interest-calculator", "take-home-pay-calculator"],
            "panels": lambda: calc_panel(
                "card",
                num_field("balance", "Card balance", 5000, 500, 50000, 100, prefix="$")
                + num_field("apr", "Interest rate (APR)", 22, 0, 36, 0.1, suffix="%")
                + num_field("payment", "Monthly payment", 200, 25, 2000, 5, prefix="$")),
            "body": f"""
<h2>How the credit card payoff calculator works</h2>
<p>Each month your card charges interest on the remaining balance at one-twelfth of the yearly rate. Your payment first covers that interest and the rest reduces the balance. The calculator repeats this month by month until the balance reaches zero, then adds up the interest. If you stop using the card, the number of months can also be found with this formula:</p>
<p class="formula-box">Months = −ln(1 − r × B ÷ P) ÷ ln(1 + r)</p>
<p>B is your balance, P is your monthly payment and r is the monthly rate (the APR divided by 12).</p>
<h2>Example</h2>
<p>A balance of {usd0(5000)} at 22% APR with a $200 monthly payment takes {years_months(K_MONTHS)} to pay off and costs about {usd0(K_INT)} in interest. Raising the payment to $250 cuts that to {years_months(K_MONTHS_B)} and the interest to about {usd0(K_INT_B)}. A small increase in the payment saves a lot because the interest charge shrinks each month the balance falls.</p>
<h2>Why minimum payments are slow</h2>
<p>Minimum payments are typically a small percentage of the balance plus interest, so they fall as the balance falls. Paying only the minimum can keep you in debt for many years and cost far more in interest than the original balance. Choose a fixed payment that you keep the same each month, even as the minimum drops.</p>
<h2>Ways to pay off a card faster</h2>
<ul>
<li>Pay more than the minimum, and keep paying the same amount as the balance falls.</li>
<li>If you have several cards, the avalanche method puts extra money toward the highest APR first and saves the most interest. The snowball method targets the smallest balance first, which some people find more motivating.</li>
<li>Consider a balance transfer card with a low introductory rate. These usually charge a transfer fee, often 3% to 5%, so compare it with the interest you would save.</li>
<li>Stop adding new purchases to the card while you pay it off.</li>
</ul>
<p class="notice">This calculator assumes a fixed APR and no new charges. Rates and fees vary by card, so check your statement for the exact figures.</p>
""",
            "faqs": [
                ("How is credit card interest calculated?", "Most cards divide the APR by 12 (or by 365 for a daily rate) and charge it on your balance. Paying in full each month avoids interest on new purchases."),
                ("What if my payment is too low?", "If the payment does not cover the monthly interest, the balance never falls. The calculator tells you the minimum amount you need to bring the balance down."),
                ("Is it better to pay off the highest-rate or the smallest balance first?", "The highest rate first (avalanche) costs less in interest. The smallest balance first (snowball) gives quicker wins. Either works if you stay consistent."),
            ],
        },
        # ------------------------------------------------------------------ take-home pay
        {
            "slug": "take-home-pay-calculator", "name": "Take-Home Pay Calculator", "glyph": "net",
            "short": "Salary after federal tax, FICA and 401(k)",
            "title": "Take-Home Pay Calculator – Salary After Federal Tax (2026)",
            "desc": "Free take-home pay calculator using 2026 federal tax brackets. See your salary after federal income tax, Social Security, Medicare, state tax and 401(k).",
            "lead": "Turn a salary into what lands in your account. Uses 2026 federal tax brackets, payroll taxes and an estimated state rate.",
            "keywords": "take home pay salary paycheck net income federal tax fica social security medicare 401k after tax",
            "related": ["retirement-calculator", "mortgage-calculator", "auto-loan-calculator"],
            "panels": lambda: calc_panel(
                "takehome",
                num_field("salary", "Annual salary (before tax)", 75000, 20000, 400000, 1000, prefix="$")
                + seg_field("status", "Filing status", [("single", "Single"), ("married", "Married filing jointly")], "single")
                + num_field("k401", "Pre-tax 401(k) (per year)", 0, 0, 0, 500, prefix="$", slider=False)
                + num_field("state", "State income tax (estimated rate)", 5, 0, 0, 0.5, suffix="%", slider=False)),
            "body": f"""
<h2>How take-home pay is calculated</h2>
<p>Your paycheck is your salary minus several deductions. This calculator applies them in the order that payroll does:</p>
<ul>
<li><strong>Pre-tax 401(k):</strong> money you put into a traditional 401(k) reduces the income that federal and most state income tax is based on. It does not reduce Social Security and Medicare tax.</li>
<li><strong>Federal income tax:</strong> the standard deduction ($16,100 for single filers and $32,200 for married couples filing jointly in 2026) is subtracted first. The rest is taxed in layers, called brackets.</li>
<li><strong>Social Security:</strong> 6.2% of wages up to $184,500 in 2026.</li>
<li><strong>Medicare:</strong> 1.45% of all wages, plus an extra 0.9% on wages above $200,000 for single filers and $250,000 for married couples filing jointly.</li>
<li><strong>State income tax:</strong> you enter an estimated rate. Some states, such as Texas and Florida, do not tax wages.</li>
</ul>
<h2>2026 federal tax brackets</h2>
<p>Each rate applies only to the slice of taxable income inside its range, not to all your income. Single filers:</p>
{bracket_table("single")}
<p>Married filing jointly:</p>
{bracket_table("married")}
<h2>Marginal rate and effective rate</h2>
<p>Your marginal rate is the rate on your last dollar of taxable income, which is the bracket you fall in. Your effective rate is your total federal tax divided by your salary, and it is always lower. Moving into a higher bracket only taxes the extra income at the higher rate, so a raise never lowers your take-home pay.</p>
<h2>Example</h2>
<p>A single filer earning {usd0(75000)} has taxable income of {usd0(T["taxable"])} after the standard deduction. Federal income tax is about {usd0(T["fed"])}, Social Security {usd0(T["ss"])} and Medicare {usd0(T["med"])}. With a 5% state tax estimate of {usd0(T["state"])}, take-home pay is about <strong>{usd0(T["net"])}</strong> a year, or {usd0(T["net"] / 12)} a month.</p>
<h2>What is not included</h2>
<p>This is a simplified estimate. It does not include other income, itemized deductions, tax credits such as the child tax credit, local or city taxes, health insurance and other payroll deductions, or head of household filing. Your actual paycheck depends on your W-4 and your employer's payroll.</p>
<p class="notice">Figures are for tax year 2026. Tax rules change, so check irs.gov or a tax professional for your own situation.</p>
""",
            "faqs": [
                ("What is the difference between gross and take-home pay?", "Gross pay is your salary before anything is taken out. Take-home pay, also called net pay, is what remains after taxes and deductions such as a 401(k)."),
                ("Does a 401(k) contribution lower my taxes?", "A traditional 401(k) lowers the income used for federal and most state income tax, so your take-home pay falls by less than the amount you contribute. It does not lower Social Security or Medicare tax."),
                ("What state tax rate should I enter?", "Enter 0 if your state does not tax wages. Otherwise use your state's rate for your income level, which your state revenue department publishes. The calculator treats it as a flat percentage."),
                ("Why is my real paycheck different?", "Employers also withhold for health insurance, other benefits and local taxes, and withholding depends on your W-4. This calculator shows the annual tax picture, not your exact payroll."),
            ],
        },
    ]
