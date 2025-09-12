import datetime
import time
from datetime import datetime

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pytest
from freezegun import freeze_time
from rich.table import Table

import edgar
from edgar.dates import extract_dates, InvalidDateException
from edgar.formatting import display_size, reverse_name, split_camel_case
from edgar.core import (decode_content,
                        get_identity,
                        set_identity,
                        ask_for_identity,
                        Result,
                        CRAWL, CAUTION,
                        get_bool,
                        is_start_of_quarter,
                        has_html_content,

                        parallel_thread_map)
from edgar.filtering import (
    filter_by_form,
    filter_by_cik,
    filter_by_accession_number,
    filter_by_ticker,
    filter_by_date
)
from edgar.richtools import *

from edgar.httpclient import get_http_params

def client_headers():
    return get_http_params()["headers"]

@pytest.mark.fast
def test_decode_content():
    text = "Kyle Walker vs Mbappe"
    assert decode_content(text.encode('utf-8')) == text
    assert decode_content(text.encode('latin-1')) == text

@pytest.mark.fast
def test_decode_latin1():
    text = "Mbappe vs Messi"
    assert decode_content(text.encode("latin-1")) == text

@pytest.mark.fast
def test_get_identity():
    identity = get_identity()
    assert identity

@pytest.mark.fast
def test_get_identity_environment_variable_not_set(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda: "Tom Holland tholland@restishistory.com")
    monkeypatch.delenv("EDGAR_IDENTITY", raising=False)
    identity = get_identity()
    assert identity == "Tom Holland tholland@restishistory.com"

@pytest.mark.fast
def test_set_identity():
    old_identity = get_identity()
    set_identity("Mike Tirico mtirico@cal.com")
    assert get_identity() == "Mike Tirico mtirico@cal.com"
    set_identity(old_identity)

@pytest.mark.fast
def test_ask_for_identity(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda: "Tom Holland tholland@restishistory.com")
    identity = ask_for_identity()
    assert identity == "Tom Holland tholland@restishistory.com"

@pytest.mark.fast
def test_ask_for_identity_prompt(monkeypatch, capsys):
    monkeypatch.setattr('builtins.input', lambda: "Tom Holland tholland@restishistory.com")
    identity = ask_for_identity("Who are you")
    assert identity == "Tom Holland tholland@restishistory.com"
    captured = capsys.readouterr()
    assert 'Who are you' in captured.out

@pytest.mark.fast
def test_ask_for_identity_keyboard_interrupt(monkeypatch):
    def input_interrupt():
        raise KeyboardInterrupt()

    monkeypatch.setattr('builtins.input', input_interrupt)
    with pytest.raises(TimeoutError) as exc:
        ask_for_identity("Who are you")

@pytest.mark.fast
def test_get_header():
    assert client_headers()['User-Agent'] == get_identity()

@pytest.mark.fast
def test_df_to_rich_table():
    df = pd.read_csv('data/cereal.csv')
    table: Table = df_to_rich_table(df)
    assert table
    assert len(table.rows) == 21

@pytest.mark.fast
def test_repr_rich():
    df = pd.read_csv('data/cereal.csv',
                     usecols=['name', 'mfr', 'type', 'calories', 'protein', 'fat', 'sodium'])
    table: Table = df_to_rich_table(df)
    value = repr_rich(table)
    assert '100% Bran' in value

@pytest.mark.fast
def test_result():
    result = Result.Ok(value=1)
    assert result.success
    assert not result.failure
    assert result.value == 1

    assert "Success" in str(result)

    result = Result.Fail("Does not work")
    assert result.failure
    assert not result.success
    assert not result.value
    assert result.error == "Does not work"
    assert "Failure" in str(result)

@pytest.mark.fast
def test_display_size():
    assert display_size(117000) == "114.3 KB"
    assert display_size(1170000) == "1.1 MB"
    assert display_size("117000") == "114.3 KB"
    assert display_size("1170000") == "1.1 MB"
    assert display_size(None) == ""
    assert display_size("aaa") == ""
    assert display_size("\x01") == ""


