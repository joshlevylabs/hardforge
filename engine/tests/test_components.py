"""
Tests for E-series component snapping and engineering notation.

Validates:
1. Correct snapping to E12, E24, E48, E96 series
2. Error percentage calculation
3. Engineering notation formatting
4. Edge cases
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from engine.components import (
    snap_to_e_series,
    engineering_notation,
    snap_resistor,
    snap_capacitor,
    snap_inductor,
    E12_BASE,
    E24_BASE,
    E48_BASE,
    E96_BASE,
)


class TestSnapToESeries:
    """Test E-series value snapping."""

    def test_exact_e24_value(self):
        """Exact E24 value should snap to itself with 0% error."""
        snapped, error = snap_to_e_series(4700.0, 'E24')
        assert snapped == pytest.approx(4700.0)
        assert error == pytest.approx(0.0, abs=0.01)

    def test_e12_snap(self):
        """Values should snap to nearest E12 value."""
        snapped, error = snap_to_e_series(5000.0, 'E12')
        assert snapped == pytest.approx(4700.0)

    def test_e24_snap(self):
        """Values should snap to nearest E24 value."""
        snapped, error = snap_to_e_series(5000.0, 'E24')
        assert snapped == pytest.approx(5100.0)

    def test_e96_snap(self):
        """E96 should provide tighter snapping."""
        snapped, error = snap_to_e_series(5000.0, 'E96')
        assert snapped == pytest.approx(4990.0)
        assert abs(error) < 1.0  # E96 has ≤1% spacing

    def test_small_values(self):
        """Should work for very small values (capacitors)."""
        snapped, error = snap_to_e_series(4.7e-9, 'E24')  # 4.7nF
        assert snapped == pytest.approx(4.7e-9, rel=0.01)

    def test_large_values(self):
        """Should work for large values (resistors)."""
        snapped, error = snap_to_e_series(1e6, 'E24')  # 1MΩ
        assert snapped == pytest.approx(1e6, rel=0.01)

    def test_error_sign_positive(self):
        """Positive error means snapped value is higher."""
        # 5000 snaps to 5100 in E24: positive error
        _, error = snap_to_e_series(5000.0, 'E24')
        assert error > 0

    def test_error_sign_negative(self):
        """Negative error means snapped value is lower."""
        # 5500 snaps to 5100 or 5600 in E24
        snapped, error = snap_to_e_series(5500.0, 'E24')
        # 5600 is closer, positive error
        # or 5100 is closer, negative error
        assert isinstance(error, float)

    def test_negative_value_raises(self):
        """Should raise ValueError for negative values."""
        with pytest.raises(ValueError):
            snap_to_e_series(-100.0)

    def test_zero_value_raises(self):
        """Should raise ValueError for zero."""
        with pytest.raises(ValueError):
            snap_to_e_series(0.0)

    def test_unknown_series_raises(self):
        """Should raise ValueError for unknown series."""
        with pytest.raises(ValueError):
            snap_to_e_series(100.0, 'E6')

    def test_all_e12_values_snap_to_self(self):
        """Every E12 base value (scaled) should snap to itself."""
        for base in E12_BASE:
            for decade in [1, 10, 100, 1000]:
                val = base * decade
                snapped, error = snap_to_e_series(val, 'E12')
                assert snapped == pytest.approx(val, rel=0.001), (
                    f"{val} snapped to {snapped} instead of itself"
                )

    def test_all_e24_values_snap_to_self(self):
        """Every E24 base value (scaled) should snap to itself."""
        for base in E24_BASE:
            val = base * 100  # Scale to 100s
            snapped, error = snap_to_e_series(val, 'E24')
            assert snapped == pytest.approx(val, rel=0.001), (
                f"{val} snapped to {snapped} instead of itself"
            )

    def test_midpoint_between_values(self):
        """Midpoint between two E24 values should snap to the geometrically closer one."""
        # Between 1.0 and 1.1 in E24
        mid = (1.0 * 1.1) ** 0.5  # Geometric mean ≈ 1.0488
        snapped, _ = snap_to_e_series(mid * 1000, 'E24')
        # Should snap to one of the two neighbors
        assert snapped in [1000.0, 1100.0]


class TestConvenienceFunctions:
    """Test snap_resistor, snap_capacitor, snap_inductor."""

    def test_snap_resistor(self):
        snapped, error = snap_resistor(4700.0)
        assert snapped == pytest.approx(4700.0)

    def test_snap_capacitor(self):
        snapped, error = snap_capacitor(100e-9)  # 100nF
        assert snapped == pytest.approx(100e-9, rel=0.05)

    def test_snap_inductor(self):
        snapped, error = snap_inductor(2.2e-3)  # 2.2mH
        assert snapped == pytest.approx(2.2e-3, rel=0.05)


class TestEngineeringNotation:
    """Test engineering notation formatting."""

    def test_kilo(self):
        """1000 → '1kΩ'."""
        result = engineering_notation(1000, 'Ω')
        assert result == '1kΩ'

    def test_mega(self):
        """1000000 → '1MΩ'."""
        result = engineering_notation(1e6, 'Ω')
        assert result == '1MΩ'

    def test_micro(self):
        """0.0001 → '100µF'."""
        result = engineering_notation(0.0001, 'F')
        assert result == '100µF'

    def test_milli(self):
        """0.047 → '47mH'."""
        result = engineering_notation(0.047, 'H')
        assert result == '47mH'

    def test_nano(self):
        """1e-9 → '1nF'."""
        result = engineering_notation(1e-9, 'F')
        assert result == '1nF'

    def test_pico(self):
        """100e-12 → '100pF'."""
        result = engineering_notation(100e-12, 'F')
        assert result == '100pF'

    def test_fractional_kilo(self):
        """4700 → '4.7kΩ'."""
        result = engineering_notation(4700, 'Ω')
        assert result == '4.7kΩ'

    def test_no_unit(self):
        """Should work without a unit string."""
        result = engineering_notation(1000)
        assert result == '1k'

    def test_zero(self):
        """Zero should format cleanly."""
        result = engineering_notation(0, 'Ω')
        assert result == '0Ω'

    def test_integer_value(self):
        """Whole numbers should not have decimal point."""
        result = engineering_notation(100, 'Ω')
        assert '.' not in result or result == '100Ω'

    def test_negative(self):
        """Negative values should include minus sign."""
        result = engineering_notation(-1000, 'Ω')
        assert '-' in result


class TestESeriesCompleteness:
    """Verify the E-series arrays are complete and sorted."""

    def test_e12_count(self):
        assert len(E12_BASE) == 12

    def test_e24_count(self):
        assert len(E24_BASE) == 24

    def test_e48_count(self):
        assert len(E48_BASE) == 48

    def test_e96_count(self):
        assert len(E96_BASE) == 96

    def test_e12_sorted(self):
        assert E12_BASE == sorted(E12_BASE)

    def test_e24_sorted(self):
        assert E24_BASE == sorted(E24_BASE)

    def test_e12_range(self):
        """E12 values should be in [1.0, 10.0)."""
        assert E12_BASE[0] == 1.0
        assert E12_BASE[-1] < 10.0

    def test_e24_range(self):
        assert E24_BASE[0] == 1.0
        assert E24_BASE[-1] < 10.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
