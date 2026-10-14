import importlib.util

import pytest

from backend.app.research.structures import analyze_smiles


@pytest.mark.skipif(importlib.util.find_spec("rdkit") is None, reason="RDKit optional dependency")
def test_ethanol_descriptors():
    result = analyze_smiles("CCO")
    assert result["valid"] is True
    assert result["canonical_smiles"] == "CCO"
    assert result["molecular_formula"] == "C2H6O"
    assert 46 < result["molecular_weight"] < 47


@pytest.mark.skipif(importlib.util.find_spec("rdkit") is None, reason="RDKit optional dependency")
def test_invalid_smiles_is_rejected():
    result = analyze_smiles("C1CC")
    assert result["valid"] is False


def test_empty_smiles_is_rejected():
    with pytest.raises(ValueError):
        analyze_smiles("  ")


def test_oversized_smiles_is_rejected():
    with pytest.raises(ValueError):
        analyze_smiles("C" * 2049)
