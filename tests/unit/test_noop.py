from maskme.strategies.noop import apply

def test_explicit_keep_strategy():
    rules = {"diagnosis": "keep"}
    data = {"diagnosis": "cancer"}
    masked = apply(data)
    assert masked['diagnosis'] == "cancer"

def test_implicit_ignore():
    rules = {"other_field": "hash"}
    data = {"ignored_field": "stay_the_same"}
    masked = apply(data)
    assert masked['ignored_field'] == "stay_the_same"