def date(s):
    return datetime.strptime(s, "%Y-%m-%d")


def date_now():
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

@pytest.mark.fast
def test_extract_dates():
    # Basic valid cases
    assert extract_dates("2022-03-04") == (date("2022-03-04"), None, False)
    assert extract_dates("2022-03-04:") == (date("2022-03-04"), date_now(), True)
    assert extract_dates(":2022-03-04") == (date('1994-07-01'), date("2022-03-04"), True)
    assert extract_dates("2022-03-04:2022-04-04") == (date("2022-03-04"), date("2022-04-04"), True)

    # Valid edge cases
    assert extract_dates("2024-02-29") == (date("2024-02-29"), None, False)  # Leap year
    assert extract_dates("2022-03-04:2022-03-04") == (date("2022-03-04"), date("2022-03-04"), True)  # Same date range
    assert extract_dates("1994-07-01") == (date("1994-07-01"), None, False)  # Earliest allowed date

    # Invalid dates - should all raise InvalidDateException
    invalid_cases = [
        # Empty/None input
        "",

        # Invalid separators
        "2022-03-04::",
        "::",
        "::2022-03-04",
        "2022-03-04/2022-04-04",
        "2022-03-04;2022-04-04",

        # Incomplete dates
        "2022",
        "2022-03",
        "2022-03-",
        "-03-04",
        "2022--04",
        "2022-03-",
        ":2022-03-04:",

        # Invalid date components
        "2022-00-04",  # month 0
        "2022-13-04",  # month 13
        "2022-12-00",  # day 0
        "2022-12-32",  # day 32
        "2022-04-31",  # invalid day for April
        "2023-02-29",  # non-leap year February
        "0000-03-04",  # year 0

        # Wrong format
        "03-04-2022",
        "2022.03.04",
        "20220304",
        "2022/03/04",

        # Invalid characters
        "2022-O3-04",  # letter O instead of zero
        "2022-03-O4",
        "YYYY-MM-DD",
        # "2022-3-4",  # missing leading zeros
        "22-03-04",  # 2-digit year

        # Whitespace issues
        " 2022-03-04",
        "2022-03-04 ",
        "2022-03-04: 2022-04-04",
        # "2022-03-04 : 2022-04-04",

        # Date range order issues
        "2022-03-04:2022-02-04",  # end before start

        # Multiple colons
        "2022-03-04:2022-04-04:2022-05-04",

        # Mixed valid/invalid
        "2022-03-04:2022-13-04",  # valid start, invalid end
        ":2022-13-04",  # invalid end date
        "2022-13-04:",  # invalid start date

        # Special characters
        "2022-03-04\n",
        "2022-03-04\t",
        "\n2022-03-04",
    ]

    for invalid_case in invalid_cases:
        print(invalid_case)
        with pytest.raises(InvalidDateException):
            extract_dates(invalid_case)

    # Specific error message tests
    try:
        extract_dates("bad")
    except InvalidDateException as e:
        assert "YYYY-MM-DD" in str(e)
        assert "2022-10-27" in str(e)  # Example date in error message

@pytest.mark.fast
def test_invalid_date_exception():
    exception = InvalidDateException("Something went wrong")
    assert str(exception) == "Something went wrong"

@pytest.mark.fast
def test_filter_by_date():
    arrays = [pa.array(['a', 'b', 'c']),
              pa.array([3, 2, 1]),
              pc.cast(pc.strptime(pa.array(['2013-04-24', '2015-12-03', '2017-08-10']), '%Y-%m-%d', 'us'), pa.date32())]

    # arrays[2] = pc.cast(pc.strptime(arrays[2], '%Y-%m-%d', 'us'), pa.date32())
    table = pa.Table.from_arrays(arrays,
                                 names=['item', 'value', 'date']
                                 )

    assert len(filter_by_date(table, '2013-04-24', 'date')) == 1
    assert len(filter_by_date(table, '2013-04-24:2016-04-24', 'date')) == 2

    # Use datetime to filter by date
    assert len(filter_by_date(table, datetime.strptime('2013-04-24', '%Y-%m-%d'), 'date')) == 1

