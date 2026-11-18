# Review packet: fable-authored templates

For each template: is the question clear and realistic, are its conventions stated, is the program right, and is every gold value correct? Record **accept**, **fix** (describe the change to the template) or **reject** with a reason in `synth/fable/reviews.json` (or tell Claude). Fixes change the template, never individual gold values. No R1 or R2 output exists for these questions.

Templates: 25 of 25 planned.

## 0. corporate_finance / wacc (basic)

`syn.fable.corporate_finance.wacc.wacc_from_target_debt_equity_ratio.basic.v1`

Authored by claude-fable-5-1 (effort high) in 2 attempt(s); rejected drafts: seed 0: question text is 509 characters; basic questions in train are at most 494 at the 90th percentile; state inputs and conventions concisely.

**Question (seed 0):**

> A company targets a market-value debt-to-equity ratio D/E of 1.25. Its annual nominal cost of equity ke is 11 percent, its annual nominal pretax cost of debt kd is 7 percent, and its corporate tax rate T is 20 percent. Capital weights follow from the target ratio alone, ke exceeds kd, and only debt receives the interest tax shield. Compute the annual nominal WACC in percent. Use exact arithmetic and do not round any intermediate value.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `percent` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "percent", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `target_debt_weight` | Exact debt share of capital from target ratio. | `{"type": "decimal", "unit": "ratio", "rounding": {"mode": "exact"}}` |
| `debt_contribution_percent` | Exact weighted after-tax debt contribution to WACC. | `{"type": "decimal", "unit": "percent", "rounding": {"mode": "exact"}}` |

**Parameters:** `DE` 0.20..1.50 step 0.05; `KE` 7.00..13.00 step 0.25; `KD` 3.00..7.50 step 0.25; `T` 20..35 step 1

**Program:**

```python
def solve():
    de = Q(P["DE"])
    ke = Q(P["KE"])
    kd = Q(P["KD"])
    t = Q(P["T"])
    if ke <= kd:
        raise ValueError("cost of equity must exceed pretax cost of debt")
    wd = de / (1 + de)
    we = 1 - wd
    after_tax_kd = kd * (1 - t / 100)
    debt_part = wd * after_tax_kd
    wacc = we * ke + debt_part
    return {"final": wacc, "target_debt_weight": wd, "debt_contribution_percent": debt_part}
```

**Gold for every instance:**

| Seed | Parameters | Final | target_debt_weight | debt_contribution_percent |
|---|---|---|---|---|
| 0 | DE=1.25, KD=7, KE=11, T=20 | 8.00 | 5/9 | 28/9 |
| 1 | DE=0.75, KD=4.25, KE=9, T=20 | 6.60 | 3/7 | 51/35 |
| 2 | DE=1.45, KD=4, KE=7.75, T=29 | 4.84 | 29/49 | 2059/1225 |
| 3 | DE=0.7, KD=3, KE=11, T=31 | 7.32 | 7/17 | 1449/1700 |
| 4 | DE=1.05, KD=5, KE=10.5, T=22 | 7.12 | 21/41 | 819/410 |
| 5 | DE=1.45, KD=5.75, KE=12.5, T=31 | 7.45 | 29/49 | 46023/19600 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 6/6 fields, all fields agree.

**Decision:** _pending_

---

## 1. sustainable_finance / sustainability_reporting (intermediate)

`syn.fable.sustainable_finance.sustainability_reporting.net_zero_offset_credit_purchase_cost.intermediate.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> A company's GHG inventory for the reporting year shows Scope 1 emissions S1=18850 tCO2e and location-based Scope 2 emissions S2=4900 tCO2e. It retires renewable energy certificates covering p=45.25 percent of Scope 2, so market-based Scope 2 equals the uncovered share of S2. Its net-zero reporting policy offsets all Scope 1 plus market-based Scope 2 with carbon credits of one tCO2e each, bought only in whole credits (any fractional ton of residual emissions requires one additional credit) at c=28.5 USD per credit. Use exact arithmetic. Compute the total credit purchase cost in USD.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `usd` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `market_based_scope2_trace` | Exact market-based Scope 2 emissions in tCO2e. | `{"type": "decimal", "unit": "tons_co2e", "rounding": {"mode": "exact"}}` |
| `residual_emissions_trace` | Exact residual emissions to be offset in tCO2e. | `{"type": "decimal", "unit": "tons_co2e", "rounding": {"mode": "exact"}}` |
| `credits_required_trace` | Whole number of carbon credits purchased. | `{"type": "decimal", "unit": "credits", "rounding": {"mode": "exact"}}` |

**Parameters:** `S1` 2000..20000 step 50; `S2` 1000..15000 step 25; `REC_PCT` 20.00..80.00 step 0.25; `PRICE` 8.00..30.00 step 0.25

**Program:**

```python
def solve():
    s1 = P["S1"]
    s2 = P["S2"]
    p = P["REC_PCT"]
    c = P["PRICE"]
    market_based_scope2 = s2 * (1 - p / 100)
    residual = s1 + market_based_scope2
    credits = math.ceil(residual)
    cost = credits * c
    return {
        "final": cost,
        "market_based_scope2_trace": market_based_scope2,
        "residual_emissions_trace": residual,
        "credits_required_trace": credits,
    }
```

**Gold for every instance:**

| Seed | Parameters | Final | market_based_scope2_trace | residual_emissions_trace | credits_required_trace |
|---|---|---|---|---|---|
| 0 | PRICE=28.5, REC_PCT=45.25, S1=18850, S2=4900 | 613690.50 | 2682.75 | 21532.75 | 21533 |
| 1 | PRICE=28.75, REC_PCT=39, S1=18800, S2=4400 | 617665.00 | 2684 | 21484 | 21484 |
| 2 | PRICE=12, REC_PCT=73.5, S1=5300, S2=7650 | 87936.00 | 2027.25 | 7327.25 | 7328 |
| 3 | PRICE=16.5, REC_PCT=41.25, S1=4900, S2=8125 | 159621.00 | 4773.4375 | 9673.4375 | 9674 |
| 4 | PRICE=15.25, REC_PCT=21.25, S1=16400, S2=9675 | 366305.00 | 7619.0625 | 24019.0625 | 24020 |
| 5 | PRICE=23, REC_PCT=56.75, S1=12400, S2=10200 | 386676.00 | 4411.5 | 16811.5 | 16812 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 8/8 fields, all fields agree.

**Decision:** _pending_

---

## 2. crypto_finance / global_events_impact (advanced)

`syn.fable.crypto_finance.global_events_impact.event_shock_margin_call_release_price.advanced.v1`

Authored by claude-fable-5-1 (effort high) in 2 attempt(s); rejected drafts: only 5 of 6 instances were valid; last errors: ["seed 21, params {'COINS': '47', 'DROP': '24', 'LOAN': '64000', 'MAINT': '1.5', 'P0': '3500', 'RECOVERY': '30'}:.

**Question (seed 0):**

> A fictional global event hits a locally described crypto asset. Pre-event price is P0=3400 USD and the event-day close is 31 percent below it. On each later day the close recovers 35 percent of the gap between the previous close and the pre-event price. A lender holds N=31 coins as collateral; the loan was sized so that the pre-event coin value equals c=1.3 times the loan amount. The lender requires the coin value at each close to be at least m=1.15 times the loan; at the event-day close the borrower deposits cash equal to the shortfall below that requirement. The cash is released at the first later close at which the coin value alone meets the requirement (equality counts). What is the close price in USD on the release day? Use exact arithmetic.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `usd` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `event_close_price` | Closing price in USD on the event day. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |
| `shortfall_deposit` | Cash deposited at event-day close, in USD. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |
| `release_threshold_price` | Lowest price where coins alone meet requirement, in USD. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |
| `days_to_release` | Days after event day until cash release. | `{"type": "decimal", "unit": "count", "rounding": {"mode": "exact"}}` |

**Parameters:** `P0` 2000..4000 step 50; `DROP` 25..45 step 1; `RECOVERY` 10..40 step 5; `COINS` 10..50 step 1; `C0` 1.30..1.50 step 0.05; `MAINT` 1.15..1.25 step 0.05

**Program:**

```python
def solve():
    P0 = Q(P["P0"])
    d = Q(P["DROP"]) / 100
    g = Q(P["RECOVERY"]) / 100
    N = Q(P["COINS"])
    c0 = Q(P["C0"])
    m = Q(P["MAINT"])
    L = N * P0 / c0
    p1 = P0 * (1 - d)
    req = m * L
    if p1 * N >= req:
        raise ValueError("no margin call on event day")
    if P0 * N <= req:
        raise ValueError("coins can never meet requirement")
    deposit = req - p1 * N
    thr = req / N
    price = p1
    days = 0
    while price * N < req:
        price = price + g * (P0 - price)
        days += 1
        if days > 500:
            raise ValueError("recovery too slow")
    return {
        "final": price,
        "event_close_price": p1,
        "shortfall_deposit": deposit,
        "release_threshold_price": thr,
        "days_to_release": days,
    }
```

**Gold for every instance:**

| Seed | Parameters | Final | event_close_price | shortfall_deposit | release_threshold_price | days_to_release |
|---|---|---|---|---|---|---|
| 0 | C0=1.3, COINS=31, DROP=31, MAINT=1.15, P0=3400, RECOVERY=35 | 3110.55 | 2346 | 266662/13 | 39100/13 | 3 |
| 1 | C0=1.45, COINS=38, DROP=29, MAINT=1.25, P0=2850, RECOVERY=40 | 2552.46 | 2023.5 | 477603/29 | 71250/29 | 2 |
| 2 | C0=1.35, COINS=21, DROP=25, MAINT=1.25, P0=2450, RECOVERY=10 | 2277.01 | 1837.5 | 162925/18 | 61250/27 | 12 |
| 3 | C0=1.3, COINS=18, DROP=38, MAINT=1.2, P0=2600, RECOVERY=20 | 2434.24 | 1612 | 14184 | 2400 | 8 |
| 4 | C0=1.4, COINS=23, DROP=35, MAINT=1.25, P0=3450, RECOVERY=30 | 3160.08 | 2242.5 | 134895/7 | 43125/14 | 4 |
| 5 | C0=1.35, COINS=47, DROP=28, MAINT=1.15, P0=2300, RECOVERY=30 | 1984.44 | 1656 | 384836/27 | 52900/27 | 2 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 10/10 fields, all fields agree.

**Decision:** _pending_

---

## 3. accounting_and_financial_reporting / balance_sheets (basic)

`syn.fable.accounting_and_financial_reporting.balance_sheets.ppe_carrying_amount_share_of_total_assets.basic.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> A balance sheet shows property, plant and equipment at historical cost of 304000 USD with accumulated depreciation of 119000 USD. Total assets are 810000 USD and already include the equipment at its carrying amount. Using carrying amount = cost minus accumulated depreciation, compute the carrying amount of property, plant and equipment as a percentage of total assets, in percentage points. Use exact arithmetic.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `percent` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "percent", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `ppe_carrying_amount` | Equipment cost less accumulated depreciation. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |

