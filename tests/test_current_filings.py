
from edgar.current_filings import get_current_filings, parse_summary, CurrentFilings, get_all_current_filings
from edgar import get_all_current_filings, Filings, iter_current_filings_pages
import datetime
import pytest
from edgar import get_by_accession_number

@pytest.mark.network
def test_get_current_entries():
    print()
    filings = get_current_filings()
    print(filings)
    print(filings.to_pandas())
    # previous should be None
    assert filings.previous() is None

    next_filings = filings.next()
    assert next_filings is not None
    print(next_filings)
    previous_filings = next_filings.previous()
    print(previous_filings)
    assert previous_filings.previous() is None

@pytest.mark.network
def test_get_current_filings_by_form():
    form='4'
    filings:CurrentFilings = get_current_filings(form=form)

    # Check that all filings are start with 4. This matches the behavior of the SEC website

    for i in range(4):
        filings = filings.next()
        if not filings:
            break
        assert all(f.startswith(form) for f in set(filings.data['form'].to_pylist()))

@pytest.mark.network
def test_current_filings_to_pandas():
    filings:CurrentFilings = get_current_filings()
    filing_pandas = filings.to_pandas()
    assert filings[0].accession_no == filing_pandas['accession_number'][0]
    accession_number_on_page0 = filings[0].accession_no

    # Get the next page
    filings_page2 = filings.next()
    filing_page2_pandas = filings_page2.to_pandas()
    assert filing_page2_pandas is not None
    #assert filings_page2[0].accession_no == filing_page2_pandas['accession_number'][0]
    #accession_number_on_page1 = filings_page2[0].accession_no
    #assert accession_number_on_page0 != accession_number_on_page1

@pytest.mark.network
def test_current_filings_get_by_index_on_page1():
    print()
    filings: CurrentFilings = get_current_filings()
    filing = filings.get(20)
    assert filing
    assert filings[20]

    # Find the filing on page2
    filing_page2 = filings.next()
    print(filing_page2)

@pytest.mark.network
def test_current_filings_get_by_index_on_page2():
    filings: CurrentFilings = get_current_filings()
    # Find the filing on page2
    filing_page2 = filings.next()
    print(filing_page2)
    # Get the first filing on page2 which should be index 40
    filing = filing_page2.get(40)
    # Get the first row of the data
    accession_number = filing_page2.data['accession_number'].to_pylist()[0]
    assert filing
    assert filing.accession_no == accession_number
    assert filing_page2[79]

    with pytest.raises(IndexError):
        # The boundary is 80 - should raise IndexError for out of bounds
        filing_page2[80]

@pytest.mark.network
def test_current_filings_get_accession_number():
    filings:CurrentFilings = get_current_filings()
    filings = filings.next()
    accession_number = filings.data['accession_number'].to_pylist()[0]
    print(accession_number)
    filings = filings.previous()
    filing = filings.get(accession_number)
    assert filing
    assert filing.accession_no == accession_number

@pytest.mark.network
@pytest.mark.slow
def test_current_filings_get_accession_number_not_found():
    filings:CurrentFilings = get_current_filings().next()
    accession_number = '0000000900-24-000000'
    filings = filings.previous()
    filing = filings.get(accession_number)
    assert not filing

@pytest.mark.network
def test_parse_summary():
    summary1 = '<b>Filed:</b> 2023-09-13 <b>AccNo:</b> 0001714174-23-000114 <b>Size:</b> 668 KB'

    filing_date, accession_number = parse_summary(summary1)
    assert (filing_date, accession_number) == (datetime.date(2023, 9, 13), '0001714174-23-000114')

    summary2 = '<b>Film#:</b> 23003229  <b>Filed:</b> 2023-08-17 <b>AccNo:</b> 9999999997-23-004141 <b>Size:</b> 1 KB'
    assert parse_summary(summary2) == (datetime.date(2023, 8, 17), '9999999997-23-004141')

@pytest.mark.network
def test_current_filings_with_no_results():

    filings = get_current_filings(form='4000')
    assert filings.empty
    assert isinstance(filings, CurrentFilings)
    assert filings.start_date is None
    assert filings.end_date is None

@pytest.mark.network
def test_get_current_filing_by_accession_number():
    current_filings = get_current_filings()
    print()
    print(current_filings)
    filing = current_filings[0]
    # Now find the filing
    filing = get_by_accession_number(filing.accession_no)
    assert filing
    assert filing.accession_no == current_filings[0].accession_no

    # Now find a filing that is on the next page
    current_filings = current_filings.next()
    filing_on_next_page = current_filings[40]
    print(filing_on_next_page)

@pytest.mark.network
def test_get_all_current_filings():
    all_filings = get_all_current_filings()
    assert isinstance(all_filings, Filings)
    assert len(all_filings) > 100

@pytest.mark.network
def test_iter_current_filings_pages():
    filings = next(iter_current_filings_pages())
    assert filings
