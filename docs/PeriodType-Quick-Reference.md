# PeriodType Quick Reference

**FEAT-003: PeriodType Enum for EdgarTools**  
Enhanced developer experience through IDE autocomplete and parameter validation for financial reporting periods.

## 📋 Available Period Types

| Enum Value | String Value | Description | Use Case |
|------------|-------------|-------------|----------|
| `PeriodType.ANNUAL` | `"annual"` | Annual reporting periods | Full fiscal year financial data |
| `PeriodType.QUARTERLY` | `"quarterly"` | Quarterly reporting periods | 3-month period financial data |
| `PeriodType.MONTHLY` | `"monthly"` | Monthly reporting periods | Monthly financial data (rare) |
| `PeriodType.TTM` | `"ttm"` | Trailing Twelve Months | Rolling 12-month performance |
| `PeriodType.YTD` | `"ytd"` | Year to Date | Current year performance |

### Convenience Aliases
| Alias | Same As | Notes |
|-------|---------|--------|
| `PeriodType.YEARLY` | `PeriodType.ANNUAL` | Alternative naming |
| `PeriodType.QUARTER` | `PeriodType.QUARTERLY` | Shorter form |

## 🚀 Basic Usage

### Import
```python
from edgar.enums import PeriodType, PeriodInput, validate_period_type
```

### Function Parameters (New Style)
```python
from edgar import Company
from edgar.enums import PeriodType

# Enhanced with autocomplete for financial statements
company = Company("AAPL")
facts = company.get_facts()

# Period filtering through statement methods
annual_income = facts.income_statement(annual=True)       # Annual periods
quarterly_income = facts.income_statement(annual=False)   # Quarterly periods

# Using query interface with PeriodType
annual_facts = facts.query().by_period_length(12).get()  # Annual (12 months)
quarterly_facts = facts.query().by_period_length(3).get() # Quarterly (3 months)
```

### Backwards Compatibility (Existing Style)
```python
# Still works - no breaking changes
from edgar import Company

company = Company("AAPL")
facts = company.get_facts()
annual_income = facts.income_statement(annual=True)
quarterly_income = facts.income_statement(annual=False)
```

## 🛡️ Enhanced Validation

### Smart Error Messages
```python
from edgar.enums import validate_period_type

# Typo detection
try:
    validate_period_type("anual")  # misspelled
except ValueError as e:
    print(e)  # Error: "Invalid period type 'anual'. Did you mean: annual?"

# Invalid input
try:
    validate_period_type("invalid")
except ValueError as e:
    print(e)  # Error: "Invalid period type 'invalid'. Use PeriodType enum for autocomplete..."
```

## 🔧 Function Integration

### Type Hints
```python
from edgar.enums import PeriodInput, PeriodType, validate_period_type

def analyze_financials(ticker: str, period: PeriodInput = PeriodType.ANNUAL) -> str:
    """Function with PeriodType parameter."""
    validated_period = validate_period_type(period)
    return f"Analyzing {ticker} {validated_period} financials"

# Usage
result1 = analyze_financials("AAPL", PeriodType.QUARTERLY)  # IDE autocomplete
result2 = analyze_financials("MSFT", "ttm")                 # String still works
```

### Migration from Boolean Annual
```python
from edgar.enums import PeriodInput, PeriodType, validate_period_type

# Old pattern
def old_style(annual: bool = True) -> str:
    period = "annual" if annual else "quarterly"
    return f"Getting {period} data"

# New pattern - more expressive
def new_style(period: PeriodInput = PeriodType.ANNUAL) -> str:
    period_str = validate_period_type(period)
    return f"Getting {period_str} data"

# Benefits:
# ✅ Support for TTM, YTD, monthly (not just annual/quarterly)
# ✅ IDE autocomplete 
# ✅ Validation prevents typos
# ✅ Self-documenting code
```

## 📚 Convenience Collections

```python
from edgar.enums import STANDARD_PERIODS, SPECIAL_PERIODS, ALL_PERIODS

# Most common periods
for period in STANDARD_PERIODS:
    print(f"Standard: {period}")  # ANNUAL, QUARTERLY

# Special analysis periods  
for period in SPECIAL_PERIODS:
    print(f"Special: {period}")   # TTM, YTD

# All available periods
for period in ALL_PERIODS:
    print(f"Available: {period}") # All 5 period types
```

