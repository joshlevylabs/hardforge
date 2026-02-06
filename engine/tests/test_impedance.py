"""
Tests for impedance modeling.

Validates the loudspeaker impedance model against known physical behaviors:
1. Peak impedance at resonance ≈ Re * (1 + Qms/Qes)
2. DC impedance → Re
3. High-frequency impedance rises with Le
4. Qts consistency check
5. CSV parsing and interpolation
"""

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from engine.impedance import (
    calculate_impedance,
    impedance_magnitude,
    impedance_phase,
    verify_impedance_model,
    parse_impedance_csv,
    interpolate_impedance,
    generate_frequencies,
    _motional_params_from_ts,
)


# Reference driver: Dayton Audio RS180-8 (well-characterized)
RS180 = {
    'manufacturer': 'Dayton Audio',
    'model': 'RS180-8',
    're': 6.0,
    'le': 0.56,
    'fs': 37.0,
    'qms': 2.79,
    'qes': 0.42,
    'qts': 0.36,
    'vas': 24.0,
    'bl': 6.9,
    'mms': 14.0,
    'cms': 1.33,
    'rms': 1.18,
    'sd': 137.0,
    'xmax': 5.0,
    'nominal_impedance': 8,
    'power_rating': 60,
    'sensitivity': 86.5,
}

# Minimal TS params (Q-factor path)
MINIMAL_DRIVER = {
    're': 6.0,
    'le': 0.5,
    'fs': 40.0,
    'qms': 3.0,
    'qes': 0.5,
    'qts': 0.43,
}


class TestImpedanceCalculation:
    """Test core impedance calculation."""

    def test_peak_at_resonance(self):
        """Impedance peak should occur near fs."""
        freqs = np.logspace(1, 4, 1000)  # 10 Hz to 10 kHz
        Z = calculate_impedance(RS180, freqs)
        mag = np.abs(Z)

        # Find peak frequency
        peak_idx = np.argmax(mag)
        peak_freq = freqs[peak_idx]

        # Peak should be within 5% of fs
        assert abs(peak_freq - RS180['fs']) / RS180['fs'] < 0.05, (
            f"Peak at {peak_freq:.1f} Hz, expected near {RS180['fs']} Hz"
        )

    def test_peak_magnitude(self):
        """Peak impedance ≈ Re * (1 + Qms/Qes) when Le is small."""
        # Use Q-factor path to verify the relationship
        driver = dict(MINIMAL_DRIVER)
        driver['le'] = 0.0  # Remove Le for cleaner test

        Z_at_fs = calculate_impedance(driver, np.array([driver['fs']]))
        peak_mag = np.abs(Z_at_fs[0])

        expected = driver['re'] * (1 + driver['qms'] / driver['qes'])

        assert abs(peak_mag - expected) / expected < 0.01, (
            f"Peak magnitude {peak_mag:.2f}Ω, expected {expected:.2f}Ω"
        )

    def test_dc_impedance_approaches_re(self):
        """At very low frequencies, |Z| → Re."""
        Z_low = calculate_impedance(RS180, np.array([0.1]))
        mag_low = np.abs(Z_low[0])

        # Should be within 5% of Re (motional impedance is very high at DC)
        assert abs(mag_low - RS180['re']) / RS180['re'] < 0.05, (
            f"DC impedance {mag_low:.2f}Ω, expected ≈{RS180['re']}Ω"
        )

    def test_high_frequency_rising(self):
        """At high frequencies, impedance should rise due to Le."""
        freqs = np.array([100, 1000, 10000])
        Z = calculate_impedance(RS180, freqs)
        mag = np.abs(Z)

        # Impedance at 10 kHz should be higher than at 1 kHz (above resonance)
        assert mag[2] > mag[1], (
            f"Impedance should rise at HF: {mag[2]:.2f}Ω at 10kHz vs {mag[1]:.2f}Ω at 1kHz"
        )

    def test_complex_output(self):
        """Output should be complex numpy array."""
        freqs = np.array([100.0, 1000.0])
        Z = calculate_impedance(RS180, freqs)

        assert Z.dtype == complex
        assert len(Z) == 2

    def test_positive_magnitude(self):
        """Magnitude should always be positive."""
        freqs = np.logspace(1, 4.5, 500)
        mag = impedance_magnitude(RS180, freqs)

        assert np.all(mag > 0), "All impedance magnitudes must be positive"

    def test_phase_range(self):
        """Phase should be in [-90, 90] degrees for passive devices."""
        freqs = np.logspace(1, 4.5, 500)
        phase = impedance_phase(RS180, freqs)

        assert np.all(phase >= -90) and np.all(phase <= 90), (
            f"Phase out of range: min={phase.min():.1f}°, max={phase.max():.1f}°"
        )

    def test_q_factor_vs_bl_path(self):
        """Q-factor and BL-based paths should give similar results."""
        # Only Q-factor path
        driver_q = {
            're': RS180['re'],
            'le': RS180['le'],
            'fs': RS180['fs'],
            'qms': RS180['qms'],
            'qes': RS180['qes'],
        }

        freqs = np.logspace(1, 4, 200)
        Z_full = calculate_impedance(RS180, freqs)
        Z_q = calculate_impedance(driver_q, freqs)

        mag_full = np.abs(Z_full)
        mag_q = np.abs(Z_q)

        # Differences are expected because BL/Mms/Cms/Rms and Q-factor values
        # from datasheets are measured independently and may not be perfectly
        # self-consistent. We verify that the overall shape is similar.
        relative_diff = np.abs(mag_full - mag_q) / mag_full
        # Allow up to 25% mean difference — the key assertion is that
        # both paths produce the same qualitative behavior (peak at fs, etc.)
        assert np.mean(relative_diff) < 0.25, (
            f"Mean relative difference: {np.mean(relative_diff):.2%}"
        )

    def test_no_le(self):
        """Should work when Le is 0 or not provided."""
        driver = {'re': 6.0, 'fs': 40.0, 'qms': 3.0, 'qes': 0.5}
        freqs = np.array([40.0, 1000.0])
        Z = calculate_impedance(driver, freqs)
        assert len(Z) == 2
        assert np.all(np.isfinite(Z))


