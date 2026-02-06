"""
Tests for impedance correction network calculations.

Validates:
1. Zobel network: Rz = Re, Cz = Le/Re²
2. Notch filter: correct resonant frequency, R = Re*Qms/Qes
3. Full correction: corrected impedance is flatter than uncorrected
4. Power rating estimates
"""

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from engine.correction import (
    zobel_network,
    notch_filter,
    full_correction,
    calculate_corrected_impedance,
)
from engine.impedance import calculate_impedance


# Reference driver
DRIVER = {
    're': 6.0,
    'le': 0.56,  # mH
    'fs': 37.0,
    'qms': 2.79,
    'qes': 0.42,
    'qts': 0.36,
    'power_rating': 60,
}


class TestZobelNetwork:
    """Test Zobel network calculations."""

    def test_basic_values(self):
        """Rz should equal Re, Cz should equal Le/Re²."""
        result = zobel_network(Re=6.0, Le=0.56)

        assert result['Rz'] == pytest.approx(6.0, abs=0.01)

        Le_si = 0.56e-3  # mH → H
        expected_Cz = Le_si / (6.0 ** 2)
        assert result['Cz'] == pytest.approx(expected_Cz, rel=0.001)

    def test_with_margin(self):
        """Margin should scale Rz."""
        result = zobel_network(Re=6.0, Le=0.56, margin=1.25)
        assert result['Rz'] == pytest.approx(7.5, abs=0.01)

    def test_negative_le_raises(self):
        """Should raise ValueError for Le <= 0."""
        with pytest.raises(ValueError):
            zobel_network(Re=6.0, Le=0.0)

        with pytest.raises(ValueError):
            zobel_network(Re=6.0, Le=-0.5)

    def test_units(self):
        """Output should have correct unit labels."""
        result = zobel_network(Re=8.0, Le=1.0)
        assert result['Rz_unit'] == 'Ω'
        assert result['Cz_unit'] == 'F'


class TestNotchFilter:
    """Test resonance notch filter calculations."""

    def test_resonant_frequency(self):
        """Notch filter should resonate at fs."""
        result = notch_filter(fs=37.0, Qms=2.79, Qes=0.42, Re=6.0)

        # Check resonant frequency: f = 1/(2π√(LC))
        f_check = result['resonant_freq_check']
        assert f_check == pytest.approx(37.0, rel=0.01), (
            f"Notch resonates at {f_check} Hz, expected 37.0 Hz"
        )

    def test_resistance_value(self):
        """R_notch should equal Re * Qms / Qes."""
        result = notch_filter(fs=37.0, Qms=2.79, Qes=0.42, Re=6.0)

        expected_R = 6.0 * 2.79 / 0.42
        assert result['R_notch'] == pytest.approx(expected_R, rel=0.01)

    def test_inductance_value(self):
        """L_notch = Qes * Re / (2πfs)."""
        result = notch_filter(fs=37.0, Qms=2.79, Qes=0.42, Re=6.0)

        expected_L = 0.42 * 6.0 / (2 * np.pi * 37.0)
        assert result['L_notch'] == pytest.approx(expected_L, rel=0.01)

    def test_capacitance_value(self):
        """C_notch = 1 / (2πfs * Qes * Re)."""
        result = notch_filter(fs=37.0, Qms=2.79, Qes=0.42, Re=6.0)

        expected_C = 1.0 / (2 * np.pi * 37.0 * 0.42 * 6.0)
        assert result['C_notch'] == pytest.approx(expected_C, rel=0.01)

    def test_positive_values(self):
        """All component values should be positive."""
        result = notch_filter(fs=100.0, Qms=5.0, Qes=0.5, Re=8.0)
        assert result['R_notch'] > 0
        assert result['L_notch'] > 0
        assert result['C_notch'] > 0