@pytest.mark.fast
def test_filter_by_form():
    arrays = [pa.array(['a', 'b', 'c', 'd']),
              pa.array([3, 2, 1, 4]),
              pa.array(['10-K', '10-Q', '10-K', '10-K/A'])]

    table = pa.Table.from_arrays(arrays, names=['item', 'value', 'form'])

    assert len(filter_by_form(table, '10-K', )) == 3
    assert len(filter_by_form(table, ['10-K', '10-Q'], )) == 4

    # Amendments false
    assert len(filter_by_form(table, form='10-K', amendments=False)) == 2

    assert len(filter_by_form(table, form=['10-K', '10-Q', '10-K/A'], amendments=False)) == 3
    assert len(filter_by_form(table, form=['10-K', '10-Q', '10-K/A'], amendments=True)) == 4

@pytest.mark.fast
def test_filter_by_accession_number():
    arrays = [pa.array(['a', 'b', 'c', 'd', 'e']),
              pa.array([3, 2, 1, 4, 4]),
              pa.array(['10-K', '10-Q', '10-K', '10-K/A', '4-K']),
              pa.array([3, 2, 1, 4, 4])
              ]

    table = pa.Table.from_arrays(arrays, names=['item', 'value', 'form', 'accession_number'])

    assert len(filter_by_accession_number(table, 1)) == 1
    assert len(filter_by_accession_number(table, [3, 4], )) == 3
    assert len(filter_by_accession_number(table, ['3', 4], )) == 3
    assert len(filter_by_accession_number(table, ['3'], )) == 1

@pytest.mark.fast
def test_filter_by_cik():
    arrays = [pa.array(['a', 'b', 'c', 'd', 'e']),
              pa.array([3, 2, 1, 4, 4]),
              pa.array(['10-K', '10-Q', '10-K', '10-K/A', '4-K']),
              pa.array([3, 2, 1, 4, 4])
              ]

    table = pa.Table.from_arrays(arrays, names=['item', 'value', 'form', 'cik'])

    assert len(filter_by_cik(table, 1)) == 1
    assert len(filter_by_cik(table, [3, 4], )) == 3
    assert len(filter_by_cik(table, ['3', 4], )) == 3
    assert len(filter_by_cik(table, ['3'], )) == 1

@pytest.mark.fast
def test_filter_by_ticker():
    arrays = [pa.array(['a', 'b', 'c', 'd', 'e']),
              pa.array([3, 2, 1, 4, 4]),
              pa.array(['10-K', '10-Q', '10-K', '10-K/A', '4-K']),
              pa.array([1318605, 320193, 1341439, 789019, 789019]),
              pa.array(['TSLA', 'AAPL', 'ORCL', 'MSFT', 'MSFT'])
              ]

    table = pa.Table.from_arrays(arrays, names=['item', 'value', 'form', 'cik', 'ticker'])
    assert len(filter_by_ticker(table, 'TSLA')) == 1
    assert len(filter_by_ticker(table, 'MSFT')) == 2
    assert len(filter_by_ticker(table, 'ORCL')) == 1
    assert len(filter_by_ticker(table, 'PD')) == 0

@pytest.mark.fast
def test_dataframe_pager():
    from edgar.core import DataPager
    import numpy as np
    df = pd.DataFrame({'A': np.random.randint(0, 100, size=150),
                       'B': np.random.randint(0, 100, size=150)})
    pager = DataPager(df, 100)
    # Test getting the first page
    first_page = pager.current()
    assert len(first_page) == 100

    """ 

    # Test getting the next page
    second_page = pager.next()
    assert len(second_page) == 50
    assert all(first_page.iloc[-1] != second_page.iloc[0])

    # Test getting the previous page
    prev_page = pager.previous()
    assert len(prev_page) == 100
    assert all(first_page == prev_page)

    # Test going to the next page again
    next_page = pager.next()
    assert len(next_page) == 50
    assert all(second_page == next_page)

    # Test going to the next page when there is no more page
    last_page = pager.next()
    assert last_page is None
    """