class TestVerifyModel:
    """Test the model verification function."""

    def test_verification_passes(self):
        """Verify function should pass for a well-formed driver."""
        result = verify_impedance_model(RS180)

        assert result['qts_consistent']
        assert result['peak_error_pct'] < 5.0
        assert abs(result['dc_impedance'] - RS180['re']) / RS180['re'] < 0.1

    def test_qts_consistency(self):
        """Qts should equal Qms*Qes/(Qms+Qes)."""
        result = verify_impedance_model(RS180)
        expected_qts = (RS180['qms'] * RS180['qes']) / (RS180['qms'] + RS180['qes'])
        assert abs(result['qts_expected'] - expected_qts) < 0.001


class TestMotionalParams:
    """Test motional parameter derivation."""

    def test_bl_path_units(self):
        """BL-path should handle unit conversions correctly."""
        Res, Lces, Cmes = _motional_params_from_ts(RS180)

        # All values should be positive and finite
        assert Res > 0 and np.isfinite(Res)
        assert Lces > 0 and np.isfinite(Lces)
        assert Cmes > 0 and np.isfinite(Cmes)

        # Resonant frequency of motional circuit should be close to fs
        f_res = 1.0 / (2 * np.pi * np.sqrt(Lces * Cmes))
        assert abs(f_res - RS180['fs']) / RS180['fs'] < 0.10, (
            f"Motional resonance {f_res:.1f} Hz, expected ≈{RS180['fs']} Hz"
        )

    def test_q_path(self):
        """Q-factor path should produce valid parameters."""
        driver = {'re': 6.0, 'fs': 40.0, 'qms': 3.0, 'qes': 0.5}
        Res, Lces, Cmes = _motional_params_from_ts(driver)

        assert Res > 0
        assert Lces > 0
        assert Cmes > 0

        # Verify Res = Re * Qms / Qes
        expected_Res = driver['re'] * driver['qms'] / driver['qes']
        assert abs(Res - expected_Res) < 0.001


