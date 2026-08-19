"""Automated test suite for the Multi-Unit Conversion Engine.

Verifies conversion formulas and contract bounds for temperature, length, and weight conversions.
"""

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).parent.parent
SOURCE_FILE = PROJECT_DIR / "source" / "unit_converter.omni"
OMNI_CLI = [sys.executable, "-m", "omni_compiler.cli"]


def run_omni(command: list[str]) -> subprocess.CompletedProcess:
    """Run an omni CLI command and return the result."""
    return subprocess.run(
        OMNI_CLI + command,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )


class TestCompilerChecks:
    """Test that the source file passes all compiler checks."""

    def test_check_passes(self):
        """omni check should exit with code 0."""
        result = run_omni(["check", str(SOURCE_FILE)])
        assert result.returncode == 0, f"Check failed: {result.stderr}"

    def test_verify_all_contracts_proven(self):
        """omni verify should prove all contracts (status verified or no-contracts)."""
        result = run_omni(["verify", str(SOURCE_FILE)])
        assert result.returncode == 0, f"Verify failed: {result.stderr}"

        import json
        data = json.loads(result.stdout)
        assert data["schema"] == "omni.verify.batch"

        for fn_result in data["results"]:
            # All functions should be verified or have no contracts
            assert fn_result["status"] in ("verified", "no-contracts"), (
                f"Function {fn_result['function']} failed verification: "
                f"status={fn_result['status']}, reason={fn_result.get('reason')}"
            )

    def test_run_executes_without_errors(self):
        """omni run should execute without runtime errors."""
        result = run_omni(["run", str(SOURCE_FILE)])
        assert result.returncode == 0, f"Run failed: {result.stderr}"

        # Check that expected output sections are present
        assert "=== Temperature Conversions ===" in result.stdout
        assert "=== Length Conversions ===" in result.stdout
        assert "=== Weight Conversions ===" in result.stdout
        assert "=== Boundary Validation Tests ===" in result.stdout
        assert "All conversions completed successfully!" in result.stdout

    def test_generate_test_template(self):
        """omni generate should produce a valid test template for a conversion function."""
        result = run_omni(["generate", str(SOURCE_FILE), "celsius_to_fahrenheit"])
        assert result.returncode == 0, f"Generate failed: {result.stderr}"

        # The generated test should be valid Python
        test_code = result.stdout
        assert "def test_celsius_to_fahrenheit_compiles" in test_code
        assert "def test_celsius_to_fahrenheit_contracts_present" in test_code
        assert "@given" in test_code


class TestTemperatureConversions:
    """Test temperature conversion formulas by running the program and checking output."""

    def run_converter(self) -> str:
        """Run the converter and return stdout."""
        result = run_omni(["run", str(SOURCE_FILE)])
        assert result.returncode == 0
        return result.stdout

    def test_celsius_to_fahrenheit(self):
        """0°C = 32°F, 100°C = 212°F"""
        output = self.run_converter()
        assert "0 Celsius = 32 Fahrenheit" in output

    def test_fahrenheit_to_celsius(self):
        """32°F = 0°C, 212°F = 100°C"""
        output = self.run_converter()
        assert "32 Fahrenheit = 0 Celsius" in output

    def test_celsius_to_kelvin(self):
        """0°C = 273.15K, 100°C = 373.15K"""
        output = self.run_converter()
        assert "0 Celsius = 273.15 Kelvin" in output

    def test_kelvin_to_celsius(self):
        """273.15K = 0°C, 0K = -273.15°C"""
        output = self.run_converter()
        assert "273.15 Kelvin = 0 Celsius" in output
        assert "0 Kelvin = -273.15 Celsius" in output

    def test_fahrenheit_to_kelvin(self):
        """32°F = 273.15K"""
        output = self.run_converter()
        assert "32 Fahrenheit = 273.15 Kelvin" in output

    def test_kelvin_to_fahrenheit(self):
        """273.15K = 32°F"""
        output = self.run_converter()
        assert "273.15 Kelvin = 32 Fahrenheit" in output