## 🌍 Real-World Examples

### Financial Analysis
```python
from edgar.enums import PeriodInput

def compare_performance(ticker: str, periods: list[PeriodInput]) -> dict:
    """Compare company performance across different periods."""
    from edgar import Company
    from edgar.enums import validate_period_type

    company = Company(ticker)
    facts = company.get_facts()
    results = {}

    for period in periods:
        period_str = validate_period_type(period)
        data = None  # Initialize data variable

        if period_str == "annual":
            data = facts.income_statement(annual=True, periods=1)
        elif period_str == "quarterly":
            data = facts.income_statement(annual=False, periods=1)
        elif period_str == "ttm":
            # Get last 4 quarters for TTM calculation
            data = facts.income_statement(annual=False, periods=4)

        if data is not None:
            results[period_str] = data

    return results

# Usage with mixed types
from edgar.enums import PeriodType

analysis = compare_performance("AAPL", [
    PeriodType.ANNUAL,    # Enum
    "quarterly",          # String
    PeriodType.TTM        # Enum
])
```

### Batch Processing
```python
from edgar.enums import PeriodInput, PeriodType

def process_companies(tickers: list[str],
                     period: PeriodInput = PeriodType.QUARTERLY) -> dict:
    """Process multiple companies for specified period."""
    from edgar import Company
    from edgar.enums import validate_period_type

    period_str = validate_period_type(period)
    results = {}

    for ticker in tickers:
        company = Company(ticker)
        facts = company.get_facts()
        statement = None  # Initialize statement variable

        if period_str == "annual":
            statement = facts.income_statement(annual=True, periods=1)
        elif period_str == "quarterly":
            statement = facts.income_statement(annual=False, periods=1)

        if statement is not None:
            results[ticker] = statement

    return results

# Usage
from edgar.enums import PeriodType

tech_stocks = ["AAPL", "MSFT", "GOOGL"]
result = process_companies(tech_stocks, PeriodType.QUARTERLY)
```

### Period Iteration
```python
def comprehensive_analysis(ticker: str) -> dict:
    """Analyze company across all standard periods."""
    from edgar import Company
    from edgar.enums import STANDARD_PERIODS

    company = Company(ticker)
    facts = company.get_facts()
    results = {}

    for period in STANDARD_PERIODS:
        # Each period provides IDE autocomplete when used
        statement = None  # Initialize statement variable

        if period.value == "annual":
            statement = facts.income_statement(annual=True, periods=2)
        elif period.value == "quarterly":
            statement = facts.income_statement(annual=False, periods=4)

        if statement is not None:
            results[period.value] = statement

    return results
```

## 💡 IDE Benefits

With PeriodType, your IDE will provide:

### Autocomplete
When you type `PeriodType.`, your IDE shows:
```
PeriodType.ANNUAL     # 'annual' - Full fiscal year
PeriodType.QUARTERLY  # 'quarterly' - 3-month periods  
PeriodType.MONTHLY    # 'monthly' - Monthly periods
PeriodType.TTM        # 'ttm' - Trailing twelve months
PeriodType.YTD        # 'ytd' - Year to date
```

### Documentation
Hover over enum values to see descriptions:
- **ANNUAL**: Annual reporting periods (full fiscal year)
- **QUARTERLY**: Quarterly reporting periods (3-month periods)
- **TTM**: Trailing Twelve Months for rolling performance analysis

### Type Safety
Your IDE will warn about:
- Invalid period types
- Wrong parameter types
- Potential typos before runtime

## 🔄 Migration Guide

### From Boolean Annual Parameter

**Before:**
```python
# Limited to annual/quarterly only
from edgar import Company

company = Company("AAPL")
facts = company.get_facts()
annual_income = facts.income_statement(annual=True)    # Annual data
quarterly_income = facts.income_statement(annual=False)   # Quarterly data
```