@pytest.mark.fast
def test_settings():
    assert edgar.edgar_mode.max_connections == 10

    edgar.edgar_mode = CAUTION
    assert edgar.edgar_mode.max_connections == 5

    edgar.edgar_mode = CRAWL
    assert edgar.edgar_mode.max_connections == 2

@pytest.mark.fast
def test_reverse_name():
    assert reverse_name('WALKER KYLE') == 'Kyle Walker'
    assert reverse_name('KONDO CHRIS') == 'Chris Kondo'
    assert reverse_name('KONDO CHRIS Jr') == 'Chris Kondo Jr'
    assert reverse_name('KONDO CHRIS Jr.') == 'Chris Kondo Jr.'
    assert reverse_name('KONDO CHRIS Jr ET AL') == 'Chris Kondo Jr ET AL'
    assert reverse_name('KONDO CHRIS Jr et al') == 'Chris Kondo Jr et al'
    assert reverse_name('KONDO CHRIS Jr et al.') == 'Chris Kondo Jr et al.'
    assert reverse_name('JAMES HAMILTON E') == 'Hamilton E James'
    assert reverse_name('BURNS BENJAMIN MICHAEL') == 'Benjamin Michael Burns'
    assert reverse_name('FROST PHILLIP MD') == 'Phillip Frost MD'
    assert reverse_name('FROST PHILLIP MD ET AL') == 'Phillip Frost MD ET AL'
    assert reverse_name("Borninkhof K. Michelle") == "Michelle K. Borninkhof"
    assert reverse_name("Bennett C Frank") == "Frank C Bennett"
    assert reverse_name("Frank Thomas AJ") == "Thomas AJ Frank"

    assert reverse_name("FOSTER WATT R JR") == "Watt R Foster JR"
    # Single word name
    assert reverse_name("WATT") == "Watt"
    # O'Names
    assert reverse_name("O'CONNELL BENJAMIN") == "Benjamin O'Connell"

@pytest.mark.fast
def test_get_bool():
    assert get_bool(1)
    assert get_bool("1")
    assert get_bool("Y")
    assert get_bool("true")
    assert get_bool("TRUE")
    assert get_bool("True")

@pytest.mark.fast
def test_split_camel_case():
    assert split_camel_case("CoverPage") == "Cover Page"
    assert split_camel_case("CONSOLIDATEDBALANCESHEETS") == "CONSOLIDATEDBALANCESHEETS"
    assert split_camel_case("consolidatedbalancesheets") == "consolidatedbalancesheets"
    assert split_camel_case("SummaryofSignificantAccountingPolicies") == "Summaryof Significant Accounting Policies"
    assert split_camel_case("RoleStatementINCOMESTATEMENTS") == "Role Statement INCOMESTATEMENTS"

@pytest.mark.fast
@pytest.mark.parametrize("test_date, expected_result", [
    ("2024-01-01", True),  # New Year's Day (start of Q1)
    ("2024-01-02", True),  # First business day after New Year's
    ("2024-01-03", False),  # Second business day after New Year's
    ("2024-03-31", False),  # Last day of Q1
    ("2024-04-01", True),  # First day of Q2
    ("2024-04-02", True),  # Possibly first business day of Q2
    ("2024-04-03", False),  # Second business day of Q2
    ("2024-07-01", True),  # First day of Q3
    ("2024-07-02", True),  # Possibly first business day of Q3
    ("2024-07-03", False),  # Second business day of Q3
    ("2024-10-01", True),  # First day of Q4
    ("2024-10-02", True),  # Possibly first business day of Q4
    ("2024-10-03", False),  # Second business day of Q4
    ("2024-12-31", False),  # Last day of Q4
    ("2024-05-15", False),  # Random day in middle of quarter
])

@pytest.mark.fast
def test_is_start_of_quarter(test_date, expected_result):
    with freeze_time(test_date):
        assert is_start_of_quarter() == expected_result