**Parameters:** `COST` 60000..400000 step 1000; `ACC_DEP` 10000..300000 step 1000; `TOTAL_ASSETS` 150000..900000 step 1000

**Program:**

```python
def solve():
    cost = P["COST"]
    acc_dep = P["ACC_DEP"]
    total_assets = P["TOTAL_ASSETS"]
    if acc_dep >= cost:
        raise ValueError("accumulated depreciation must be below cost")
    carrying = cost - acc_dep
    if carrying > total_assets:
        raise ValueError("carrying amount cannot exceed total assets")
    share = Fraction(carrying, total_assets) * 100
    return {"final": share, "ppe_carrying_amount": carrying}
```

**Gold for every instance:**

| Seed | Parameters | Final | ppe_carrying_amount |
|---|---|---|---|
| 2 | ACC_DEP=119000, COST=304000, TOTAL_ASSETS=810000 | 22.84 | 185000 |
| 3 | ACC_DEP=118000, COST=303000, TOTAL_ASSETS=208000 | 88.94 | 185000 |
| 4 | ACC_DEP=24000, COST=315000, TOTAL_ASSETS=571000 | 50.96 | 291000 |
| 5 | ACC_DEP=84000, COST=211000, TOTAL_ASSETS=506000 | 25.10 | 127000 |
| 7 | ACC_DEP=252000, COST=393000, TOTAL_ASSETS=291000 | 48.45 | 141000 |
| 9 | ACC_DEP=107000, COST=146000, TOTAL_ASSETS=671000 | 5.81 | 39000 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 4/4 fields, all fields agree.

**Decision:** _pending_

---

## 4. accounting_and_financial_reporting / income_statements (intermediate)

`syn.fable.accounting_and_financial_reporting.income_statements.basic_eps_midyear_share_issue.intermediate.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> A company reports net income of 1557000 USD for a 12-month year and declares preferred dividends of 120000 USD, which reduce income available to common shareholders. It had 450000 common shares outstanding on January 1 and issued 145000 additional shares for cash at the start of month 5 (month 1 is January), so the new shares are outstanding for the remaining months of the year. Weight each share block by months outstanding over 12, with no other share changes and no dilutive securities. Use exact arithmetic and compute basic earnings per share.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `usd_per_count` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "usd_per_count", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `income_to_common_trace` | Exact net income after preferred dividends. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |
| `new_share_weight_trace` | Exact fraction of year new shares outstanding. | `{"type": "decimal", "unit": "ratio", "rounding": {"mode": "exact"}}` |
| `weighted_average_shares_trace` | Exact weighted average common shares for the year. | `{"type": "decimal", "unit": "count", "rounding": {"mode": "exact"}}` |

**Parameters:** `NET_INCOME` 500000..5000000 step 1000; `PREF_DIV` 0..400000 step 5000; `OPENING_SHARES` 200000..2000000 step 10000; `NEW_SHARES` 20000..500000 step 5000; `ISSUE_MONTH` 2..12 step 1

**Program:**

```python
def solve():
    ni = P["NET_INCOME"]
    pref = P["PREF_DIV"]
    if pref >= ni:
        raise ValueError("preferred dividends must be below net income")
    income_common = ni - pref
    months = 13 - P["ISSUE_MONTH"]
    weight = Fraction(months, 12)
    wavg = P["OPENING_SHARES"] + P["NEW_SHARES"] * weight
    eps = Fraction(income_common) / wavg
    return {
        "final": eps,
        "income_to_common_trace": income_common,
        "new_share_weight_trace": weight,
        "weighted_average_shares_trace": wavg,
    }
```

**Gold for every instance:**

| Seed | Parameters | Final | income_to_common_trace | new_share_weight_trace | weighted_average_shares_trace |
|---|---|---|---|---|---|
| 0 | ISSUE_MONTH=5, NET_INCOME=1557000, NEW_SHARES=145000, OPENING_SHARES=450000, PREF_DIV=120000 | 2.63 | 1437000 | 2/3 | 1640000/3 |
| 1 | ISSUE_MONTH=11, NET_INCOME=3807000, NEW_SHARES=100000, OPENING_SHARES=870000, PREF_DIV=155000 | 4.12 | 3652000 | 1/6 | 2660000/3 |
| 2 | ISSUE_MONTH=10, NET_INCOME=3613000, NEW_SHARES=410000, OPENING_SHARES=990000, PREF_DIV=35000 | 3.28 | 3578000 | 0.25 | 1092500 |
| 3 | ISSUE_MONTH=9, NET_INCOME=4049000, NEW_SHARES=375000, OPENING_SHARES=1060000, PREF_DIV=135000 | 3.30 | 3914000 | 1/3 | 1185000 |
| 4 | ISSUE_MONTH=4, NET_INCOME=4824000, NEW_SHARES=50000, OPENING_SHARES=1310000, PREF_DIV=35000 | 3.55 | 4789000 | 0.75 | 1347500 |
| 5 | ISSUE_MONTH=2, NET_INCOME=1733000, NEW_SHARES=205000, OPENING_SHARES=220000, PREF_DIV=315000 | 3.48 | 1418000 | 11/12 | 1223750/3 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 8/8 fields, all fields agree.

**Decision:** _pending_

---

## 5. financial_markets / forex_trading (advanced)

`syn.fable.financial_markets.forex_trading.leveraged_fx_stop_versus_margin_closeout.advanced.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> A trader opens a long position of 150000 base-currency units at a spot quote of USD 1.335 per unit with 20:1 leverage, funded by an account holding USD 15000. Required margin is fixed at the entry notional divided by the leverage. Account equity equals the deposit plus the unrealised P/L of the position; one pip is a quote change of USD 0.0001 per unit. The broker closes the whole position automatically when equity falls to 100 percent of required margin, with no slippage. The trader also places a stop-loss 120 pips below the entry quote. The quote then declines steadily. Determine which exit fires first (if both would fire at the same quote, the stop-loss fires) and compute the signed realised P/L in USD at that exit; a loss is negative. Use exact arithmetic.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `usd` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `required_margin_trace` | USD margin required at entry. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |
| `closeout_quote_trace` | USD quote per unit triggering automatic close-out. | `{"type": "decimal", "unit": "usd_per_count", "rounding": {"mode": "exact"}}` |
| `closeout_pips_trace` | Adverse pips from entry to close-out. | `{"type": "decimal", "unit": "dimensionless", "rounding": {"mode": "exact"}}` |
| `exit_trigger_trace` | Which exit fires first. | `{"type": "enum", "allowed_values": ["stop_loss", "margin_closeout"]}` |

**Parameters:** `UNITS` 50000..300000 step 10000; `SPOT` 1.0500..1.3500 step 0.0050; `LEV` one of [10, 20, 30, 50]; `EQUITY` 3000..15000 step 500; `CLOSEOUT` one of [50, 80, 100]; `STOP_PIPS` 50..400 step 10

**Program:**

```python
def solve():
    N = P["UNITS"]
    S0 = P["SPOT"]
    L = P["LEV"]
    E = P["EQUITY"]
    c = P["CLOSEOUT"]
    k = P["STOP_PIPS"]
    pip = Q("0.0001")
    req = N * S0 / L
    if E <= req:
        raise ValueError("deposit does not cover required margin")
    equity_at_close = req * c / 100
    loss_to_close = E - equity_at_close
    if loss_to_close <= 0:
        raise ValueError("close-out would trigger immediately")
    s_close = S0 - loss_to_close / N
    if s_close <= 0:
        raise ValueError("close-out quote not positive")
    pip_value = N * pip
    pips_close = loss_to_close / pip_value
    if k <= pips_close:
        trigger = "stop_loss"
        pl = -k * pip_value
    else:
        trigger = "margin_closeout"
        pl = -loss_to_close
    return {
        "final": pl,
        "required_margin_trace": req,
        "closeout_quote_trace": s_close,
        "closeout_pips_trace": pips_close,
        "exit_trigger_trace": trigger,
    }
```

**Gold for every instance:**

| Seed | Parameters | Final | required_margin_trace | closeout_quote_trace | closeout_pips_trace | exit_trigger_trace |
|---|---|---|---|---|---|---|
| 0 | CLOSEOUT=100, EQUITY=15000, LEV=20, SPOT=1.335, STOP_PIPS=120, UNITS=150000 | -1800.00 | 10012.5 | 1.30175 | 332.5 | stop_loss |
| 3 | CLOSEOUT=80, EQUITY=4000, LEV=50, SPOT=1.35, STOP_PIPS=50, UNITS=120000 | -600.00 | 3240 | 10037/7500 | 352/3 | stop_loss |
| 4 | CLOSEOUT=80, EQUITY=7500, LEV=30, SPOT=1.15, STOP_PIPS=380, UNITS=170000 | -2286.67 | 19550/3 | 14491/12750 | 6860/51 | margin_closeout |
| 7 | CLOSEOUT=50, EQUITY=6000, LEV=50, SPOT=1.34, STOP_PIPS=120, UNITS=80000 | -960.00 | 2144 | 1.2784 | 616 | stop_loss |
| 9 | CLOSEOUT=100, EQUITY=14000, LEV=30, SPOT=1.125, STOP_PIPS=130, UNITS=160000 | -2080.00 | 6000 | 1.075 | 500 | stop_loss |
| 10 | CLOSEOUT=100, EQUITY=8000, LEV=50, SPOT=1.085, STOP_PIPS=190, UNITS=300000 | -1490.00 | 6510 | 32401/30000 | 149/3 | margin_closeout |

**Blind cross-check** (claude-fable-5-1, 2 instances): 10/10 fields, all fields agree.

**Decision:** _pending_

---

## 6. finance_regulation / security (basic)

