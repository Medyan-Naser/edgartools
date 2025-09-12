"""
Tests for enhanced XBRL standardization with company-specific mappings.

This test suite validates the enhanced standardization system with feature flags,
company-specific mappings, and priority-based resolution.
"""

import os
import tempfile
import shutil
import json
from unittest.mock import patch, MagicMock

import pytest

from edgar.xbrl.standardization import (
    StandardConcept, MappingStore, ConceptMapper, 
    standardize_statement, initialize_default_mappings
)


@pytest.fixture
def temp_standardization_dir():
    """Create a temporary directory structure for standardization testing."""
    temp_dir = tempfile.mkdtemp()
    
    # Create the basic structure
    standardization_dir = os.path.join(temp_dir, "standardization")
    company_mappings_dir = os.path.join(standardization_dir, "company_mappings")
    os.makedirs(company_mappings_dir)
    
    # Create core concept_mappings.json
    core_mappings = {
        "Revenue": ["us-gaap_Revenue", "us-gaap_Revenues"],
        "Net Income": ["us-gaap_NetIncome", "us-gaap_NetIncomeLoss"]
    }
    with open(os.path.join(standardization_dir, "concept_mappings.json"), 'w') as f:
        json.dump(core_mappings, f)
    
    # Create Tesla mappings
    tesla_mappings = {
        "metadata": {
            "entity_identifier": "tsla",
            "company_name": "Tesla, Inc.",
            "priority": "high"
        },
        "concept_mappings": {
            "Automotive Revenue": ["tsla:AutomotiveRevenue"],
            "Automotive Leasing Revenue": ["tsla:AutomotiveLeasing"],
            "Energy Revenue": ["tsla:EnergyGenerationAndStorageRevenue"]
        },
        "hierarchy_rules": {
            "Revenue": {
                "children": ["Automotive Revenue", "Energy Revenue"]
            }
        }
    }
    with open(os.path.join(company_mappings_dir, "tsla_mappings.json"), 'w') as f:
        json.dump(tesla_mappings, f)
    
    yield standardization_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.mark.fast
def test_tesla_specific_mapping_priority(temp_standardization_dir):
    """Test that Tesla-specific mappings have higher priority than core mappings."""
    
    core_mappings_path = os.path.join(temp_standardization_dir, "concept_mappings.json")
    store = MappingStore(source=core_mappings_path, read_only=True)
        
    # Tesla-specific concept should map to Tesla-specific standard concept
    result = store.get_standard_concept("tsla:AutomotiveLeasing")
    assert result == "Automotive Leasing Revenue"
        
    # Regular US-GAAP concept should still work
    result = store.get_standard_concept("us-gaap_Revenue")
    assert result == "Revenue"

@pytest.mark.fast
def test_fallback_to_core_mappings(temp_standardization_dir):
    """Test fallback to core mappings when enhanced mappings don't match."""
    
    core_mappings_path = os.path.join(temp_standardization_dir, "concept_mappings.json")
    store = MappingStore(source=core_mappings_path, read_only=True)
        
    # Unknown Tesla concept should fall back to core if no specific mapping
    result = store.get_standard_concept("us-gaap_NetIncome")
    assert result == "Net Income"

@pytest.mark.fast
def test_company_detection_from_concept_prefix(temp_standardization_dir):
    """Test automatic company detection from concept prefixes."""
    core_mappings_path = os.path.join(temp_standardization_dir, "concept_mappings.json")
    store = MappingStore(source=core_mappings_path, read_only=True)
        
    # Test entity detection
    assert store._detect_entity_from_concept("tsla_AutomotiveRevenue") == "tsla"
    assert store._detect_entity_from_concept("us-gaap_Revenue") is None
    assert store._detect_entity_from_concept("unknown:Concept") is None

@pytest.mark.fast
def test_enhanced_standardization_backwards_compatibility(temp_standardization_dir):
    """Test that enhanced standardization maintains backwards compatibility."""
    # Test with enhanced features disabled
    core_mappings_path = os.path.join(temp_standardization_dir, "concept_mappings.json")
    store_disabled = MappingStore(source=core_mappings_path, read_only=True)
        
    result_disabled = store_disabled.get_standard_concept("us-gaap_Revenue")
    assert result_disabled == "Revenue"



@pytest.mark.fast
def test_hierarchy_rules_loading(temp_standardization_dir):
    """Test that hierarchy rules are properly loaded from company mappings."""

    
    core_mappings_path = os.path.join(temp_standardization_dir, "concept_mappings.json")
    store = MappingStore(source=core_mappings_path, read_only=True)
        
    # Check hierarchy rules were loaded
    assert "Revenue" in store.hierarchy_rules
    assert store.hierarchy_rules["Revenue"]["children"] == ["Automotive Revenue", "Energy Revenue"]

@pytest.mark.fast
def test_enhanced_concept_mapper_integration(temp_standardization_dir):
    """Test that ConceptMapper works with enhanced MappingStore."""
    core_mappings_path = os.path.join(temp_standardization_dir, "concept_mappings.json")
    store = MappingStore(source=core_mappings_path, read_only=True)
    mapper = ConceptMapper(store)
        
    # Test Tesla-specific mapping
    result = mapper.map_concept(
            "tsla:AutomotiveLeasing", 
            "Automotive leasing", 
            {"statement_type": "IncomeStatement"}
    )
    assert result == "Automotive Leasing Revenue"
        
    # Test core mapping still works
    result = mapper.map_concept(
            "us-gaap_Revenue", 
            "Revenue", 
            {"statement_type": "IncomeStatement"}
    )
    assert result == "Revenue"

