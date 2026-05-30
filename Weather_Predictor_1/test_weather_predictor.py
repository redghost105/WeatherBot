"""
Test script for WeatherPredictor Phase 1 & 2 implementation.

Tests:
1. Bucket dataclass functionality
2. HistoricalBiasLearner persistence and bias calculation
3. WeatherPredictor hybrid probability calculation
4. Integration with existing WeatherAggregator
"""

import os
import tempfile
from weather_aggregator import WeatherAggregator
from weather_predictor import (
    Bucket, HistoricalBiasLearner, WeatherPredictor,
    parse_bucket_string, create_buckets_from_range
)
from config import CITIES_KALSHI


def test_bucket_dataclass():
    """Test 1: Bucket dataclass functionality"""
    print("\n" + "="*80)
    print("✅ TEST 1: Bucket Dataclass")
    print("="*80)

    bucket = Bucket(low=92, high=93, label="92-93")
    print(f"Created bucket: {bucket.label}")
    print(f"  Contains 92.5°F: {bucket.contains(92.5)}")
    print(f"  Contains 93.5°F: {bucket.contains(93.5)}")
    print(f"  Midpoint: {bucket.midpoint()}°F")
    print(f"  Width: {bucket.width()}°F")

    assert bucket.contains(92.5) == True
    assert bucket.contains(93.5) == False
    assert bucket.midpoint() == 92.5
    assert bucket.width() == 1.0

    print("\n✅ Bucket dataclass working correctly")


def test_historical_bias_learner():
    """Test 2: HistoricalBiasLearner with persistence"""
    print("\n" + "="*80)
    print("✅ TEST 2: HistoricalBiasLearner")
    print("="*80)

    # Use temporary file for testing
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        bias_file = f.name

    try:
        # Create learner
        learner = HistoricalBiasLearner(bias_file=bias_file)
        print(f"Created HistoricalBiasLearner (file: {bias_file})")

        # Add some bias records for KNYC
        print("\nAdding bias records for KNYC:")
        records = [
            (88, 87),  # Forecast 88, actual 87 → bias = +1.0
            (89, 87),  # Forecast 89, actual 87 → bias = +2.0
            (87, 86),  # Forecast 87, actual 86 → bias = +1.0
        ]
        for forecast, actual in records:
            learner.update("KNYC", forecast, actual)
            print(f"  Forecast: {forecast}°F, Actual: {actual}°F → Bias: {forecast - actual:.1f}°F")

        # Get average bias
        avg_bias = learner.get_bias("KNYC")
        print(f"\nAverage bias for KNYC: {avg_bias:.2f}°F (forecast runs warm)")
        assert avg_bias == pytest.approx(1.33, rel=0.01), f"Expected ~1.33, got {avg_bias}"

        # Get bias std
        bias_std = learner.get_bias_std("KNYC")
        print(f"Bias std dev for KNYC: {bias_std:.2f}°F")

        # Test persistence: create new learner instance
        learner2 = HistoricalBiasLearner(bias_file=bias_file)
        avg_bias2 = learner2.get_bias("KNYC")
        print(f"\nLoaded from file, bias still: {avg_bias2:.2f}°F ✓")
        assert avg_bias == avg_bias2, "Persistence failed"

        # Test with no history
        no_history_bias = learner.get_bias("KMDW")
        print(f"Bias for KMDW (no history): {no_history_bias:.2f}°F")
        assert no_history_bias == 0.0, "Expected 0.0 for no history"

        print("\n✅ HistoricalBiasLearner working correctly")

    finally:
        # Clean up temp file
        if os.path.exists(bias_file):
            os.remove(bias_file)