`syn.fable.finance_regulation.security.ownership_dilution_from_new_issue.basic.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> Apply only this fictional scenario-local securities calculation. An investor holds 540000 shares of an issuer with 9700000 shares outstanding. The issuer then issues 200000 new shares, all to other parties; the investor buys none. Ownership percent is 100 times shares held divided by total shares outstanding. Compute the signed change in the investor's ownership in percentage points, post-issue minus pre-issue. Use exact arithmetic. Report pre-issue and post-issue ownership percent.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `percent` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "percent", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `pre_issue_ownership_percent` | Exact ownership percent before the new issue. | `{"type": "decimal", "unit": "percent", "rounding": {"mode": "exact"}}` |
| `post_issue_ownership_percent` | Ownership percent after the new issue. | `{"type": "decimal", "unit": "percent", "rounding": {"mode": "half_up", "decimal_places": 4}}` |

**Parameters:** `SHARES_HELD` 50000..600000 step 10000; `SHARES_OUTSTANDING` 1000000..10000000 step 100000; `NEW_SHARES` 100000..3000000 step 100000

**Program:**

```python
def solve():
    held = P["SHARES_HELD"]
    outstanding = P["SHARES_OUTSTANDING"]
    new = P["NEW_SHARES"]
    if held >= outstanding:
        raise ValueError("shares held must be less than shares outstanding")
    pre = Fraction(100 * held, outstanding)
    post = Fraction(100 * held, outstanding + new)
    change = post - pre
    return {
        "final": change,
        "pre_issue_ownership_percent": pre,
        "post_issue_ownership_percent": post
    }
```

**Gold for every instance:**

| Seed | Parameters | Final | pre_issue_ownership_percent | post_issue_ownership_percent |
|---|---|---|---|---|
| 0 | NEW_SHARES=200000, SHARES_HELD=540000, SHARES_OUTSTANDING=9700000 | -0.11 | 540/97 | 5.4545 |
| 1 | NEW_SHARES=1500000, SHARES_HELD=380000, SHARES_OUTSTANDING=9400000 | -0.56 | 190/47 | 3.4862 |
| 2 | NEW_SHARES=1600000, SHARES_HELD=230000, SHARES_OUTSTANDING=4100000 | -1.57 | 230/41 | 4.0351 |
| 3 | NEW_SHARES=2000000, SHARES_HELD=220000, SHARES_OUTSTANDING=6100000 | -0.89 | 220/61 | 2.7160 |
| 4 | NEW_SHARES=2400000, SHARES_HELD=320000, SHARES_OUTSTANDING=1200000 | -17.78 | 80/3 | 8.8889 |
| 5 | NEW_SHARES=2500000, SHARES_HELD=600000, SHARES_OUTSTANDING=10000000 | -1.20 | 6 | 4.8000 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 6/6 fields, all fields agree.

**Decision:** _pending_

---

## 7. mergers_and_acquisitions / valuation_methods (intermediate)

`syn.fable.mergers_and_acquisitions.valuation_methods.sotp_implied_value_per_share.intermediate.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> Use exact arithmetic. A target is valued on a sum-of-the-parts basis. Segment A EBITDA is 48 USD million at a comparable multiple of 9.5 times; Segment B EBITDA is 26 USD million at a multiple of 6.25 times. Net debt is 45 USD million (a negative value means net cash), minority interest is 7 USD million, and diluted shares outstanding are 39 million. Enterprise value is the sum of the two segment values. Equity value equals enterprise value minus net debt minus minority interest. Compute the implied equity value per share in USD.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `usd` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `segment_a_value` | Segment A value from its EBITDA multiple. | `{"type": "decimal", "unit": "usd_million", "rounding": {"mode": "exact"}}` |
| `sotp_enterprise_value` | Combined enterprise value of both segments. | `{"type": "decimal", "unit": "usd_million", "rounding": {"mode": "exact"}}` |
| `implied_equity_value` | Equity value after net debt and minority interest. | `{"type": "decimal", "unit": "usd_million", "rounding": {"mode": "exact"}}` |

**Parameters:** `EBITDA_A` 12..60 step 1; `MULT_A` 5.00..10.00 step 0.25; `EBITDA_B` 5..40 step 1; `MULT_B` 4.00..9.00 step 0.25; `NET_DEBT` -20..90 step 1; `MINORITY` 0..15 step 1; `SHARES` 10.0..80.0 step 0.5

**Program:**

```python
def solve():
    ebitda_a = Q(P["EBITDA_A"])
    mult_a = Q(P["MULT_A"])
    ebitda_b = Q(P["EBITDA_B"])
    mult_b = Q(P["MULT_B"])
    net_debt = Q(P["NET_DEBT"])
    minority = Q(P["MINORITY"])
    shares = Q(P["SHARES"])
    if shares <= 0:
        raise ValueError("shares must be positive")
    seg_a = ebitda_a * mult_a
    seg_b = ebitda_b * mult_b
    ev = seg_a + seg_b
    equity = ev - net_debt - minority
    if equity <= 0:
        raise ValueError("equity value must be positive")
    per_share = equity / shares
    return {
        "final": per_share,
        "segment_a_value": seg_a,
        "sotp_enterprise_value": ev,
        "implied_equity_value": equity,
    }
```

**Gold for every instance:**

| Seed | Parameters | Final | segment_a_value | sotp_enterprise_value | implied_equity_value |
|---|---|---|---|---|---|
| 0 | EBITDA_A=48, EBITDA_B=26, MINORITY=7, MULT_A=9.5, MULT_B=6.25, NET_DEBT=45, SHARES=39 | 14.53 | 456 | 618.5 | 566.5 |
| 1 | EBITDA_A=59, EBITDA_B=30, MINORITY=8, MULT_A=8.75, MULT_B=8.75, NET_DEBT=-19, SHARES=18 | 43.88 | 516.25 | 778.75 | 789.75 |
| 2 | EBITDA_A=59, EBITDA_B=6, MINORITY=13, MULT_A=9, MULT_B=5.25, NET_DEBT=78, SHARES=79.5 | 5.93 | 531 | 562.5 | 471.5 |
| 3 | EBITDA_A=22, EBITDA_B=18, MINORITY=15, MULT_A=6, MULT_B=4.75, NET_DEBT=-20, SHARES=54.5 | 4.08 | 132 | 217.5 | 222.5 |
| 4 | EBITDA_A=35, EBITDA_B=37, MINORITY=10, MULT_A=5.75, MULT_B=5, NET_DEBT=52, SHARES=24 | 13.51 | 201.25 | 386.25 | 324.25 |
| 5 | EBITDA_A=47, EBITDA_B=6, MINORITY=5, MULT_A=7, MULT_B=4.25, NET_DEBT=-6, SHARES=31 | 11.47 | 329 | 354.5 | 355.5 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 8/8 fields, all fields agree.

**Decision:** _pending_

---

## 8. corporate_finance / capital_structure (advanced)

`syn.fable.corporate_finance.capital_structure.mm_tax_recap_target_leverage_share_price.advanced.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> Use exact arithmetic. A firm with existing perpetual debt D0=390 USD million and current total firm value V=1780 USD million has N=105 million shares outstanding. The corporate tax rate is T=30 percent and Modigliani-Miller with taxes holds: each USD of additional perpetual debt adds T USD of tax shield to firm value. The firm announces a recapitalisation: it issues new perpetual debt and uses all proceeds to repurchase shares at the post-announcement price, which fully reflects the added tax shield. The new debt is sized so that total debt (existing plus new) divided by post-recapitalisation equity value equals the target ratio L=1. The disclosed inputs always imply a strictly positive new debt issue. Compute the post-announcement share price in USD.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `usd` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `new_debt_issued` | New perpetual debt issued in USD million. | `{"type": "decimal", "unit": "usd_million", "rounding": {"mode": "exact"}}` |
| `tax_shield_added` | Firm value added by the new tax shield. | `{"type": "decimal", "unit": "usd_million", "rounding": {"mode": "exact"}}` |
| `post_recap_equity_value` | Equity value after debt issue and buyback. | `{"type": "decimal", "unit": "usd_million", "rounding": {"mode": "exact"}}` |
| `shares_repurchased_millions` | Shares bought back, in millions of shares. | `{"type": "decimal", "unit": "count", "rounding": {"mode": "half_up", "decimal_places": 4}}` |

**Parameters:** `V` 800..2000 step 10; `D0` 100..400 step 10; `N` 40..150 step 5; `T` 20..30 step 1; `L` 0.60..1.20 step 0.05

**Program:**

```python
def solve():
    V = Q(P["V"])
    D0 = Q(P["D0"])
    N = Q(P["N"])
    t = Q(P["T"]) / 100
    L = Q(P["L"])
    denom = 1 + L - L * t
    dD = (L * (V - D0) - D0) / denom
    if dD <= 0:
        raise ValueError("target leverage already met or exceeded by existing debt")
    shield = t * dD
    VL = V + shield
    E_post = VL - D0 - dD
    if E_post <= 0:
        raise ValueError("non-positive post-recap equity")
    price = (VL - D0) / N
    shares_rep = dD / price
    if shares_rep >= N:
        raise ValueError("buyback exceeds shares outstanding")
    return {
        "final": price,
        "new_debt_issued": dD,
        "tax_shield_added": shield,
        "post_recap_equity_value": E_post,
        "shares_repurchased_millions": shares_rep,
    }
```

**Gold for every instance:**

| Seed | Parameters | Final | new_debt_issued | tax_shield_added | post_recap_equity_value | shares_repurchased_millions |
|---|---|---|---|---|---|---|
| 0 | D0=390, L=1, N=105, T=30, V=1780 | 14.92 | 10000/17 | 3000/17 | 16630/17 | 39.4292 |
| 1 | D0=350, L=0.65, N=100, T=21, V=910 | 5.62 | 28000/3027 | 1960/1009 | 1673000/3027 | 1.6461 |
| 2 | D0=250, L=0.8, N=40, T=30, V=1100 | 23.32 | 10750/39 | 1075/13 | 25625/39 | 11.8213 |
| 3 | D0=130, L=0.65, N=150, T=28, V=1100 | 7.10 | 125125/367 | 35035/367 | 265900/367 | 47.9988 |
| 4 | D0=260, L=0.65, N=145, T=29, V=1890 | 12.34 | 1599000/2923 | 463710/2923 | 3629200/2923 | 44.3470 |
| 5 | D0=290, L=1.2, N=150, T=20, V=1270 | 7.14 | 22150/49 | 4430/49 | 30300/49 | 63.3460 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 10/10 fields, all fields agree.

**Decision:** _pending_

---

## 9. crypto_finance / regulations (basic)

`syn.fable.crypto_finance.regulations.stablecoin_reserve_shortfall.basic.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> A fictional stablecoin issuer has 4650000 tokens outstanding, each redeemable at exactly 1 USD. A local reserve regulation requires liquid reserves equal to r=107.5 percent of the outstanding redemption value. The issuer currently holds 5370000 USD of eligible reserves. Use exact arithmetic. What is the signed reserve shortfall in USD, defined as required reserves minus held reserves (negative means a surplus)?
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `usd` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `required_reserve_trace` | Required reserve amount in USD. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |

**Parameters:** `TOKENS` 1000000..5000000 step 50000; `RESERVE_PCT` 100.0..110.0 step 0.5; `HELD` 900000..5600000 step 10000

**Program:**

```python
def solve():
    tokens = P["TOKENS"]
    r = P["RESERVE_PCT"]
    held = P["HELD"]
    outstanding_value = tokens * 1
    required = outstanding_value * r / 100
    shortfall = required - held
    return {"final": shortfall, "required_reserve_trace": required}
```

**Gold for every instance:**

| Seed | Parameters | Final | required_reserve_trace |
|---|---|---|---|
| 0 | HELD=5370000, RESERVE_PCT=107.5, TOKENS=4650000 | -371250.00 | 4998750 |
| 1 | HELD=2550000, RESERVE_PCT=100.5, TOKENS=2700000 | 163500.00 | 2713500 |
| 2 | HELD=1290000, RESERVE_PCT=102, TOKENS=4700000 | 3504000.00 | 4794000 |
| 3 | HELD=1910000, RESERVE_PCT=106, TOKENS=1800000 | -2000.00 | 1908000 |
| 4 | HELD=1310000, RESERVE_PCT=103.5, TOKENS=5000000 | 3865000.00 | 5175000 |
| 5 | HELD=1160000, RESERVE_PCT=102, TOKENS=3300000 | 2206000.00 | 3366000 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 4/4 fields, all fields agree.

**Decision:** _pending_

---

## 10. mergers_and_acquisitions / synergies_and_cost_savings (intermediate)

`syn.fable.mergers_and_acquisitions.synergies_and_cost_savings.headcount_synergy_severance_two_year_cumulative.intermediate.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> Use exact arithmetic. A merger eliminates N=190 redundant positions with an average fully loaded annual cost of c=135 thousand USD each. Severance paid once at closing equals m=5 months of the annual run-rate savings. Only p=80 percent of run-rate savings are realized in year 1; year 2 realizes the full run-rate. Compute cumulative net savings at the end of year 2 in USD million (realized savings in years 1 and 2 minus severance).
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `usd_million` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "usd_million", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `run_rate_savings` | Annual run-rate headcount savings in USD million. | `{"type": "decimal", "unit": "usd_million", "rounding": {"mode": "exact"}}` |
| `severance_cost` | One-time severance paid at closing. | `{"type": "decimal", "unit": "usd_million", "rounding": {"mode": "exact"}}` |
| `year_one_realized` | Savings realized during year one. | `{"type": "decimal", "unit": "usd_million", "rounding": {"mode": "exact"}}` |

**Parameters:** `POSITIONS` 40..400 step 10; `COST_PER_POSITION` 60..160 step 5; `SEVERANCE_MONTHS` 3..12 step 1; `PHASE_IN_PCT` 30..80 step 5

**Program:**

```python
def solve():
    n = P["POSITIONS"]
    c = P["COST_PER_POSITION"]
    m = P["SEVERANCE_MONTHS"]
    p = P["PHASE_IN_PCT"]
    run_rate = Fraction(n * c, 1000)
    severance = run_rate * Fraction(m, 12)
    year_one = run_rate * Fraction(p, 100)
    final = year_one + run_rate - severance
    return {
        "final": final,
        "run_rate_savings": run_rate,
        "severance_cost": severance,
        "year_one_realized": year_one,
    }
```

**Gold for every instance:**

| Seed | Parameters | Final | run_rate_savings | severance_cost | year_one_realized |
|---|---|---|---|---|---|
| 0 | COST_PER_POSITION=135, PHASE_IN_PCT=80, POSITIONS=190, SEVERANCE_MONTHS=5 | 35.48 | 25.65 | 10.6875 | 20.52 |
| 1 | COST_PER_POSITION=120, PHASE_IN_PCT=55, POSITIONS=270, SEVERANCE_MONTHS=10 | 23.22 | 32.4 | 27 | 17.82 |
| 2 | COST_PER_POSITION=60, PHASE_IN_PCT=55, POSITIONS=130, SEVERANCE_MONTHS=10 | 5.59 | 7.8 | 6.5 | 4.29 |
| 3 | COST_PER_POSITION=115, PHASE_IN_PCT=70, POSITIONS=80, SEVERANCE_MONTHS=4 | 12.57 | 9.2 | 46/15 | 6.44 |
| 4 | COST_PER_POSITION=85, PHASE_IN_PCT=50, POSITIONS=40, SEVERANCE_MONTHS=11 | 1.98 | 3.4 | 187/60 | 1.7 |
| 5 | COST_PER_POSITION=120, PHASE_IN_PCT=45, POSITIONS=330, SEVERANCE_MONTHS=8 | 31.02 | 39.6 | 26.4 | 17.82 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 8/8 fields, all fields agree.

**Decision:** _pending_

---

## 11. personal_finance / saveretire (advanced)

`syn.fable.personal_finance.saveretire.required_savings_rate_with_match_and_salary_growth.advanced.v1`

Authored by claude-fable-5-1 (effort high) in 3 attempt(s); rejected drafts: seed 0: question text is 843 characters; advanced questions in train are at most 831 at the 90th percentile; state inputs and conventions concisely; gold rejected by the toolkit validator: /slot_values/year_n_salary_usd: value exceeds 64 significant digits.

**Question (seed 0):**

> Apply only this fictional scenario-local retirement saving-rate rule. Age is 44, retirement age is 57; contribution years N equal the difference. Salary in year t is S=95000 USD times (1+g)^(t-1), g=4 percent. Current savings B=120000 USD and all contributions earn r=5.5 percent per year, compounded annually. At the end of each year t the employee contributes a fixed percent of that year's salary and the employer adds m=0 percent of the same salary; both then compound for N-t years. Target nest egg at retirement is 50 percent of year-N salary divided by withdrawal rate w=5 percent. Find the employee percent at which compounded savings plus contributions exactly equal the target; if negative, report zero. Use exact arithmetic and round only the final value half up to two decimals.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `percent` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "percent", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `year_n_salary_usd` | Salary in the final contribution year in USD. | `{"type": "decimal", "unit": "usd_per_year", "rounding": {"mode": "half_up", "decimal_places": 2}}` |
| `target_nest_egg_usd` | Target nest egg at retirement in USD. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}}` |
| `savings_future_value_usd` | Compounded current savings at retirement in USD. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}}` |
| `combined_required_percent` | Signed combined employee plus employer percent of salary needed. | `{"type": "decimal", "unit": "percent", "rounding": {"mode": "half_up", "decimal_places": 4}}` |

**Parameters:** `AGE` 25..45 step 1; `RET_AGE` 55..67 step 1; `SALARY` 40000..150000 step 5000; `GROWTH` 1.0..4.0 step 0.5; `SAVINGS` 0..200000 step 10000; `RETURN` 3.0..8.0 step 0.5; `MATCH` 0.0..6.0 step 1.0; `REPL` 50..80 step 5; `WDR` 3.0..5.0 step 0.5

**Program:**

```python
def solve():
    N = P["RET_AGE"] - P["AGE"]
    if N < 1:
        raise ValueError("retirement age must exceed current age")
    S = Q(P["SALARY"])
    g = Q(P["GROWTH"]) / 100
    r = Q(P["RETURN"]) / 100
    B = Q(P["SAVINGS"])
    m = Q(P["MATCH"])
    rep = Q(P["REPL"]) / 100
    w = Q(P["WDR"]) / 100
    final_salary = S * (1 + g) ** (N - 1)
    target = rep * final_salary / w
    fv_savings = B * (1 + r) ** N
    factor = sum((1 + g) ** (t - 1) * (1 + r) ** (N - t) for t in range(1, N + 1))
    combined = (target - fv_savings) / (S * factor) * 100
    employee = combined - m
    if employee < 0:
        employee = Q(0)
    return {
        "final": employee,
        "year_n_salary_usd": final_salary,
        "target_nest_egg_usd": target,
        "savings_future_value_usd": fv_savings,
        "combined_required_percent": combined,
    }
```

**Gold for every instance:**

| Seed | Parameters | Final | year_n_salary_usd | target_nest_egg_usd | savings_future_value_usd | combined_required_percent |
|---|---|---|---|---|---|---|
| 0 | AGE=44, GROWTH=4, MATCH=0, REPL=50, RETURN=5.5, RET_AGE=57, SALARY=95000, SAVINGS=120000, WDR=5 | 59.33 | 152098.06 | 1520980.61 | 240692.87 | 59.3339 |
| 1 | AGE=28, GROWTH=1, MATCH=6, REPL=75, RETURN=7, RET_AGE=67, SALARY=65000, SAVINGS=0, WDR=4.5 | 5.66 | 94869.27 | 1581154.51 | 0.00 | 11.6569 |
| 2 | AGE=42, GROWTH=3, MATCH=3, REPL=75, RETURN=7.5, RET_AGE=67, SALARY=60000, SAVINGS=50000, WDR=5 | 25.55 | 121967.65 | 1829514.70 | 304916.98 | 28.5536 |
| 3 | AGE=26, GROWTH=2, MATCH=2, REPL=65, RETURN=5.5, RET_AGE=56, SALARY=45000, SAVINGS=130000, WDR=4 | 13.95 | 79913.01 | 1298586.43 | 647913.67 | 15.9516 |
| 4 | AGE=38, GROWTH=1, MATCH=3, REPL=60, RETURN=3.5, RET_AGE=64, SALARY=60000, SAVINGS=120000, WDR=4 | 28.16 | 76945.92 | 1154188.80 | 293515.03 | 31.1648 |
| 5 | AGE=34, GROWTH=4, MATCH=6, REPL=75, RETURN=3, RET_AGE=66, SALARY=115000, SAVINGS=180000, WDR=5 | 43.91 | 387910.34 | 5818655.13 | 463514.90 | 49.9117 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 10/10 fields, all fields agree.

**Decision:** _pending_

---

## 12. finance_regulation / compliance (basic)

`syn.fable.finance_regulation.compliance.compliance_training_completion_shortfall.basic.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> Apply only this fictional scenario-local compliance policy. A firm has headcount N=450 employees, of whom C=90 have completed mandatory AML training. Policy requires at least T=83.5 percent of headcount to have completed it. The required count is the smallest whole number of employees that is at least T percent of N. Use exact arithmetic. Report the current completion rate in percent and the required count, then compute how many additional completions are needed, floored at zero.
> 
> Answer format: return only the exact numeric value interpreted in `count`, using finite-decimal notation when it terminates in base 10 and an irreducible `numerator/denominator` fraction otherwise, with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "count", "rounding": {"mode": "exact"}}`

| Slot | Description | Spec |
|---|---|---|
| `completion_rate_percent` | Current training completion rate in percent. | `{"type": "decimal", "unit": "percent", "rounding": {"mode": "exact"}}` |
| `required_completions` | Whole-number required completions under policy. | `{"type": "decimal", "unit": "count", "rounding": {"mode": "exact"}}` |

**Parameters:** `HEADCOUNT` 50..500 step 10; `COMPLETED` 30..500 step 1; `THRESHOLD` 80.0..98.0 step 0.5

**Program:**

```python
def solve():
    n = P["HEADCOUNT"]
    c = P["COMPLETED"]
    t = P["THRESHOLD"]
    if c > n:
        raise ValueError("completed exceeds headcount")
    rate = Q(100) * c / n
    required = math.ceil(t * n / 100)
    shortfall = max(0, required - c)
    return {"final": shortfall, "completion_rate_percent": rate, "required_completions": required}
