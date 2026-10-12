from assent_agents.abbrev import expand


def test_expands_clinical_shorthand_without_touching_codes() -> None:
    out = expand("A/P: L L radic 2/2 L5-S1 HNP w/ foraminal stenosis.")
    assert "left left radiculopathy secondary to L5-S1 herniated nucleus pulposus" in out
    assert "L5-S1" in out  # spinal levels are not "left"


def test_durations_and_mixed_case() -> None:
    assert expand("LBP x10 wks w/ radiation to L LE.") == (
        "low back pain for 10 weeks with radiation to left lower extremity (leg)."
    )
    assert expand("PSH: no spinal surgery.") == "past surgical history: no spinal surgery."
    assert expand("Plain sentence about pain.") == "Plain sentence about pain."