**After:**
```python
# Rich period support with enhanced querying
from edgar import Company

company = Company("AAPL")
facts = company.get_facts()

# Financial statement methods with boolean parameters
annual_income = facts.income_statement(annual=True)     # Annual
quarterly_income = facts.income_statement(annual=False) # Quarterly

# Advanced period filtering with query interface
ttm_facts = facts.query().by_period_length(12).get()   # Trailing twelve months
quarterly_facts = facts.query().by_period_length(3).get() # Quarterly periods

# Individual fact retrieval with period specification
revenue_2023 = facts.get_fact("Revenue", period="2023-FY")
revenue_q4 = facts.get_fact("Revenue", period="2023-Q4")
```

### From String Parameters

**Before:**
```python
# Typo-prone, no autocomplete
def analyze_data(period: str) -> str:
    return f"Analyzing {period} data"

analyze_data("annual")     # Could typo as "anual"
analyze_data("quarterly")  # Could typo as "quartly"
```

**After:**
```python
# Autocomplete prevents typos
from edgar.enums import PeriodType, PeriodInput, validate_period_type

def analyze_data(period: PeriodInput) -> str:
    validated_period = validate_period_type(period)
    return f"Analyzing {validated_period} data"

analyze_data(PeriodType.ANNUAL)     # IDE autocomplete
analyze_data(PeriodType.QUARTERLY)  # IDE autocomplete

# Strings still work with validation
analyze_data("annual")     # Validated, helpful errors if typo
```

## ⚖️ Consistency with FormType

PeriodType follows the same design pattern as FormType:

| Feature | FormType | PeriodType |
|---------|----------|------------|
| **Enum Type** | `StrEnum` | `StrEnum` |
| **Validation** | `validate_form_type()` | `validate_period_type()` |
| **Type Hints** | `FormInput` | `PeriodInput` |
| **Collections** | `PERIODIC_FORMS`, etc. | `STANDARD_PERIODS`, etc. |
| **Error Handling** | Smart suggestions | Smart suggestions |
| **Backwards Compat** | ✅ Union types | ✅ Union types |

## 🎯 Best Practices

### 1. Use Enums for New Code
```python
# Recommended: Enhanced developer experience
from edgar.enums import PeriodInput, PeriodType

def analyze_trends(period: PeriodInput = PeriodType.ANNUAL) -> str:
    return f"Analyzing trends for {period}"
```

### 2. Maintain String Compatibility
```python
# Support both for flexibility
from edgar.enums import PeriodInput, validate_period_type

def flexible_function(period: PeriodInput) -> str:
    validated = validate_period_type(period)  # Handles both
    return f"Processing {validated} data"
```

### 3. Leverage Collections
```python
# Use predefined collections
from edgar.enums import STANDARD_PERIODS

def process_period(period_type):
    return f"Processing {period_type}"

for period in STANDARD_PERIODS:
    result = process_period(period)
    print(result)
```

### 4. Provide Good Defaults
```python
# Use meaningful defaults
from edgar.enums import PeriodInput, PeriodType

def get_financials(period: PeriodInput = PeriodType.ANNUAL) -> str:
    """Default to annual for most financial analysis."""
    return f"Getting {period} financials"
```

## 🚦 Error Handling

### Common Errors and Solutions

```python
from edgar.enums import validate_period_type, PeriodType

# Typo in string
try:
    validate_period_type("anual")
except ValueError as e:
    print(e)  # "Did you mean: annual?"

# Wrong type
try:
    validate_period_type("123")  # Use string instead of int
except ValueError as e:
    print(e)  # "Invalid period type '123'..."

# Completely invalid
try:
    validate_period_type("invalid")
except ValueError as e:
    print(e)  # "Use PeriodType enum for autocomplete..."
```

---

## 📈 Impact Summary

**FEAT-003 delivers on EdgarTools principles:**

- ✅ **Simple yet powerful**: Easy enum usage with rich functionality
- ✅ **Beginner-friendly**: IDE autocomplete helps discovery
- ✅ **Joyful UX**: Prevents typos, provides helpful errors
- ✅ **Accurate financials**: Validation ensures correct period specification

**Key improvements:**
- 🎯 IDE autocomplete for period types
- 🛡️ Enhanced validation with smart error messages  
- 🔧 Seamless integration with existing API
- 🔄 Clear migration path from boolean parameters
- ⚖️ Consistent design with FormType enum