@pytest.mark.fast
@pytest.mark.parametrize("test_datetime, expected_result", [
    ("2024-01-01 00:00:01", True),  # Just after midnight on New Year's
    ("2024-01-02 23:59:59", True),  # Just before midnight on Jan 2
    ("2024-01-03 00:00:01", False),  # Just after midnight on Jan 3
    ("2024-04-01 12:00:00", True),  # Noon on first day of Q2
    ("2024-07-01 18:30:00", True),  # Evening on first day of Q3
    ("2024-10-02 09:00:00", True),  # Morning of possibly first business day of Q4
])
def test_is_start_of_quarter_with_time(test_datetime, expected_result):
    with freeze_time(test_datetime):
        assert is_start_of_quarter() == expected_result

@pytest.mark.fast
def test_has_html_content():
    assert has_html_content(
        """
        <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<title>SEC FORM 
        """
    )

    assert has_html_content(
        """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns:m1="http://www.sec.gov/edgar/rega/oneafiler" xmlns:ns1="http://www.sec.gov/edgar/common"  
        """
    )
    assert not has_html_content(
        """
        <?xml version="1.0"?>
<SEC-DOCUMENT>0001193125-23-048785.txt : 20230224
<SEC-HEADER>0001193125-23-048785.hdr.sgml : 20230224
<ACCEPTANCE-DATETIME>20230224163457
        """
    )

    assert has_html_content(
        """
        <?xml version=\'1.0\' encoding=\'ASCII\'?>\n<html xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:link="http://www.xbrl.org/2003/linkbase" 
        xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi" 
        xmlns:iso4217="http://www.xbrl.org/2003/iso4217" xmlns:srt="http://fasb.org/srt/2024" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" 
        """
    )

@pytest.mark.fast
def test_parallel_thread_map_basic():
    """Test basic functionality of parallel_thread_map"""

    # Simple squaring function
    def square(x):
        return x * x

    # Test with a list of integers
    numbers = [1, 2, 3, 4, 5]
    result = parallel_thread_map(square, numbers)

    # Check results
    assert result == [1, 4, 9, 16, 25]

@pytest.mark.fast
def test_parallel_thread_map_with_kwargs():
    """Test parallel_thread_map with keyword arguments"""

    # Function that multiplies by a factor
    def multiply(x, factor=1):
        return x * factor

    # Test with a list and a keyword argument
    numbers = [1, 2, 3, 4, 5]
    result = parallel_thread_map(multiply, numbers, factor=2)

    # Check results
    assert result == [2, 4, 6, 8, 10]

@pytest.mark.fast
def test_parallel_thread_map_empty_list():
    """Test parallel_thread_map with an empty list"""
    # Should return an empty list
    result = parallel_thread_map(lambda x: x * 2, [])
    assert result == []

@pytest.mark.fast
def test_parallel_thread_map_with_io_bound_task():
    """Test parallel_thread_map with an I/O-bound task"""

    # Function that simulates I/O with sleep
    def slow_operation(x, delay=0.01):
        time.sleep(delay)  # Simulate I/O delay
        return x * 2

    # Generate a list of test items
    items = list(range(10))

    # Time the parallel execution
    start_time = time.time()
    parallel_result = parallel_thread_map(slow_operation, items)
    parallel_time = time.time() - start_time

    # Time the sequential execution for comparison
    start_time = time.time()
    sequential_result = [slow_operation(x) for x in items]
    sequential_time = time.time() - start_time

    # Verify results are the same
    assert parallel_result == sequential_result

    # In properly working ThreadPoolExecutor, parallel should be faster
    # but don't assert on timing as it could be inconsistent in CI environments
    print(f"Parallel: {parallel_time:.4f}s, Sequential: {sequential_time:.4f}s")

@pytest.mark.fast
def test_parallel_thread_map_with_n_workers():
    """Test parallel_thread_map with a specific number of workers"""

    # Function that returns the current thread name
    def get_thread_info(x):
        import threading
        time.sleep(0.01)  # Small delay to ensure thread creation
        return threading.current_thread().name

    # Run with just 2 workers
    items = list(range(10))
    results = parallel_thread_map(get_thread_info, items, n_workers=2)

    # Count unique thread names (should be at most 2 + main thread)
    unique_threads = set(results)
    assert len(unique_threads) <= 3  # Main thread + 2 workers
