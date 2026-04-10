from scripts.formula_detector import FormulaDetector


def test_formula_detector_positive_cases():
    detector = FormulaDetector()
    assert detector.is_formula_expression("E = (1 - RH / 100) × (1 + 0.35v)")
    assert detector.is_formula_expression("x^2 + y^2 = z^2")
    assert detector.is_formula_expression("sin(theta) + 1/2")


def test_formula_detector_negative_cases():
    detector = FormulaDetector()
    assert not detector.is_formula_expression("print(x)")
    assert not detector.is_formula_expression("def handler(event):")
    assert not detector.is_formula_expression("user_id")