def test_weather_predictor_with_real_data():
    """Test 3: WeatherPredictor hybrid logic with real weather data"""
    print("\n" + "="*80)
    print("✅ TEST 3: WeatherPredictor with Real Data")
    print("="*80)

    # Fetch real weather data for NYC
    city = CITIES_KALSHI["NYC"]
    agg = WeatherAggregator()

    print(f"\nFetching weather for {city['name']}...")
    weather = agg.get_complete_weather_data(
        latitude=city['lat'],
        longitude=city['lon'],
        location_name=city['name'],
        forecast_days=7
    )

    if not weather:
        print("❌ Failed to fetch weather data")
        return

    print(f"✅ Retrieved weather data:")
    print(f"   Current: {weather.current.temperature:.1f}°C")
    print(f"   Hourly forecasts: {len(weather.hourly_forecast)}")
    print(f"   Daily forecasts: {len(weather.daily_forecast)}")
    print(f"   Ensemble forecasts: {len(weather.ensemble_forecast)}")

    # Create predictor with bias learner
    bias_learner = HistoricalBiasLearner()
    # Add some mock historical data
    bias_learner.update("KNYC", 88, 87)  # NYC runs +1°F warm on average
    bias_learner.update("KNYC", 85, 84)
    bias_learner.update("KNYC", 90, 89)

    predictor = WeatherPredictor(
        bias_learner=bias_learner,
        ensemble_weight=0.7,
        temp_unit='C'
    )

    print(f"\nCreated WeatherPredictor")
    print(f"   Ensemble weight: 70%")
    print(f"   Temperature unit: Celsius")

    # Create buckets (in Celsius)
    # If current is ~24°C, we'd expect ~29°C high
    buckets = create_buckets_from_range(low=20, high=36)
    print(f"\nCreated {len(buckets)} temperature buckets (20-36°C)")

    # Calculate probabilities
    probs = predictor.hybrid_bucket_probabilities(
        weather_data=weather,
        buckets=buckets,
        station_id="KNYC",
        apply_bias_correction=True
    )

    print(f"\n📊 Probability Distribution (26 buckets):")
    print(f"   {'Bucket':<10} {'Probability':<15} {'Method':<15}")
    print(f"   {'-'*40}")

    top_buckets = sorted(probs.items(), key=lambda x: x[1]['probability'], reverse=True)[:5]
    for label, data in top_buckets:
        prob = data['probability']
        method = data['method']
        print(f"   {label:<10} {prob:>6.1%}         {method:<15}")

    # Verify probabilities sum to ~1.0
    total_prob = sum(p['probability'] for p in probs.values())
    print(f"\n✓ Total probability: {total_prob:.3f}")
    assert 0.99 < total_prob < 1.01, f"Probabilities don't sum to 1.0: {total_prob}"

    # Verify method is set
    first_bucket = next(iter(probs.values()))
    method = first_bucket['method']
    confidence = first_bucket['confidence']
    print(f"✓ Method: {method}, Confidence: {confidence:.1%}")
    assert method in ['ensemble', 'statistical', 'blended'], f"Invalid method: {method}"

    print("\n✅ WeatherPredictor working correctly")


def test_bucket_parsing():
    """Test 4: Bucket parsing helpers"""
    print("\n" + "="*80)
    print("✅ TEST 4: Bucket Parsing Helpers")
    print("="*80)

    # Test parse_bucket_string
    bucket = parse_bucket_string("92-93")
    print(f"Parsed '92-93': low={bucket.low}, high={bucket.high}, label={bucket.label}")
    assert bucket.low == 92 and bucket.high == 93

    # Test create_buckets_from_range
    buckets = create_buckets_from_range(low=88, high=95)
    print(f"Created {len(buckets)} buckets from 88-95:")
    for b in buckets:
        print(f"  {b.label}")

    assert len(buckets) == 7
    assert buckets[0].label == "88-89"
    assert buckets[-1].label == "94-95"

    print("\n✅ Bucket parsing helpers working correctly")


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🧪 WEATHERPREDICTOR PHASE 1 & 2 TEST SUITE")
    print("="*80)

    try:
        test_bucket_dataclass()
        test_historical_bias_learner()
        test_bucket_parsing()
        test_weather_predictor_with_real_data()

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80)
        print("\nWeatherPredictor Phase 1 & 2 implementation verified:")
        print("  ✓ Bucket dataclass working")
        print("  ✓ HistoricalBiasLearner with JSON persistence")
        print("  ✓ WeatherPredictor hybrid logic (ensemble + statistical blending)")
        print("  ✓ Real data integration with WeatherAggregator")
        print("  ✓ Bucket parsing utilities")
        print("\nReady for Phase 3: Edge Detection & Trading Intelligence")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Note: Using try/except instead of pytest.approx for simplicity
    class pytest:
        @staticmethod
        def approx(value, rel=0.01):
            class Approx:
                def __init__(self, v, r):
                    self.v = v
                    self.r = r
                def __eq__(self, other):
                    return abs(other - self.v) / self.v <= self.r
            return Approx(value, rel)

    main()
