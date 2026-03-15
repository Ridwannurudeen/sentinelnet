from agent.alerts import AlertChecker


def test_alert_triggered_on_large_drop():
    checker = AlertChecker(threshold=20)
    assert checker.should_alert(previous_score=80, new_score=55) is True


def test_no_alert_on_small_change():
    checker = AlertChecker(threshold=20)
    assert checker.should_alert(previous_score=80, new_score=75) is False


def test_no_alert_on_improvement():
    checker = AlertChecker(threshold=20)
    assert checker.should_alert(previous_score=60, new_score=80) is False


def test_alert_on_exact_threshold():
    checker = AlertChecker(threshold=20)
    assert checker.should_alert(previous_score=80, new_score=60) is True