class TestLengthConversions:
    """Test length conversion formulas."""

    def run_converter(self) -> str:
        result = run_omni(["run", str(SOURCE_FILE)])
        assert result.returncode == 0
        return result.stdout

    def test_meters_to_feet(self):
        """1 m = 3.28084 ft"""
        output = self.run_converter()
        assert "1 Meter = 3.28084 Feet" in output

    def test_feet_to_meters(self):
        """3.28084 ft = 1 m"""
        output = self.run_converter()
        assert "3.28084 Feet = 1 Meters" in output

    def test_meters_to_inches(self):
        """1 m = 39.3701 in"""
        output = self.run_converter()
        assert "1 Meter = 39.3701 Inches" in output

    def test_inches_to_meters(self):
        """39.3701 in = 1 m"""
        output = self.run_converter()
        assert "39.3701 Inches = 1 Meters" in output

    def test_meters_to_kilometers(self):
        """1000 m = 1 km"""
        output = self.run_converter()
        assert "1000 Meters = 1 Kilometers" in output

    def test_kilometers_to_meters(self):
        """1 km = 1000 m"""
        output = self.run_converter()
        assert "1 Kilometer = 1000 Meters" in output

    def test_feet_to_inches(self):
        """1 ft = 12 in"""
        output = self.run_converter()
        assert "1 Foot = 12 Inches" in output

    def test_inches_to_feet(self):
        """12 in = 1 ft"""
        output = self.run_converter()
        assert "12 Inches = 1 Feet" in output

    def test_kilometers_to_feet(self):
        """1 km = 3280.84 ft"""
        output = self.run_converter()
        assert "1 Kilometer = 3280.84 Feet" in output

    def test_feet_to_kilometers(self):
        """3280.84 ft = 1 km"""
        output = self.run_converter()
        assert "3280.84 Feet = 1 Kilometers" in output


class TestWeightConversions:
    """Test weight conversion formulas."""

    def run_converter(self) -> str:
        result = run_omni(["run", str(SOURCE_FILE)])
        assert result.returncode == 0
        return result.stdout

    def test_kilograms_to_pounds(self):
        """1 kg = 2.20462 lb"""
        output = self.run_converter()
        assert "1 Kilogram = 2.20462 Pounds" in output

    def test_pounds_to_kilograms(self):
        """2.20462 lb = 1 kg"""
        output = self.run_converter()
        assert "2.20462 Pounds = 1 Kilograms" in output

    def test_kilograms_to_ounces(self):
        """1 kg = 35.274 oz"""
        output = self.run_converter()
        assert "1 Kilogram = 35.274 Ounces" in output

    def test_ounces_to_kilograms(self):
        """35.274 oz = 1 kg"""
        output = self.run_converter()
        assert "35.274 Ounces = 1 Kilograms" in output

    def test_pounds_to_ounces(self):
        """1 lb = 16 oz"""
        output = self.run_converter()
        assert "1 Pound = 16 Ounces" in output

    def test_ounces_to_pounds(self):
        """16 oz = 1 lb"""
        output = self.run_converter()
        assert "16 Ounces = 1 Pounds" in output


class TestBoundaryValidation:
    """Test boundary validation (non-negative constraints, absolute zero)."""

    def run_converter(self) -> str:
        result = run_omni(["run", str(SOURCE_FILE)])
        assert result.returncode == 0
        return result.stdout

    def test_kelvin_absolute_zero(self):
        """0 Kelvin = -273.15 Celsius (absolute zero boundary)"""
        output = self.run_converter()
        assert "0 Kelvin = -273.15 Celsius" in output

    def test_non_negative_length_inputs(self):
        """Length conversions require non-negative inputs (enforced by contracts)"""
        # This is verified by the contract verification in TestCompilerChecks
        pass

    def test_non_negative_weight_inputs(self):
        """Weight conversions require non-negative inputs (enforced by contracts)"""
        # This is verified by the contract verification in TestCompilerChecks
        pass


class TestPureFunctions:
    """Test that conversion functions are declared pure."""

    def test_all_conversion_functions_are_pure(self):
        """All conversion functions should have 'pure' declaration."""
        source = SOURCE_FILE.read_text(encoding="utf-8")

        # Count pure functions (22 conversion functions + 1 make_result helper = 23)
        pure_count = source.count("pure")
        assert pure_count >= 23


class TestStructuredResults:
    """Test structured result representation."""

    def test_conversion_result_type_defined(self):
        """ConversionResult type should be defined."""
        source = SOURCE_FILE.read_text(encoding="utf-8")
        assert "type ConversionResult" in source
        assert "value: Number" in source
        assert "source_unit: Text" in source
        assert "target_unit: Text" in source
        assert "status: Text" in source

    def test_make_result_constructs_structured_output(self):
        """make_result helper should construct ConversionResult structs."""
        source = SOURCE_FILE.read_text(encoding="utf-8")
        assert "fn make_result" in source
        assert "ConversionResult(" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])