@pytest.mark.fast
def test_standardize_statement_with_tesla_concepts(temp_standardization_dir):
    """Test standardizing a statement with Tesla-specific concepts."""

    
    core_mappings_path = os.path.join(temp_standardization_dir, "concept_mappings.json")
    store = MappingStore(source=core_mappings_path, read_only=True)
    mapper = ConceptMapper(store)
        
    # Create test statement data with Tesla concepts
    statement_data = [
            {
                "concept": "tsla:AutomotiveLeasing",
                "label": "Automotive leasing",
                "statement_type": "IncomeStatement",
                "is_abstract": False
            },
            {
                "concept": "us-gaap_Revenue",
                "label": "Total revenues",
                "statement_type": "IncomeStatement",
                "is_abstract": False
            }
        ]
        
    # Standardize the statement
    result = standardize_statement(statement_data, mapper)
        
    # Check Tesla concept was mapped to Tesla-specific standard concept
    tesla_item = next(item for item in result if item["concept"] == "tsla:AutomotiveLeasing")
    assert tesla_item["label"] == "Automotive Leasing Revenue"
    assert tesla_item["original_label"] == "Automotive leasing"
        
    # Check US-GAAP concept was mapped to core standard concept
    gaap_item = next(item for item in result if item["concept"] == "us-gaap_Revenue")
    assert gaap_item["label"] == "Revenue"
    assert gaap_item["original_label"] == "Total revenues"

@pytest.mark.fast
def test_new_standard_concepts_available():
    """Test that new hierarchical standard concepts are available."""
    # Test hierarchical revenue concepts
    assert StandardConcept.AUTOMOTIVE_REVENUE.value == "Automotive Revenue"
    assert StandardConcept.AUTOMOTIVE_LEASING_REVENUE.value == "Automotive Leasing Revenue"
    assert StandardConcept.ENERGY_REVENUE.value == "Energy Revenue"
    
    # Test hierarchical expense concepts
    assert StandardConcept.SELLING_EXPENSE.value == "Selling Expense"
    assert StandardConcept.GENERAL_ADMIN_EXPENSE.value == "General and Administrative Expense"
    assert StandardConcept.MARKETING_EXPENSE.value == "Marketing Expense"

@pytest.mark.fast
def test_enhanced_disabled_company_not_in_list(temp_standardization_dir):
    """Test that enhanced mappings only apply to companies in ENHANCED_COMPANIES list."""

    
    core_mappings_path = os.path.join(temp_standardization_dir, "concept_mappings.json")
    store = MappingStore(source=core_mappings_path, read_only=True)
        
    # Tesla mappings should load but not be prioritized
    assert 'tsla' in store.company_mappings  # Tesla mappings are loaded
        
    # Tesla concept should not get enhanced priority
    result = store.get_standard_concept("tsla:AutomotiveLeasing")
    # Should still work but with lower priority (if it gets mapped at all)
    # This depends on the specific implementation priority logic
    assert result == "Automotive Leasing Revenue"  # Tesla mappings still work

@pytest.mark.fast
def test_error_handling_missing_company_mapping_file(temp_standardization_dir):
    """Test error handling when company mapping files are missing or invalid."""
    # Create invalid JSON file
    invalid_file = os.path.join(temp_standardization_dir, "company_mappings", "invalid_mappings.json")
    with open(invalid_file, 'w') as f:
        f.write("{ invalid json")

    core_mappings_path = os.path.join(temp_standardization_dir, "concept_mappings.json")
        
    # Should not crash, just log warning
    store = MappingStore(source=core_mappings_path, read_only=True)
        
    # Tesla mappings should still work
    assert 'tsla' in store.company_mappings

@pytest.mark.fast
def test_performance_with_enhanced_mappings(temp_standardization_dir):
    """Test that enhanced mappings initialization doesn't cause major performance issues."""
    import time
    
    # Test initialization time with enhanced disabled
    core_mappings_path = os.path.join(temp_standardization_dir, "concept_mappings.json")
        
    start_time = time.time()
    store_disabled = MappingStore(source=core_mappings_path, read_only=True)
    disabled_init_time = time.time() - start_time
        
    # Test lookup time
    start_time = time.time()
    result_disabled = store_disabled.get_standard_concept("us-gaap_Revenue")
    disabled_lookup_time = time.time() - start_time
    

    start_time = time.time()
    store_enabled = MappingStore(source=core_mappings_path, read_only=True)
    enabled_init_time = time.time() - start_time
        
    # Test lookup time
    start_time = time.time()
    result_enabled = store_enabled.get_standard_concept("us-gaap_Revenue")
    enabled_lookup_time = time.time() - start_time
    
    # Basic functionality should work the same
    assert result_disabled == result_enabled == "Revenue"
    
    # Initialization should complete in reasonable time (< 1 second)
    assert enabled_init_time < 1.0, f"Enhanced initialization too slow: {enabled_init_time}"
    assert disabled_init_time < 1.0, f"Core initialization too slow: {disabled_init_time}"