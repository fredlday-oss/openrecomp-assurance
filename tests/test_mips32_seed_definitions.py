from harness.runner.openrecomp_mips32 import SEEDS, baseline_hex, decoded_records, seeded_hex


def canonical_from_seed_anchors() -> str:
    return "\n".join(old for _, old, _, _ in SEEDS) + "\n"


def test_seed_ids_and_anchors_are_unique():
    assert len(SEEDS) == 5
    assert len({seed_id for seed_id, _, _, _ in SEEDS}) == 5
    assert len({old for _, old, _, _ in SEEDS}) == 5


def test_equivalent_baseline_comments_change_bytes_not_records():
    canonical = canonical_from_seed_anchors()
    left = baseline_hex(canonical, "A")
    right = baseline_hex(canonical, "B")
    assert left != right
    assert decoded_records(left) == decoded_records(right)


def test_each_seed_changes_exactly_one_valid_instruction_record():
    canonical = canonical_from_seed_anchors()
    baseline = decoded_records(canonical)
    for _, old, new, _ in SEEDS:
        mutated = seeded_hex(canonical, old, new)
        records = decoded_records(mutated)
        assert len(records) == len(baseline)
        assert sum(a != b for a, b in zip(baseline, records, strict=True)) == 1