```

**Gold for every instance:**

| Seed | Parameters | Final | completion_rate_percent | required_completions |
|---|---|---|---|---|
| 0 | COMPLETED=90, HEADCOUNT=450, THRESHOLD=83.5 | 286 | 20 | 376 |
| 1 | COMPLETED=72, HEADCOUNT=110, THRESHOLD=91.5 | 29 | 720/11 | 101 |
| 5 | COMPLETED=324, HEADCOUNT=490, THRESHOLD=87.5 | 105 | 3240/49 | 429 |
| 10 | COMPLETED=232, HEADCOUNT=400, THRESHOLD=91 | 132 | 58 | 364 |
| 11 | COMPLETED=426, HEADCOUNT=460, THRESHOLD=83 | 0 | 2130/23 | 382 |
| 12 | COMPLETED=100, HEADCOUNT=250, THRESHOLD=90 | 125 | 40 | 225 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 6/6 fields, all fields agree.

**Decision:** _pending_

---

## 13. fintech / digital_banking (intermediate)

`syn.fable.fintech.digital_banking.digital_savings_direct_deposit_boost_interest.intermediate.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> A fictional digital savings account has an ending balance B=2000 USD and pays a base annual rate r_b=0.85 percent. If the customer's monthly direct deposit D=4000 USD is at least the threshold T=2500 USD (a deposit exactly equal to T qualifies), the account instead pays a boosted annual rate r_h=4 percent on the part of the balance up to the cap C=17500 USD and the base rate on any balance above the cap. Otherwise the whole balance earns the base rate. Monthly interest is the annual rate divided by 12 applied to the ending balance only; the deposit itself is not added. Use exact arithmetic. What is the month's total interest in USD?
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `usd` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `boost_qualified` | Whether the direct deposit meets the threshold. | `{"type": "enum", "allowed_values": ["false", "true"]}` |
| `boosted_rate_balance` | Balance portion earning the boosted rate in USD. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |
| `base_rate_balance` | Balance portion earning the base rate in USD. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |

**Parameters:** `BALANCE` 2000..40000 step 250; `DEPOSIT` 0..4000 step 100; `THRESHOLD` 500..2500 step 250; `CAP` 5000..25000 step 2500; `BASE_RATE` 0.50..2.00 step 0.05; `BOOST_RATE` 3.00..5.50 step 0.10

**Program:**

```python
def solve():
    B = Q(P["BALANCE"])
    D = Q(P["DEPOSIT"])
    T = Q(P["THRESHOLD"])
    C = Q(P["CAP"])
    rb = Q(P["BASE_RATE"])
    rh = Q(P["BOOST_RATE"])
    if rh <= rb:
        raise ValueError("boost rate must exceed base rate")
    qualified = D >= T
    if qualified:
        boosted = min(B, C)
        base_part = B - boosted
    else:
        boosted = Q(0)
        base_part = B
    interest = boosted * rh / Q(1200) + base_part * rb / Q(1200)
    return {
        "final": interest,
        "boost_qualified": "true" if qualified else "false",
        "boosted_rate_balance": boosted,
        "base_rate_balance": base_part,
    }
```

**Gold for every instance:**

| Seed | Parameters | Final | boost_qualified | boosted_rate_balance | base_rate_balance |
|---|---|---|---|---|---|
| 0 | BALANCE=2000, BASE_RATE=0.85, BOOST_RATE=4, CAP=17500, DEPOSIT=4000, THRESHOLD=2500 | 6.67 | true | 2000 | 0 |
| 1 | BALANCE=33000, BASE_RATE=0.95, BOOST_RATE=3.2, CAP=22500, DEPOSIT=3100, THRESHOLD=2500 | 68.31 | true | 22500 | 10500 |
| 2 | BALANCE=2750, BASE_RATE=1.85, BOOST_RATE=3.9, CAP=17500, DEPOSIT=3100, THRESHOLD=2000 | 8.94 | true | 2750 | 0 |
| 3 | BALANCE=21750, BASE_RATE=1.25, BOOST_RATE=4.7, CAP=5000, DEPOSIT=2700, THRESHOLD=1500 | 37.03 | true | 5000 | 16750 |
| 4 | BALANCE=2500, BASE_RATE=0.6, BOOST_RATE=3.8, CAP=10000, DEPOSIT=2300, THRESHOLD=2000 | 7.92 | true | 2500 | 0 |
| 5 | BALANCE=35750, BASE_RATE=0.9, BOOST_RATE=5.1, CAP=7500, DEPOSIT=2800, THRESHOLD=2250 | 53.06 | true | 7500 | 28250 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 8/8 fields, all fields agree.

**Decision:** _pending_

---

## 14. fintech / robo_advisors (advanced)

`syn.fable.fintech.robo_advisors.drift_band_rebalance_first_trigger_month.advanced.v1`

Authored by claude-fable-5-1 (effort high) in 2 attempt(s); rejected drafts: seed 0, params {'B': '0.4', 'D': '2', 'E': '0.5', 'F': '0.5', 'V0': '60000', 'W': '70'}: 'equity_sleeve_at_trigger' = Fraction(331523455360743388432672935973869.

**Question (seed 0):**

> A fictional robo-advisor starts a portfolio of 60000 USD exactly at its target equity weight of 70 percent, the rest in bonds. Each month equities earn a fixed 0.5 percent and bonds a fixed 0.4 percent; then an annual advisory fee of 0.5 percent, charged as one twelfth of that rate at each month end, is deducted pro rata from both sleeves. After each month-end fee the advisor measures the equity weight and rebalances at the first month where the absolute deviation from target, in percentage points, strictly exceeds the band of 2 points; a deviation exactly equal to the band triggers nothing. The rebalance restores the target weight with a single equity trade against bonds. Use exact arithmetic. What signed equity trade in USD is executed at the first rebalance, where positive means buy and negative means sell?
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `usd` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `trigger_month_count` | Number of months until the first rebalance. | `{"type": "decimal", "unit": "count", "rounding": {"mode": "exact"}}` |
| `equity_sleeve_at_trigger` | Equity value after fee in trigger month. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 4}}` |
| `portfolio_total_at_trigger` | Total portfolio value after fee in trigger month. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 4}}` |
| `equity_weight_at_trigger` | Equity weight in percent at trigger month. | `{"type": "decimal", "unit": "percent", "rounding": {"mode": "half_up", "decimal_places": 4}}` |

**Parameters:** `V0` 10000..250000 step 1000; `W` one of [50, 60, 70, 80]; `E` 0.3..1.5 step 0.1; `B` -0.2..0.5 step 0.1; `D` 2.0..5.0 step 0.5; `F` 0.2..1.0 step 0.1

**Program:**

```python
def solve():
    V0 = Q(P["V0"])
    w = Q(P["W"]) / 100
    e = Q(P["E"]) / 100
    b = Q(P["B"]) / 100
    d = Q(P["D"])
    f = Q(P["F"]) / 100
    if e == b:
        raise ValueError("equal monthly returns never drift")
    keep = 1 - f / 12
    eq = V0 * w
    bd = V0 * (1 - w)
    n = 0
    while True:
        n += 1
        if n > 120:
            raise ValueError("band not breached within 120 months")
        eq = eq * (1 + e) * keep
        bd = bd * (1 + b) * keep
        wt = eq / (eq + bd)
        if abs(wt - w) * 100 > d:
            break
    total = eq + bd
    trade = w * total - eq
    return {
        "final": trade,
        "trigger_month_count": n,
        "equity_sleeve_at_trigger": eq,
        "portfolio_total_at_trigger": total,
        "equity_weight_at_trigger": wt * 100,
    }
```

**Gold for every instance:**

| Seed | Parameters | Final | trigger_month_count | equity_sleeve_at_trigger | portfolio_total_at_trigger | equity_weight_at_trigger |
|---|---|---|---|---|---|---|
| 0 | B=0.4, D=2, E=0.5, F=0.5, V0=60000, W=70 | -1833.03 | 98 | 65733.3787 | 91286.2068 | 72.0080 |
| 1 | B=0, D=2.5, E=1.5, F=0.5, V0=223000, W=50 | -6106.01 | 7 | 123387.2278 | 234562.4257 | 52.6032 |
| 2 | B=0, D=2, E=0.3, F=0.7, V0=204000, W=60 | -4368.79 | 29 | 131268.1960 | 211499.0103 | 62.0656 |
| 4 | B=-0.1, D=4.5, E=1.3, F=0.8, V0=106000, W=70 | -5775.46 | 17 | 91377.8280 | 122289.0927 | 74.7228 |
| 5 | B=-0.2, D=4.5, E=0.6, F=0.2, V0=28000, W=80 | -1503.85 | 39 | 28102.5751 | 33248.4117 | 84.5231 |
| 7 | B=0.1, D=3, E=1, F=0.7, V0=175000, W=70 | -6082.78 | 17 | 143645.3040 | 196517.8971 | 73.0953 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 10/10 fields, all fields agree.

**Decision:** _pending_

---

## 15. personal_finance / taxcalc (basic)