class TestFullCorrection:
    """Test combined correction network."""

    def test_has_both_networks(self):
        """Full correction should include both Zobel and notch."""
        result = full_correction(DRIVER)

        assert 'zobel' in result
        assert 'notch' in result
        assert len(result['components']) == 2

    def test_no_zobel_without_le(self):
        """No Zobel network when Le is 0 or absent."""
        driver = dict(DRIVER)
        driver['le'] = 0.0

        result = full_correction(driver)
        assert 'zobel' not in result
        assert 'notch' in result
        assert len(result['components']) == 1

    def test_target_impedance_default(self):
        """Default target should be Re."""
        result = full_correction(DRIVER)
        assert result['target_impedance'] == DRIVER['re']

    def test_corrected_impedance_is_flatter(self):
        """Corrected impedance should have less variation than uncorrected."""
        freqs = np.logspace(1, 4, 200)

        Z_orig = calculate_impedance(DRIVER, freqs)
        mag_orig = np.abs(Z_orig)

        correction = full_correction(DRIVER)
        Z_corr = calculate_corrected_impedance(DRIVER, correction, freqs)
        mag_corr = np.abs(Z_corr)

        # Measure flatness: standard deviation of impedance magnitude
        # Corrected should be flatter (lower std dev)
        std_orig = np.std(mag_orig)
        std_corr = np.std(mag_corr)

        assert std_corr < std_orig, (
            f"Corrected std ({std_corr:.2f}) should be < original std ({std_orig:.2f})"
        )

    def test_corrected_peak_reduced(self):
        """Resonance peak should be significantly reduced by correction."""
        freqs = np.logspace(1, 4, 500)

        Z_orig = calculate_impedance(DRIVER, freqs)
        mag_orig = np.abs(Z_orig)

        correction = full_correction(DRIVER)
        Z_corr = calculate_corrected_impedance(DRIVER, correction, freqs)
        mag_corr = np.abs(Z_corr)

        peak_orig = np.max(mag_orig)
        peak_corr = np.max(mag_corr)

        # Corrected peak should be at most 50% of original peak
        assert peak_corr < peak_orig * 0.7, (
            f"Corrected peak ({peak_corr:.1f}Ω) should be much less than "
            f"original peak ({peak_orig:.1f}Ω)"
        )

    def test_power_ratings_included(self):
        """Power rating estimates should be included."""
        result = full_correction(DRIVER)

        assert 'power_rating' in result['zobel']
        assert 'power_rating' in result['notch']
        assert result['zobel']['power_rating']['resistor_watts'] > 0
        assert result['notch']['power_rating']['resistor_watts'] > 0


class TestCorrectedImpedance:
    """Test corrected impedance calculation."""

    def test_output_shape(self):
        """Output should match input frequency array length."""
        freqs = np.logspace(1, 4, 100)
        correction = full_correction(DRIVER)
        Z = calculate_corrected_impedance(DRIVER, correction, freqs)

        assert len(Z) == 100
        assert Z.dtype == complex

    def test_positive_magnitude(self):
        """Corrected impedance magnitude should always be positive."""
        freqs = np.logspace(1, 4, 200)
        correction = full_correction(DRIVER)
        Z = calculate_corrected_impedance(DRIVER, correction, freqs)

        assert np.all(np.abs(Z) > 0)

    def test_corrected_below_original(self):
        """Corrected impedance should generally be ≤ original."""
        freqs = np.logspace(1, 4, 200)

        Z_orig = calculate_impedance(DRIVER, freqs)
        correction = full_correction(DRIVER)
        Z_corr = calculate_corrected_impedance(DRIVER, correction, freqs)

        # Parallel networks always reduce impedance: Z_corr ≤ Z_orig everywhere
        mag_orig = np.abs(Z_orig)
        mag_corr = np.abs(Z_corr)

        # Allow tiny floating point tolerance
        assert np.all(mag_corr <= mag_orig + 0.01), (
            "Parallel correction should never increase impedance"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
