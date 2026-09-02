from harness.runner.openrecomp_rv32i import SEEDS, baseline_source, seeded_source


CANONICAL = """
u32 recursive = fib(7u);
u32 looped = state_loop(5u);
u32 mixed = rotate_mix(looped, 3u);
host_graphics(1u, 2u, pixel);
u32 sample = (a ^ b) & 65535u;
"""


def test_exactly_five_unique_semantic_seeds():
    assert len(SEEDS) == 5
    assert len({seed[0] for seed in SEEDS}) == 5
    for _, old, new in SEEDS:
        assert old != new
        assert CANONICAL.count(old) == 1
        assert seeded_source(CANONICAL, old, new) != CANONICAL


def test_baseline_notes_change_provenance_without_source_body_change():
    a = baseline_source(CANONICAL, "A")
    b = baseline_source(CANONICAL, "B")
    assert a != b
    assert a.endswith(CANONICAL)
    assert b.endswith(CANONICAL)
    assert ".assurance_note" in a