class TestCSVParsing:
    """Test impedance CSV parsing."""

    def test_basic_csv(self):
        """Parse a basic 2-column CSV."""
        csv_data = "frequency,magnitude\n20,8.5\n100,6.2\n1000,7.1\n10000,12.3"
        freqs, mags, phases = parse_impedance_csv(csv_data)

        assert len(freqs) == 4
        assert len(mags) == 4
        assert phases is None
        np.testing.assert_array_almost_equal(freqs, [20, 100, 1000, 10000])

    def test_three_column_csv(self):
        """Parse CSV with phase data."""
        csv_data = "freq,mag,phase\n20,8.5,10\n100,6.2,-5\n1000,7.1,-15"
        freqs, mags, phases = parse_impedance_csv(csv_data)

        assert len(freqs) == 3
        assert phases is not None
        assert len(phases) == 3

    def test_no_header(self):
        """Parse CSV without header."""
        csv_data = "20,8.5\n100,6.2\n1000,7.1"
        freqs, mags, _ = parse_impedance_csv(csv_data)
        assert len(freqs) == 3

    def test_tab_delimiter(self):
        """Parse tab-delimited data."""
        csv_data = "20\t8.5\n100\t6.2\n1000\t7.1"
        freqs, mags, _ = parse_impedance_csv(csv_data)
        assert len(freqs) == 3

    def test_empty_raises(self):
        """Empty CSV should raise ValueError."""
        with pytest.raises(ValueError):
            parse_impedance_csv("")

    def test_insufficient_data(self):
        """CSV with < 2 points should raise ValueError."""
        with pytest.raises(ValueError):
            parse_impedance_csv("freq,mag\n20,8.5")


class TestInterpolation:
    """Test impedance interpolation."""

    def test_basic_interpolation(self):
        """Interpolate between known points."""
        freq = np.array([20.0, 200.0, 2000.0, 20000.0])
        mag = np.array([8.0, 6.0, 7.0, 15.0])

        target = np.array([100.0, 1000.0, 10000.0])
        interp_mag, _ = interpolate_impedance(freq, mag, None, target)

        assert len(interp_mag) == 3
        assert np.all(interp_mag > 0)

    def test_with_phase(self):
        """Interpolation should handle phase data."""
        freq = np.array([20.0, 200.0, 2000.0])
        mag = np.array([8.0, 6.0, 7.0])
        phase = np.array([10.0, -5.0, -20.0])

        target = np.array([100.0])
        interp_mag, interp_phase = interpolate_impedance(freq, mag, phase, target)

        assert interp_phase is not None
        assert len(interp_phase) == 1


class TestGenerateFrequencies:
    """Test frequency array generation."""

    def test_default_range(self):
        """Default should be 20-20kHz."""
        freqs = generate_frequencies()
        assert freqs[0] == pytest.approx(20.0)
        assert freqs[-1] == pytest.approx(20000.0)
        assert len(freqs) == 500

    def test_custom_range(self):
        """Custom range should work."""
        freqs = generate_frequencies(10, 100, 10)
        assert len(freqs) == 10
        assert freqs[0] == pytest.approx(10.0)
        assert freqs[-1] == pytest.approx(100.0)

    def test_log_spacing(self):
        """Frequencies should be logarithmically spaced."""
        freqs = generate_frequencies(10, 10000, 4)
        # Ratios between consecutive points should be equal
        ratios = freqs[1:] / freqs[:-1]
        np.testing.assert_array_almost_equal(ratios, ratios[0] * np.ones(3))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