`syn.fable.personal_finance.taxcalc.withholding_settlement_refund_or_balance.basic.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> Apply only this fictional scenario-local tax policy. Taxable income in USD is 117500. Flat tax ratio is 0.32. Tax withheld during the year in USD is 16000. Tax liability equals taxable income times the ratio. Year-end settlement equals withheld minus liability; a positive value is a refund due, a negative value is a balance owed. Use exact arithmetic and round only the final settlement half up to two decimals. Report the tax liability.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `usd` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `tax_liability_usd` | Tax liability before any withholding credit. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |

**Parameters:** `INC` 20000..150000 step 500; `RATE` 0.10..0.35 step 0.01; `WH` 2000..50000 step 100

**Program:**

```python
def solve():
    inc = P["INC"]
    rate = P["RATE"]
    wh = P["WH"]
    liability = inc * rate
    settlement = wh - liability
    return {"final": settlement, "tax_liability_usd": liability}
```

**Gold for every instance:**

| Seed | Parameters | Final | tax_liability_usd |
|---|---|---|---|
| 0 | INC=117500, RATE=0.32, WH=16000 | -21600.00 | 37600 |
| 1 | INC=77000, RATE=0.24, WH=40700 | 22220.00 | 18480 |
| 2 | INC=60500, RATE=0.26, WH=15500 | -230.00 | 15730 |
| 3 | INC=102000, RATE=0.33, WH=26200 | -7460.00 | 33660 |
| 4 | INC=38000, RATE=0.35, WH=9600 | -3700.00 | 13300 |
| 5 | INC=108000, RATE=0.25, WH=48200 | 21200.00 | 27000 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 4/4 fields, all fields agree.

**Decision:** _pending_

---

## 16. financial_ratios / liqratio (intermediate)

`syn.fable.financial_ratios.liqratio.defensive_interval_ratio_days.intermediate.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> A firm holds cash 125000 USD, marketable securities 45000 USD, accounts receivable 159000 USD, and inventory 140000 USD. Annual operating expenses are 1350000 USD, of which 65000 USD is non-cash depreciation. Defensive assets include only cash, marketable securities, and receivables. Daily cash operating expenses are the cash portion of annual operating expenses spread evenly over 365 days. Compute the defensive interval ratio, i.e. the number of days the defensive assets can cover daily cash operating expenses. Use exact arithmetic.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `days` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "days", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `defensive_assets_total` | Total defensive assets in USD. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |
| `daily_cash_opex` | Daily cash operating expenses in USD per day. | `{"type": "decimal", "unit": "usd_per_day", "rounding": {"mode": "exact"}}` |

**Parameters:** `CASH` 20000..200000 step 1000; `SEC` 5000..120000 step 1000; `AR` 10000..250000 step 1000; `INV` 10000..300000 step 1000; `OPEX` 400000..2000000 step 10000; `DEP` 20000..150000 step 5000; `DAYS` one of [360, 365]

**Program:**

```python
def solve():
    cash = P["CASH"]
    sec = P["SEC"]
    ar = P["AR"]
    opex = P["OPEX"]
    dep = P["DEP"]
    days = P["DAYS"]
    if dep >= opex:
        raise ValueError("depreciation must be less than operating expenses")
    defensive = Fraction(cash + sec + ar)
    daily = Fraction(opex - dep, days)
    if daily <= 0:
        raise ValueError("daily cash expenses must be positive")
    dir_days = defensive / daily
    return {"final": dir_days, "defensive_assets_total": defensive, "daily_cash_opex": daily}
```

**Gold for every instance:**

| Seed | Parameters | Final | defensive_assets_total | daily_cash_opex |
|---|---|---|---|---|
| 0 | AR=159000, CASH=125000, DAYS=365, DEP=65000, INV=140000, OPEX=1350000, SEC=45000 | 93.45 | 329000 | 257000/73 |
| 1 | AR=169000, CASH=190000, DAYS=360, DEP=135000, INV=111000, OPEX=1460000, SEC=110000 | 127.43 | 469000 | 33125/9 |
| 2 | AR=26000, CASH=167000, DAYS=360, DEP=45000, INV=96000, OPEX=1700000, SEC=62000 | 55.47 | 255000 | 41375/9 |
| 3 | AR=14000, CASH=131000, DAYS=360, DEP=135000, INV=57000, OPEX=1420000, SEC=52000 | 55.19 | 197000 | 32125/9 |
| 4 | AR=235000, CASH=131000, DAYS=360, DEP=35000, INV=281000, OPEX=1060000, SEC=36000 | 141.19 | 402000 | 25625/9 |
| 5 | AR=125000, CASH=157000, DAYS=365, DEP=25000, INV=222000, OPEX=930000, SEC=105000 | 156.08 | 387000 | 181000/73 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 6/6 fields, all fields agree.

**Decision:** _pending_

---

## 17. sustainable_finance / green_bonds (advanced)

`syn.fable.sustainable_finance.green_bonds.sustainability_linked_green_bond_yield_to_worst.advanced.v1`

Authored by claude-fable-5-1 (effort high) in 2 attempt(s); rejected drafts: seed 0: question text is 892 characters; advanced questions in train are at most 831 at the 90th percentile; state inputs and conventions concisely.

**Question (seed 0):**

> A sustainability-linked green bond has face F=1000 USD, annual coupon c=4.6 percent of face paid each year-end, and matures in N=4 years with face repaid then. If the KPI observed at end of year k=2 is missed, coupons for years k+1 through N step up by s=100 basis points; miss probability is p=45 percent. Conventional debt yields y=4.6 percent, annually compounded; the issue price is the present value of probability-weighted expected cash flows discounted at y minus a greenium of g=25 basis points. Compute the yield-to-worst: the annually compounded yield at which cash flows with the step-up certain have present value equal to the issue price. Use exact arithmetic for prices and round only the final yield half up to four decimal places.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 4 decimal digits, and return only the numeric value interpreted in `percent` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "percent", "rounding": {"mode": "half_up", "decimal_places": 4}}`

| Slot | Description | Spec |
|---|---|---|
| `greenium_adjusted_yield` | Exact issue discount yield after greenium. | `{"type": "decimal", "unit": "percent", "rounding": {"mode": "exact"}}` |
| `issue_price` | Exact issue price of expected cash flows. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |
| `stepup_certain_value` | Exact step-up-certain value at issue discount yield. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |

**Parameters:** `face` one of [1000, 5000, 10000]; `coupon` 2.00..6.00 step 0.05; `years` 4..8 step 1; `kpi_year` 1..3 step 1; `stepup_bp` 25..100 step 25; `miss_prob` 10..60 step 5; `conv_yield` 3.00..7.00 step 0.05; `greenium_bp` 5..25 step 5

**Program:**

```python
def solve():
    F = Q(P["face"])
    c = Q(P["coupon"]) / 100
    N = P["years"]
    k = P["kpi_year"]
    s = Q(P["stepup_bp"]) / 10000
    p = Q(P["miss_prob"]) / 100
    y = Q(P["conv_yield"]) / 100
    g = Q(P["greenium_bp"]) / 10000
    if k >= N:
        raise ValueError("KPI year must be before maturity")
    yd = y - g
    if yd <= 0:
        raise ValueError("nonpositive discount yield")
    base = F * c
    up = F * (c + s)
    exp_cf = []
    worst_cf = []
    for t in range(1, N + 1):
        if t <= k:
            e = base
            w = base
        else:
            e = (1 - p) * base + p * up
            w = up
        if t == N:
            e = e + F
            w = w + F
        exp_cf.append(e)
        worst_cf.append(w)
    def pv(r, cf):
        total = Q(0)
        for t in range(1, N + 1):
            total = total + cf[t - 1] / (1 + r) ** t
        return total
    price = pv(yd, exp_cf)
    worst_at_yd = pv(yd, worst_cf)
    lo = Q(0)
    hi = Q(1)
    for i in range(80):
        mid = (lo + hi) / 2
        if pv(mid, worst_cf) > price:
            lo = mid
        else:
            hi = mid
    r = (lo + hi) / 2
    return {
        "final": r * 100,
        "greenium_adjusted_yield": yd * 100,
        "issue_price": price,
        "stepup_certain_value": worst_at_yd,
    }
```

**Gold for every instance:**

| Seed | Parameters | Final | greenium_adjusted_yield | issue_price | stepup_certain_value |
|---|---|---|---|---|---|
| 0 | conv_yield=4.6, coupon=4.6, face=1000, greenium_bp=25, kpi_year=2, miss_prob=45, stepup_bp=100, years=4 | 4.6092 | 4.35 | 19288859366276000/18970981313761 | 19468687366276000/18970981313761 |
| 1 | conv_yield=5.7, coupon=3.05, face=1000, greenium_bp=5, kpi_year=2, miss_prob=15, stepup_bp=50, years=8 | 5.9833 | 5.65 | 333642732863704764511117837000/397370823547272766854136321 | 341165286883336013473117837000/397370823547272766854136321 |
| 2 | conv_yield=3.9, coupon=4.25, face=10000, greenium_bp=20, kpi_year=3, miss_prob=25, stepup_bp=25, years=4 | 3.7437 | 3.7 | 11802948827525000/1156418486161 | 11821698827525000/1156418486161 |
| 3 | conv_yield=4.25, coupon=2.1, face=1000, greenium_bp=15, kpi_year=1, miss_prob=20, stepup_bp=50, years=5 | 4.4306 | 4.1 | 1118223098966981000/1222513454661201 | 378411423550327000/407504484887067 |
| 4 | conv_yield=3.1, coupon=2.95, face=5000, greenium_bp=20, kpi_year=2, miss_prob=15, stepup_bp=25, years=6 | 3.0370 | 2.9 | 851361520408707782500/169587644696673903 | 2001305131498026492500/395704504292239107 |
| 5 | conv_yield=4.9, coupon=5.8, face=1000, greenium_bp=20, kpi_year=1, miss_prob=50, stepup_bp=50, years=5 | 4.8882 | 4.7 | 49233294861074000/46598253990741 | 1340026310806498000/1258152857750007 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 8/8 fields, all fields agree.

**Decision:** _pending_

---

## 18. investment_analysis / roi (basic)

`syn.fable.investment_analysis.roi.rental_property_annual_cash_roi.basic.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> A rental property is bought outright for USD 145000 with no financing. It earns monthly rent of USD 2950 for all 12 months of the year and incurs annual operating expenses of USD 12300 for taxes, insurance and maintenance. Assume no vacancy and ignore any price appreciation. Compute annual net operating income = 12 x monthly rent - annual expenses, then the annual cash ROI = net operating income / purchase price x 100 percent. Use exact arithmetic.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `percent` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "percent", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `annual_gross_rent_trace` | Total rent collected over twelve months. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |
| `net_operating_income_trace` | Annual rent less annual operating expenses. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |

**Parameters:** `PRICE` 80000..400000 step 5000; `RENT` 500..3500 step 50; `EXPENSES` 1000..20000 step 100

**Program:**

```python
def solve():
    price = Q(P["PRICE"])
    rent = Q(P["RENT"])
    expenses = Q(P["EXPENSES"])
    gross_rent = 12 * rent
    noi = gross_rent - expenses
    roi = noi / price * 100
    return {"final": roi, "annual_gross_rent_trace": gross_rent, "net_operating_income_trace": noi}
```

**Gold for every instance:**

| Seed | Parameters | Final | annual_gross_rent_trace | net_operating_income_trace |
|---|---|---|---|---|
| 0 | EXPENSES=12300, PRICE=145000, RENT=2950 | 15.93 | 35400 | 23100 |
| 1 | EXPENSES=7600, PRICE=195000, RENT=1200 | 3.49 | 14400 | 6800 |
| 2 | EXPENSES=7600, PRICE=395000, RENT=1150 | 1.57 | 13800 | 6200 |
| 3 | EXPENSES=19000, PRICE=135000, RENT=2550 | 8.59 | 30600 | 11600 |
| 4 | EXPENSES=5100, PRICE=285000, RENT=1050 | 2.63 | 12600 | 7500 |
| 5 | EXPENSES=7900, PRICE=235000, RENT=2200 | 7.87 | 26400 | 18500 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 6/6 fields, all fields agree.

**Decision:** _pending_

---

## 19. financial_markets / stock_market_analysis (intermediate)

`syn.fable.financial_markets.stock_market_analysis.split_adjusted_holding_period_return.intermediate.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> An investor buys 70 shares at USD 40 each. The company then executes a 3-for-1 stock split. After the split, a cash dividend of USD 0.4 per post-split share is paid, and the investor later sells all post-split shares at USD 42.5 each. Compute the holding-period return in percent = (sale proceeds + total dividends - purchase cost) / purchase cost x 100. Use exact arithmetic.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `percent` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "percent", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `post_split_share_count` | Number of shares held after the split. | `{"type": "decimal", "unit": "count", "rounding": {"mode": "exact"}}` |
| `post_split_dividend_cash` | Total cash dividends on post-split shares. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |
| `post_split_sale_value` | Total proceeds from selling post-split shares. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |

**Parameters:** `N` 10..200 step 5; `P0` 40..150 step 1; `S` one of [2, 3, 4, 5]; `D` 0.10..1.50 step 0.05; `P1` 8.00..80.00 step 0.25

**Program:**

```python
def solve():
    n = P["N"]
    p0 = P["P0"]
    s = P["S"]
    d = P["D"]
    p1 = P["P1"]
    cost = n * p0
    shares_post = n * s
    dividends = shares_post * d
    proceeds = shares_post * p1
    hpr = Fraction(proceeds + dividends - cost, 1) / cost * 100
    return {
        "final": hpr,
        "post_split_share_count": shares_post,
        "post_split_dividend_cash": dividends,
        "post_split_sale_value": proceeds
    }
```

**Gold for every instance:**

| Seed | Parameters | Final | post_split_share_count | post_split_dividend_cash | post_split_sale_value |
|---|---|---|---|---|---|
| 0 | D=0.4, N=70, P0=40, P1=42.5, S=3 | 221.75 | 210 | 84 | 8925 |
| 1 | D=1.35, N=130, P0=147, P1=17.75, S=2 | -74.01 | 260 | 351 | 4615 |
| 2 | D=0.3, N=80, P0=42, P1=57.5, S=4 | 450.48 | 320 | 96 | 18400 |
| 3 | D=1.2, N=70, P0=70, P1=28.75, S=2 | -14.43 | 140 | 168 | 4025 |
| 4 | D=1.35, N=180, P0=45, P1=19.25, S=2 | -8.44 | 360 | 486 | 6930 |
| 5 | D=1.1, N=80, P0=64, P1=66.5, S=5 | 428.13 | 400 | 440 | 26600 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 8/8 fields, all fields agree.

**Decision:** _pending_

---

## 20. investment_analysis / rar (advanced)

`syn.fable.investment_analysis.rar.treynor_black_beta_adjusted_active_weight.advanced.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> An active fund has expected return R_a=4.5 percent, total standard deviation sigma_a=25 percent and beta=1.2 against the market index, which has expected return R_m=8 percent and standard deviation sigma_m=14 percent; the risk-free rate is R_f=3.5 percent. Apply the Treynor-Black model: alpha is the Jensen alpha of the fund, and residual variance is total variance minus beta-squared times market variance, with all variances in displayed percentage units squared. The unadjusted active weight w0 is alpha divided by residual variance, divided by the market risk premium divided by market variance. The beta-adjusted active weight is w0/(1+(1-beta)w0). Report the beta-adjusted active weight as a percentage of the total risky portfolio (negative means a short position) using exact arithmetic.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `percent` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "percent", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `jensen_alpha_trace` | Jensen alpha of the active fund in percentage points. | `{"type": "decimal", "unit": "percent", "rounding": {"mode": "exact"}}` |
| `residual_variance_trace` | Residual variance in displayed percent units squared. | `{"type": "decimal", "unit": "dimensionless", "rounding": {"mode": "exact"}}` |
| `unadjusted_weight_trace` | Unadjusted active weight as a plain ratio. | `{"type": "decimal", "unit": "ratio", "rounding": {"mode": "exact"}}` |

**Parameters:** `RA` 4.0..16.0 step 0.5; `SA` 12..30 step 1; `BETA` 0.6..1.4 step 0.1; `RM` 6.0..12.0 step 0.5; `SM` 10..22 step 1; `RF` 1.0..4.0 step 0.5

**Program:**

```python
def solve():
    ra = Q(P["RA"])
    sa = Q(P["SA"])
    beta = Q(P["BETA"])
    rm = Q(P["RM"])
    sm = Q(P["SM"])
    rf = Q(P["RF"])
    prem = rm - rf
    if prem <= 0:
        raise ValueError("market premium must be positive")
    alpha = ra - (rf + beta * prem)
    resid = sa * sa - beta * beta * sm * sm
    if resid <= 0:
        raise ValueError("residual variance must be positive")
    w0 = (alpha / resid) / (prem / (sm * sm))
    denom = 1 + (1 - beta) * w0
    if denom <= 0:
        raise ValueError("beta adjustment denominator must be positive")
    w = w0 / denom
    return {
        "final": w * 100,
        "jensen_alpha_trace": alpha,
        "residual_variance_trace": resid,
        "unadjusted_weight_trace": w0
    }
```

**Gold for every instance:**

| Seed | Parameters | Final | jensen_alpha_trace | residual_variance_trace | unadjusted_weight_trace |
|---|---|---|---|---|---|
| 0 | BETA=1.2, RA=4.5, RF=3.5, RM=8, SA=25, SM=14 | -50.29 | -4.4 | 342.76 | -3920/7011 |
| 3 | BETA=1.2, RA=12, RF=4, RM=8.5, SA=21, SM=11 | 27.66 | 2.6 | 266.76 | 1210/4617 |
| 4 | BETA=0.8, RA=4, RF=2.5, RM=6, SA=15, SM=16 | -225.63 | -1.3 | 61.16 | -16640/10703 |
| 8 | BETA=0.7, RA=13.5, RF=3.5, RM=7, SA=29, SM=22 | 113.85 | 7.55 | 603.84 | 91355/52836 |
| 9 | BETA=1.3, RA=6, RF=3, RM=6.5, SA=29, SM=14 | -16.20 | -1.55 | 509.76 | -1085/6372 |
| 10 | BETA=0.8, RA=10, RF=2, RM=12, SA=27, SM=12 | 0.00 | 0 | 636.84 | 0 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 8/8 fields, all fields agree.

**Decision:** _pending_

---

## 21. risk_management / stress_testing (basic)

`syn.fable.risk_management.stress_testing.post_stress_cet1_ratio.basic.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> Use exact arithmetic. A bank's common equity tier 1 capital is K=800 USD million and its risk-weighted assets are R=13700 USD million. A stress scenario produces a one-off loss of L=360 USD million that reduces capital in full while risk-weighted assets are unchanged. Compute the post-stress CET1 ratio as a percentage of risk-weighted assets without intermediate rounding, then round only the final value half up to 2 decimal places.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `percent` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "percent", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `post_stress_capital` | Exact capital remaining after the stress loss. | `{"type": "decimal", "unit": "usd_million", "rounding": {"mode": "exact"}}` |

**Parameters:** `K` 800..2000 step 10; `R` 8000..20000 step 100; `L` 50..600 step 10

**Program:**

```python
def solve():
    K = P["K"]
    R = P["R"]
    L = P["L"]
    if R <= 0:
        raise ValueError("risk-weighted assets must be positive")
    post_capital = Fraction(K) - Fraction(L)
    if post_capital <= 0:
        raise ValueError("stress loss wipes out capital")
    ratio_pct = post_capital / Fraction(R) * 100
    return {"final": ratio_pct, "post_stress_capital": post_capital}
```

**Gold for every instance:**

| Seed | Parameters | Final | post_stress_capital |
|---|---|---|---|
| 0 | K=800, L=360, R=13700 | 3.21 | 440 |
| 1 | K=1590, L=220, R=12300 | 11.14 | 1370 |
| 2 | K=1060, L=190, R=11300 | 7.70 | 870 |
| 3 | K=1560, L=250, R=10800 | 12.13 | 1310 |
| 4 | K=1880, L=480, R=14100 | 9.93 | 1400 |
| 5 | K=860, L=410, R=11900 | 3.78 | 450 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 4/4 fields, all fields agree.

**Decision:** _pending_

---

## 22. financial_ratios / effratio (intermediate)

`syn.fable.financial_ratios.effratio.dso_target_cash_release.intermediate.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> Annual credit sales are 2500000 USD. Accounts receivable were 260000 USD at the beginning of the year and 278000 USD at the end. Use the arithmetic mean of beginning and ending receivables and a 365-day year. Management targets days sales outstanding of 50 days with credit sales unchanged. Compute the cash released from receivables if the target is met: current average receivables minus the receivables level implied by the target. A negative value means receivables would have to rise. Use exact arithmetic.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `usd` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `avg_receivables` | Arithmetic mean of beginning and ending receivables in USD. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |
| `receivables_turnover` | Credit sales divided by average receivables. | `{"type": "decimal", "unit": "multiple", "rounding": {"mode": "exact"}}` |
| `current_dso` | Current days sales outstanding on a 365-day year. | `{"type": "decimal", "unit": "days", "rounding": {"mode": "exact"}}` |
| `target_receivables` | Receivables level implied by the target days in USD. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |

**Parameters:** `CREDIT_SALES` 600000..3000000 step 10000; `RECV_BEGIN` 60000..400000 step 1000; `RECV_END` 60000..400000 step 1000; `TARGET_DSO` 25..60 step 1

**Program:**

```python
def solve():
    S = Fraction(P["CREDIT_SALES"])
    rb = Fraction(P["RECV_BEGIN"])
    re = Fraction(P["RECV_END"])
    T = Fraction(P["TARGET_DSO"])
    avg = (rb + re) / 2
    if avg <= 0 or S <= 0:
        raise ValueError("non-positive inputs")
    turnover = S / avg
    dso = Fraction(365) / turnover
    target = S * T / Fraction(365)
    final = avg - target
    return {
        "final": final,
        "avg_receivables": avg,
        "receivables_turnover": turnover,
        "current_dso": dso,
        "target_receivables": target,
    }
```

**Gold for every instance:**

| Seed | Parameters | Final | avg_receivables | receivables_turnover | current_dso | target_receivables |
|---|---|---|---|---|---|---|
| 0 | CREDIT_SALES=2500000, RECV_BEGIN=260000, RECV_END=278000, TARGET_DSO=50 | -73465.75 | 269000 | 2500/269 | 39.274 | 25000000/73 |
| 1 | CREDIT_SALES=830000, RECV_BEGIN=146000, RECV_END=260000, TARGET_DSO=54 | 80205.48 | 203000 | 830/203 | 14819/166 | 8964000/73 |
| 2 | CREDIT_SALES=1230000, RECV_BEGIN=270000, RECV_END=353000, TARGET_DSO=58 | 116047.95 | 311500 | 2460/623 | 45479/492 | 14268000/73 |
| 3 | CREDIT_SALES=1000000, RECV_BEGIN=362000, RECV_END=117000, TARGET_DSO=46 | 113472.60 | 239500 | 2000/479 | 87.4175 | 9200000/73 |
| 4 | CREDIT_SALES=730000, RECV_BEGIN=189000, RECV_END=332000, TARGET_DSO=49 | 162500.00 | 260500 | 1460/521 | 130.25 | 98000 |
| 5 | CREDIT_SALES=1960000, RECV_BEGIN=174000, RECV_END=72000, TARGET_DSO=25 | -11246.58 | 123000 | 1960/123 | 8979/392 | 9800000/73 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 10/10 fields, all fields agree.

**Decision:** _pending_

---

## 23. risk_management / var (advanced)

`syn.fable.risk_management.var.two_asset_var_backtest_capital_charge.advanced.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> A two-asset portfolio has value V=2400000 USD, weight w1=40 percent in asset 1 and the rest in asset 2. Daily volatilities are s1=2 percent and s2=1.9 percent; return correlation is rho=-0.2. One-day diversified VaR is V times the supplied quantile z=1.645 times portfolio daily volatility (variance-covariance, zero mean); scale it to h=4 trading days by the square root of time. The average holding-period VaR over the prior 60 days is a=2 percent of V. Backtesting over 250 days gave n=4 exceptions. Multiplier k is 3 plus an add-on: 0 for n at most 4; 0.40, 0.50, 0.65, 0.75, 0.85 for n of 5, 6, 7, 8, 9; 1.00 for n of 10 or more. Compute the capital charge in USD as the larger of the holding-period VaR and k times the 60-day average VaR; round only the final value half up to 2 decimal places.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `usd` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `undiversified_one_day_var` | Exact one-day VaR in USD ignoring diversification. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |
| `diversified_one_day_var` | One-day diversified VaR in USD. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 4}}` |
| `holding_period_var` | Diversified VaR in USD at the holding period. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 4}}` |
| `regulatory_multiplier` | Exact regulatory multiplier including add-on. | `{"type": "decimal", "unit": "multiple", "rounding": {"mode": "exact"}}` |

**Parameters:** `V` 500000..5000000 step 50000; `W1` 30..70 step 5; `S1` 0.8..2.5 step 0.1; `S2` 0.8..2.5 step 0.1; `RHO` -0.4..0.8 step 0.1; `Z` one of ['1.645', '2.054', '2.326']; `H` 1..10 step 1; `A` 1.0..5.0 step 0.25; `N` 0..12 step 1

**Program:**

```python
def solve():
    V = Q(P["V"])
    w1 = Q(P["W1"]) / 100
    w2 = 1 - w1
    s1 = Q(P["S1"]) / 100
    s2 = Q(P["S2"]) / 100
    rho = Q(P["RHO"])
    z = Q(P["Z"])
    h = P["H"]
    a = Q(P["A"]) / 100
    n = P["N"]
    undiv = V * z * (w1 * s1 + w2 * s2)
    var_p = (w1 * s1) ** 2 + (w2 * s2) ** 2 + 2 * rho * w1 * w2 * s1 * s2
    if var_p <= 0:
        raise ValueError("non-positive portfolio variance")
    sig = sqrt(var_p)
    div1 = V * z * sig
    varh = div1 * sqrt(h)
    addons = {5: Q("0.40"), 6: Q("0.50"), 7: Q("0.65"), 8: Q("0.75"), 9: Q("0.85")}
    if n <= 4:
        addon = Q(0)
    elif n >= 10:
        addon = Q(1)
    else:
        addon = addons[n]
    k = 3 + addon
    avg = V * a
    final = max(varh, k * avg)
    return {
        "final": final,
        "undiversified_one_day_var": undiv,
        "diversified_one_day_var": div1,
        "holding_period_var": varh,
        "regulatory_multiplier": k,
    }
```

**Gold for every instance:**

| Seed | Parameters | Final | undiversified_one_day_var | diversified_one_day_var | holding_period_var | regulatory_multiplier |
|---|---|---|---|---|---|---|
| 0 | A=2, H=4, N=4, RHO=-0.2, S1=2, S2=1.9, V=2400000, W1=40, Z=1.645 | 144000.00 | 76591.2 | 49543.8608 | 99087.7217 | 3 |
| 1 | A=3.25, H=8, N=5, RHO=0.4, S1=2.1, S2=2.1, V=600000, W1=45, Z=2.054 | 66300.00 | 25880.4 | 21699.4460 | 61375.3018 | 3.4 |
| 2 | A=3.5, H=4, N=8, RHO=-0.1, S1=1.3, S2=1.4, V=2000000, W1=45, Z=2.326 | 262500.00 | 63034.6 | 42763.8753 | 85527.7506 | 3.75 |
| 3 | A=4.25, H=8, N=2, RHO=0.3, S1=0.9, S2=0.8, V=3600000, W1=45, Z=2.326 | 459000.00 | 70756.92 | 57072.3961 | 161425.1132 | 3 |
| 4 | A=4.75, H=6, N=12, RHO=0.6, S1=1.8, S2=1.6, V=3700000, W1=40, Z=2.326 | 703000.00 | 144584.16 | 129649.4823 | 317575.0772 | 4 |
| 5 | A=2.5, H=2, N=10, RHO=0.3, S1=1.6, S2=1.9, V=1850000, W1=40, Z=2.326 | 185000.00 | 76595.18 | 63051.2085 | 89167.8742 | 4 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 10/10 fields, all fields agree.

**Decision:** _pending_

---

## 24. investment_analysis / npv (basic)

`syn.fable.investment_analysis.npv.npv_level_annuity_outlay.basic.v1`

Authored by claude-fable-5-1 (effort high) in 1 attempt(s).

**Question (seed 0):**

> A project requires an initial outlay of USD 9750 at time zero and returns a level cash flow of USD 810 at the end of each year for 6 years, with no salvage. The annual discount rate is r=7 percent, compounded annually. Compute the NPV as the present value of the level cash flows minus the initial outlay. Use exact arithmetic throughout.
> 
> Answer format: use exact arithmetic through all intermediate steps, round only the final value half up to 2 decimal digits, and return only the numeric value interpreted in `usd` with no unit label or additional text.

**Final answer spec:** `{"type": "decimal", "unit": "usd", "rounding": {"mode": "half_up", "decimal_places": 2}}`

| Slot | Description | Spec |
|---|---|---|
| `annuity_factor_trace` | Exact present value factor of the level annuity. | `{"type": "decimal", "unit": "ratio", "rounding": {"mode": "exact"}}` |
| `annuity_pv_trace` | Present value of all level cash flows. | `{"type": "decimal", "unit": "usd", "rounding": {"mode": "exact"}}` |

**Parameters:** `I0` 2000..12000 step 50; `C` 400..2500 step 10; `N` 3..8 step 1; `R` 2.0..12.0 step 0.5

**Program:**

```python
def solve():
    I0 = P["I0"]
    C = P["C"]
    n = P["N"]
    r = Fraction(P["R"]) / 100
    if r <= 0:
        raise ValueError("rate must be positive")
    growth = (1 + r) ** n
    af = (1 - 1 / growth) / r
    pv = C * af
    npv = pv - I0
    return {"final": npv, "annuity_factor_trace": af, "annuity_pv_trace": pv}
```

**Gold for every instance:**

| Seed | Parameters | Final | annuity_factor_trace | annuity_pv_trace |
|---|---|---|---|---|
| 0 | C=810, I0=9750, N=6, R=7 | -5889.10 | 7153290740700/1500730351849 | 5794165499967000/1500730351849 |
| 1 | C=2430, I0=4550, N=8, R=8 | 9414.33 | 1623020573200/282429536481 | 16230205732000/1162261467 |
| 2 | C=1110, I0=3300, N=3, R=7.5 | -413.42 | 206760/79507 | 229503600/79507 |
| 3 | C=2000, I0=2100, N=3, R=7 | 3148.63 | 3214900/1225043 | 6429800000/1225043 |
| 4 | C=1110, I0=10150, N=7, R=9 | -4563.42 | 920043467574100/182803912081669 | 1021248249007251000/182803912081669 |
| 5 | C=2160, I0=6950, N=5, R=10.5 | 1134.57 | 1973171096200/527182965101 | 4262049567792000/527182965101 |

**Blind cross-check** (claude-fable-5-1, 2 instances): 6/6 fields, all fields agree.

**Decision:** _pending_

---

